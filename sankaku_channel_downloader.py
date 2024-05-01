import configparser
from enum import Enum
import xxhash
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import requests
from requests.exceptions import RequestException

sys.path.append("C:\\Storage\\Source\\Python_Modules")

from modules.menelku.utils import TimedColoredLogger, wait

log = TimedColoredLogger()
SANKAKU_SECRETS = {}
WRONG_HASHES_POSTS = []
INACCESSIBLE_POSTS = []
FAILED_PAGES = []
DOWNLOADED_PAGES = []


class ContentType(Enum):
    IMAGE_DOWNSIZED = 0
    IMAGE = 1
    VIDEO = 2
    INACCESSIBLE = 3


def write_results():
    log.info("Writing results to files")

    if WRONG_HASHES_POSTS:
        log.error(f"Posts with wrong hashes: {WRONG_HASHES_POSTS}")
        with open("./wrong_hashes.txt", "w") as f:
            f.write("\n".join(WRONG_HASHES_POSTS))

    if INACCESSIBLE_POSTS:
        log.error(f"Inaccessible posts: {INACCESSIBLE_POSTS}")
        with open("./inaccessible_posts.txt", "w") as f:
            f.write("\n".join(INACCESSIBLE_POSTS))

    if FAILED_PAGES:
        log.error(f"Failed pages: {FAILED_PAGES}")
        with open("./failed_pages.txt", "w") as f:
            f.write("\n".join(FAILED_PAGES))

    if DOWNLOADED_PAGES:
        log.success(f"Downloaded pages: {DOWNLOADED_PAGES}")
        with open("./downloaded_pages.txt", "w") as f:
            f.write("\n".join(DOWNLOADED_PAGES))

    log.success("Results written to files")
    return


class SankakuDownloaderException(Exception):
    "Sankaku Downloader encountered an error"
    write_results()
    pass


def update_hash(path, hash):
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hash.update(chunk)

    return hash


def compare_hashes(save_path, temp_save_path, post_id):
    log.info(f"Comparing hashes for {post_id}")

    hash = xxhash.xxh64()
    hash = update_hash(save_path, hash)

    local_hash = hash.hexdigest()
    log.info(f"Local hash: {local_hash}")

    hash = xxhash.xxh64()
    hash = update_hash(temp_save_path, hash)

    remote_hash = hash.hexdigest()
    log.info(f"Remote hash: {remote_hash}")

    if local_hash != remote_hash:
        log.error(f"Hashes do not match for {post_id}")
        WRONG_HASHES_POSTS.append(post_id)
        return

    log.success(f"Hashes match for {post_id}")
    return


def wait_for_login_form(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "password"))
        )
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    '//*[@id="app"]/div/div[2]/div/form/div/div[2]/div[2]/button[1]',
                )
            )
        )
    except Exception as e:
        log.error("Failed to load login page: {e}")
        raise SankakuDownloaderException

    return


def login_into_sankaku(driver):
    log.info("Logging into Sankaku Complex")

    driver.get(SANKAKU_SECRETS["LOGIN_URL"])
    wait_for_login_form(driver)
    driver.find_element(By.NAME, "email").send_keys(SANKAKU_SECRETS["USERNAME"])
    driver.find_element(By.NAME, "password").send_keys(SANKAKU_SECRETS["PASSWORD"])
    driver.find_element(
        By.XPATH, '//*[@id="app"]/div/div[2]/div/form/div/div[2]/div[2]/button[1]'
    ).click()

    if driver.find_elements(By.CLASS_NAME, "error"):
        log.error("Failed to login into Sankaku Complex")
        raise SankakuDownloaderException

    log.success("Logged into Sankaku Complex")
    return


def check_premium_notif(driver):
    log.info("Checking for premium notification")

    if not driver.find_elements(By.CLASS_NAME, "table--premium"):
        log.info("No premium notification found")
        return

    log.warning("Premium notification found")
    driver.find_element(By.ID, "close-btn").click()
    log.success("Premium notification closed")
    return


def handle_sc_toggle(driver, page_num):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "sc-auto-toggle"))
        )
    except Exception as e:
        log.error(f"Failed to fetch page {page_num}, {e}")
        raise SankakuDownloaderException

    if driver.find_element(By.ID, "sc-auto-toggle").text == "Enabled: On":
        driver.find_element(By.ID, "sc-auto-toggle").click()
        driver.refresh()

    return


def wait_for_thumbnails(driver, page_num):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "thumb"))
        )
    except Exception as e:
        log.error(f"Failed to fetch page {page_num}, {e}")
        raise SankakuDownloaderException

    return


def get_all_post_ids_on_page(page_num, driver):
    log.info(f"Fetching posts from page {page_num}")

    url = SANKAKU_SECRETS["BASE_URL"] + f"&page={page_num}"
    wait(15, 15, log)  # Change this for a dedicated wait function
    driver.get(url)

    check_premium_notif(driver)
    handle_sc_toggle(driver, page_num)
    check_premium_notif(driver)
    wait_for_thumbnails(driver, page_num)

    spans = driver.find_elements(By.CLASS_NAME, "thumb")
    post_ids = [
        span.find_element(By.TAG_NAME, "a").get_attribute("href").split("/")[-1]
        for span in spans
    ]

    log.info(f"Found {len(post_ids)} posts on page {page_num}")
    return list(filter(None, post_ids))


def get_content_type(driver):
    if driver.find_elements(By.ID, "post-content")[0].find_elements(
        By.CLASS_NAME, "sample"
    ):
        return ContentType.IMAGE_DOWNSIZED

    elif driver.find_elements(By.ID, "post-content")[0].find_elements(
        By.TAG_NAME, "video"
    ):
        return ContentType.VIDEO

    elif driver.find_elements(By.ID, "post-content")[0].find_elements(By.ID, "image"):
        return ContentType.IMAGE

    else:
        return ContentType.INACCESSIBLE


