sankaku_secrets = {}
WRONG_HASHES_POSTS = []
INACCESSIBLE_POSTS = []
FAILED_PAGES = []
DOWNLOADED_PAGES = []

from utils.sankaku_setup import parse_config

sankaku_secrets = parse_config()


def get_sankaku_secrets():
    global sankaku_secrets
    return sankaku_secrets


def set_sankaku_secrets(secrets):
    global sankaku_secrets
    sankaku_secrets = secrets


def get_wrong_hashes_posts():
    global WRONG_HASHES_POSTS
    return WRONG_HASHES_POSTS


def set_wrong_hashes_posts(posts):
    global WRONG_HASHES_POSTS
    WRONG_HASHES_POSTS = posts


def get_inaccessible_posts():
    global INACCESSIBLE_POSTS
    return INACCESSIBLE_POSTS


def set_inaccessible_posts(posts):
    global INACCESSIBLE_POSTS
    INACCESSIBLE_POSTS = posts


def get_failed_pages():
    global FAILED_PAGES
    return FAILED_PAGES


def set_failed_pages(pages):
    global FAILED_PAGES
    FAILED_PAGES = pages


def get_downloaded_pages():
    global DOWNLOADED_PAGES
    return DOWNLOADED_PAGES


def set_downloaded_pages(pages):
    global DOWNLOADED_PAGES
    DOWNLOADED_PAGES = pages
