import os
import random
import re
import time

import requests
from requests.exceptions import RequestException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from utils.menelku_utils import log, wait
from utils.sankaku_content_type import (
    ContentType,
    SankakuDownloaderException,
    get_content_type,
    get_content_type_link,
)
from utils.sankaku_download import stream_download
from utils.sankaku_exception import SankakuDownloaderException, write_results
from utils.sankaku_globals import (
    get_downloaded_pages,
    get_failed_pages,
    get_inaccessible_posts,
    get_sankaku_secrets,
    set_downloaded_pages,
    set_failed_pages,
    set_inaccessible_posts,
)
from utils.sankaku_hash import compare_existing_files
from utils.sankaku_setup import set_up_driver

SANKAKU_SECRETS = get_sankaku_secrets()


def login_into_sankaku(driver):
    log.info("Logging into Sankaku Complex")

    driver.get(SANKAKU_SECRETS["LOGIN_URL"])
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "email")))
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "password"))
    )

    driver.find_element(By.NAME, "email").send_keys(SANKAKU_SECRETS["USERNAME"])
    driver.find_element(By.NAME, "password").send_keys(SANKAKU_SECRETS["PASSWORD"])
    driver.find_element(
        By.XPATH, '//*[@id="app"]/div/div[2]/div/form/div/div[2]/div[2]/button[1]'
    ).click()  # TODO: Change this xpath

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "navbar")))

    if driver.find_elements(By.CLASS_NAME, "error"):
        log.error("Failed to login into Sankaku Complex")
        raise SankakuDownloaderException

    log.success("Logged into Sankaku Complex")
    return


def parse_post_ids_from_page(page_num, driver):
    log.info(f"Fetching posts from page {page_num}")

    url = SANKAKU_SECRETS["BASE_URL"] + f"&page={page_num}"
    driver.get(url)

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, "post-preview-link"))
    )

    post_links = driver.find_elements(By.CLASS_NAME, "post-preview-link")
    post_ids = [
        re.search(r"posts/(.*)", post_link.get_attribute("href")).group(1)
        for post_link in post_links
    ]

    log.info(f"Found {len(post_ids)} posts on page {page_num}")
    return list(filter(None, post_ids))


def get_post_ids(page_num, driver):
    check_limit = 5
    post_ids = parse_post_ids_from_page(page_num, driver)

    while not post_ids and check_limit > 0:
        log.warning(
            f"Failed to fetch posts from page {page_num}, retrying in 10 seconds"
        )
        wait(10, 10, log)
        post_ids = parse_post_ids_from_page(page_num, driver)
        check_limit -= 1

    if check_limit == 0:
        log.error(f"Failed to fetch posts from page {page_num}, skipping")
        set_failed_pages(get_failed_pages() + [page_num])
        page_num += 1
        return []

    return post_ids


def get_post_content(post_id, content_link):
    try:
        response = requests.get(content_link, stream=True)
    except RequestException as e:
        log.error(f"Failed to fetch original image for {post_id}, {e}")
        return False

    if response.status_code != 200:
        log.error(
            f"Failed to fetch original image for {post_id}, status code: {response.status_code}"
        )
        return False

    return response


def save_post(post_id, post_extension, content_link):
    identical_file_exists = False
    compare_existing = SANKAKU_SECRETS["COMPARE_EXISTING"]
    save_dir = SANKAKU_SECRETS["SAVE_DIR"]
    save_path = os.path.normpath(save_dir + f"/{post_id}.{post_extension.group(1)}")
    os.makedirs(save_dir, exist_ok=True)

    if os.path.exists(save_path):
        if compare_existing:
            log.info(
                f"Post {post_id} already exists in the directory, comparing hashes"
            )
            identical_file_exists = compare_existing_files(
                save_path,
                get_post_content(post_id, content_link),
                post_extension,
                post_id,
            )
        else:
            log.warning(f"Post {post_id} already exists in the directory, skipping")
            return False

    if identical_file_exists:
        log.warning(f"Identical file for post {post_id} already exists, skipping")
        return True  # compare_existing_files incurs a download, so we return True here

    response = get_post_content(post_id, content_link)
    file_size = round(len(response.content) / 1024 / 1024, 2)
    log.info(f"Saving post {post_id} to {save_path}, it weighs {file_size} MB")
    stream_download(save_path, response)
    log.success(f"Post {post_id} downloaded successfully")
    return True


