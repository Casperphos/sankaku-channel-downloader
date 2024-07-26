import os
import shutil

import xxhash

from utils.menelku_utils import log
from utils.sankaku_download import stream_download
from utils.sankaku_globals import (
    get_sankaku_secrets,
    get_wrong_hashes_posts,
    set_wrong_hashes_posts,
)

sankaku_secrets = get_sankaku_secrets()


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
        return False

    log.success(f"Hashes match for {post_id}")
    return True


def compare_existing_files(save_path, response, post_extension, post_id):
    os.makedirs(sankaku_secrets["save_dir"] + f"/temp", exist_ok=True)
    temp_save_path = os.path.normpath(
        sankaku_secrets["save_dir"] + f"/temp/{post_id}.{post_extension.group(1)}"
    )

    log.info(f"Saving post {post_id} to {temp_save_path}, for hash comparison")
    stream_download(temp_save_path, response)

    if compare_hashes(save_path, temp_save_path, post_id) is False:
        set_wrong_hashes_posts(get_wrong_hashes_posts() + [post_id])
        return False

    os.remove(temp_save_path)
    shutil.rmtree(sankaku_secrets["save_dir"] + f"/temp")

    return True
