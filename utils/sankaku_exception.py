from utils.menelku_utils import log
from utils.sankaku_globals import (
    get_downloaded_pages,
    get_failed_pages,
    get_inaccessible_posts,
    get_wrong_hashes_posts,
)

WRONG_HASHES_POSTS = get_wrong_hashes_posts()
INACCESSIBLE_POSTS = get_inaccessible_posts()
FAILED_PAGES = get_failed_pages()
DOWNLOADED_PAGES = get_downloaded_pages()


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
