from __future__ import absolute_import
from imods import app
from imods.celery import celery
import logging
import subprocess
import gzip
from os import path
import os
import boto


def update_overrides_file(repo_path, extra_overrides):
    overrides_file_path = path.join(repo_path, "overrides.gz")

    if extra_overrides is None:
        return overrides_file_path

    dup = {}
    for entry in extra_overrides:
        key = "%s_%s" % (entry[0], entry[1])
        dup[key] = entry

    write_mode = ""
    if path.exists(overrides_file_path):
        overrides_file = gzip.open(overrides_file_path, "rt")

        for line in overrides_file:
            entry = line.split()
            key = "%s_%s" % (entry[0], entry[1])
            if key in dup:
                del dup[key]
                continue

        overrides_file.close()
        write_mode = "at"
    else:
        logging.info("overrides.gz doesn't exist, creating one...")
        write_mode = "wt"

    overrides_file = gzip.open(overrides_file_path, write_mode)

    for _, entry in dup.iteritems():
        overrides_file.write("%s %s %s\n" % (entry[0],
                                             entry[1],
                                             entry[2]))

    overrides_file.close()
    return overrides_file_path


def dpkg_scan(repo_path, index_file, extra_overrides_file):
    try:
        package_gz = gzip.open(index_file, "wb")
        if extra_overrides_file:
            options = ['-e', extra_overrides_file]
        else:
            options = []
        index_content = subprocess.check_output(
            ["dpkg-scanpackages"] + options + [repo_path])
        package_gz.write(index_content)
    except:
        return False

    return True


@celery.task()
def upload_to_s3(bucket_name, key_path, local_file, clean=False):
    logging.info("Uploading %s to %s//%s", local_file, bucket_name, key_path)
    s3 = boto.connect_s3(
        profile_name=app.config.get("BOTO_PROFILE"))
    # NOTE: Turn off bucket validation to speed up,
    # but make sure the bucket is present in S3
    bucket = s3.get_bucket(bucket_name)

    # TODO: Add threaded multipart uploading support for large files
    s3_file = bucket.get_key(key_path)
    if s3_file is None:
        s3_file = bucket.new_key(key_path)

    s3_file.set_contents_from_filename(local_file)

    # Remove tmp file
    if clean:
        os.unlink(local_file)


@celery.task()
def dpkg_update_index(local_repo_path, bucket_name, index_key_path, index_file,
                      overrides=None):
    overrides_file_path = update_overrides_file(local_repo_path, overrides)
    if not dpkg_scan(local_repo_path, index_file, overrides_file_path):
        logging.error("dpkg-scanpackages just failed, stop updating index")
        return False

    upload_to_s3.delay(bucket_name, index_key_path, index_file, False)