def download_post(post_id, driver):
    log.info(f"Fetching post details for {post_id}")

    url = f"https://chan.sankakucomplex.com/posts/{post_id}"
    driver.get(url)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "post-content"))
    )

    content_type = get_content_type(driver)
    content_link = get_content_type_link(content_type, driver)

    if content_type == ContentType.INACCESSIBLE:
        log.error(f"Post {post_id} is inaccessible, the link is {content_link}")
        set_inaccessible_posts(get_inaccessible_posts() + [post_id])
        return False

    if "sample" in content_link:
        log.error(f"Post {post_id} is downsized")
        return False

    log.info(f"Downloading post content for: {post_id}")
    log.info(f"The url is: {content_link}")
    log.info(f"The type is: {content_type}")

    post_extension = re.search(r"(jpg|png|gif|jpeg|mp4|webm)", content_link)
    if not post_extension:
        log.error(f"Post {post_id} has an unknown extension: {content_link}")
        return False

    file_downloaded = save_post(post_id, post_extension, content_link)
    return file_downloaded


def get_last_page_num(driver):
    log.info("Getting last page number")

    potential_last_page = SANKAKU_SECRETS["LAST_PAGE_NUM"]
    if potential_last_page != None and str(potential_last_page).isdigit():
        log.success(
            f"Last page number was specified, last page number: {potential_last_page}"
        )
        return int(SANKAKU_SECRETS["LAST_PAGE_NUM"])

    log.warning("Last page number was not specified, attempting to fetch it")

    current_page = 1
    while True:  # TODO: Better way to handle this
        try:
            url = SANKAKU_SECRETS["BASE_URL"] + f"&page={current_page}"
            log.info(f"Checking if page {current_page} is the last page, url: {url}")

            driver.get(url)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "post-preview-link"))
            )

            current_page += 1

        except TimeoutException as _:
            log.success(
                f"Failed to fetch posts from page {current_page}, meaning the last page is {current_page - 1}"
            )
            return current_page - 1


def get_first_page_num():
    log.info("Getting first page number")

    potential_first_page = SANKAKU_SECRETS["FIRST_PAGE_NUM"]
    if potential_first_page != None and str(potential_first_page).isdigit():
        log.success(
            f"First page number was specified, first page number: {potential_first_page}"
        )
        return int(SANKAKU_SECRETS["FIRST_PAGE_NUM"])

    log.warning("First page number was not specified, defaulting to 1")
    return 1


def download_posts(driver):
    last_page = get_last_page_num(driver)
    current_page = get_first_page_num()

    while current_page <= last_page:
        post_ids = get_post_ids(current_page, driver)
        post_len = len(post_ids)
        for post_id in post_ids:
            start_time = time.time()

            log.info(
                f"Downloading post {post_id}, [post {post_ids.index(post_id) + 1}/{post_len}, page {current_page}/{last_page}]"
            )
            file_downloaded = download_post(post_id, driver)
            if file_downloaded:
                random_wait = random.randint(5, 10)
                wait(random_wait, random_wait, log)

            end_time = time.time()
            log.success(
                f"Downloading that post took {round(end_time - start_time, 2)} seconds"
            )

        log.success("All posts on page downloaded, moving to the next page")
        set_downloaded_pages(get_downloaded_pages() + [current_page])
        current_page += 1

    log.info("Last page reached, all content downloaded")
    return True


def main():
    log.success("Started sankaku_channel_downloader.py")
    driver = set_up_driver()
    login_into_sankaku(driver)
    download_posts(driver)
    write_results()


if __name__ == "__main__":
    main()
