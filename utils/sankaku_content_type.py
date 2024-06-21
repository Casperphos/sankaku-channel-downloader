from enum import Enum

from selenium.webdriver.common.by import By

from utils.menelku_utils import log
from utils.sankaku_exception import SankakuDownloaderException


class ContentType(Enum):
    IMAGE_DOWNSIZED = 0
    IMAGE = 1
    VIDEO = 2
    INACCESSIBLE = 3


def get_content_type(driver):
    """
    This may be pretty confusing, but the existence of a downsize image, tells us
    that there is another link to the full-sized image. This is why we are checking
    for whether the image is downsized first.
    """
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
