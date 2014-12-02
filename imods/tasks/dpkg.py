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

    if path.exists(overrides_file_path):
        overrides_file = gzip.open(overrides_file_path, "rt")

        for line in overrides_file:
            entry = line.split()
            key = "%s_%s" % (entry[0], entry[1])
            if key in dup:
                continue
            dup[key] = entry

        overrides_file.close()
    else:
        logging.info("overrides.gz doesn't exist, creating one...")

    overrides_file = gzip.open(overrides_file_path, "wt")

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


# TODO: Move s3 related task functions to imods.tasks.s3
@celery.task()
def upload_to_s3(bucket_name, key_path, local_file, clean=False):
    logging.info("Uploading %s to S3 %s::%s", local_file, bucket_name, key_path)
    # NOTE: the task will be running in another process or remote host, the app.s3_conn and
    # app.s3_assets_bucket may not be available, so here we manually connect to
    # S3 rather than reusing connection pool.
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
def delete_from_s3(bucket_name, key_path):
    logging.info("Delete file from S3 %s::%s" % (bucket_name, key_path))
    # app.s3_assets_bucket may not be available.
    # NOTE: the task will be running in another process or remote host, the app.s3_conn and
    # app.s3_assets_bucket may not be available, so here we manually connect to
    # S3 rather than reusing connection pool.
    s3 = boto.connect_s3(profile_name=app.config["BOTO_PROFILE"])
    bucket = s3.get_bucket(bucket_name)
    s3_file = bucket.get_key(key_path)
    if s3_file is None:
        return
    s3_file.delete()


@celery.task()
def dpkg_update_index(local_repo_path, bucket_name, index_key_path, index_file,
                      overrides=None):
    overrides_file_path = update_overrides_file(local_repo_path, overrides)
    if not dpkg_scan(local_repo_path, index_file, overrides_file_path):
        logging.error("dpkg-scanpackages just failed, stop updating index")
        return False

    upload_to_s3.delay(bucket_name, index_key_path, index_file, False)