def get_content_type_link(content_type, driver):
    if content_type == ContentType.IMAGE_DOWNSIZED:
        content = driver.find_elements(By.ID, "post-content")[0].find_elements(
            By.ID, "image-link"
        )
        return content[0].get_attribute("href")

    elif content_type == ContentType.VIDEO:
        content = driver.find_elements(By.ID, "post-content")[0].find_elements(
            By.TAG_NAME, "video"
        )
        return content[0].get_attribute("src")

    elif content_type == ContentType.IMAGE:
        content = driver.find_elements(By.ID, "post-content")[0].find_elements(
            By.ID, "image"
        )
        return content[0].get_attribute("src")

    else:
        log.error("Link of this content type is not supported")
        raise SankakuDownloaderException


def wait_for_post_content(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "post-content"))
        )
    except Exception as e:
        log.error(f"Failed to fetch post content: {e}")
        raise SankakuDownloaderException

    return


def stream_download(path, response):
    with open(path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


def compare_existing_files(save_path, response, post_extension, post_id):
    os.makedirs(SANKAKU_SECRETS["POST_DIR"] + f"/temp", exist_ok=True)
    temp_save_path = (
        SANKAKU_SECRETS["POST_DIR"] + f"/temp/{post_id}.{post_extension.group(1)}"
    )

    log.info(f"Saving post {post_id} to {temp_save_path}, for hash comparison")
    stream_download(temp_save_path, response)

    compare_hashes(save_path, temp_save_path, post_id)

    os.remove(temp_save_path)
    os.rmdir(SANKAKU_SECRETS["POST_DIR"] + f"/temp")

    return


def download_post(post_id, driver):
    log.info(f"Fetching post details for {post_id}")

    url = f"https://chan.sankakucomplex.com/posts/{post_id}"
    driver.get(url)

    check_premium_notif(driver)
    wait_for_post_content(driver)

    check_premium_notif(driver)
    content_type = get_content_type(driver)

    check_premium_notif(driver)
    content_link = get_content_type_link(content_type, driver)

    if content_type == ContentType.INACCESSIBLE:
        log.error(f"Post {post_id} is inaccessible, the link is {content_link}")
        INACCESSIBLE_POSTS.append(post_id)
        return

    if "sample" in content_link:
        log.error(f"Post {post_id} is downsized")
        return

    log.info(f"Downloading post content for: {post_id}")
    log.info(f"Post content url: {content_link}")

    try:
        response = requests.get(content_link, stream=True)
    except RequestException as e:
        log.error(f"Failed to fetch original image for {post_id}, {e}")
        return

    post_extension = re.search(r"(jpg|png|gif|jpeg|mp4)", content_link)
    save_path = SANKAKU_SECRETS["POST_DIR"] + f"/{post_id}.{post_extension.group(1)}"
    os.makedirs(SANKAKU_SECRETS["POST_DIR"], exist_ok=True)

    if os.path.exists(save_path):
        log.info(f"Post {post_id} already exists in the directory")
        compare_existing_files(save_path, response, post_extension, post_id)
        return

    log.info(f"Saving post {post_id} to {save_path}")
    stream_download(save_path, response)

    log.success(f"Post {post_id} downloaded successfully")
    return


def set_up_driver():
    log.info("Setting up driver")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless")
    options.add_argument("log-level=2")
    driver = webdriver.Chrome(options=options)
    log.success("Driver set up successfully")
    return driver


def fetch_post_ids(page_num, driver):
    check_limit = 10
    post_ids = get_all_post_ids_on_page(page_num, driver)

    while not post_ids and check_limit > 0:
        log.warning(f"Failed to fetch posts from page {page_num}, retrying in 30s")
        wait(30, 30, log)
        post_ids = get_all_post_ids_on_page(page_num, driver)
        check_limit -= 1

        if check_limit == 0:
            log.error(f"Failed to fetch posts from page {page_num}, skipping")
            FAILED_PAGES.append(page_num)
            page_num += 1
            return []

    return post_ids


def download_posts(driver):
    page_num = 1
    while page_num <= int(SANKAKU_SECRETS["LAST_PAGE_NUM"]):
        post_ids = fetch_post_ids(page_num, driver)

        if not post_ids:
            page_num += 1
            continue

        for post_id in post_ids.copy():
            download_post(post_id, driver)
            post_ids.remove(post_id)

            if not post_ids:
                log.success("All posts on page downloaded, moving to the next page")
                DOWNLOADED_PAGES.append(page_num)
                break

            wait(5, 5, log)

        page_num += 1
        if page_num > SANKAKU_SECRETS["LAST_PAGE_NUM"]:
            log.info("Last page reached, all content downloaded")
            break

        wait(5, 5, log)


def parse_config():
    global SANKAKU_SECRETS
    log.info("Parsing config")

    config = configparser.ConfigParser(interpolation=None)
    config.read("config.ini")
    SANKAKU_SECRETS.clear()
    SANKAKU_SECRETS.update(config["SANKAKU_SECRETS"])
    SANKAKU_SECRETS = {k.upper(): v for k, v in SANKAKU_SECRETS.items()}

    log.success("Config successfully parsed")


def main():
    log.success("Started sankaku_channel_favorites_downloader.py")
    parse_config()
    driver = set_up_driver()
    login_into_sankaku(driver)
    download_posts(driver)


if __name__ == "__main__":
    main()
