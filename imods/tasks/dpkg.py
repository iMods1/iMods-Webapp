from __future__ import absolute_import
from imods import app
from imods.celery import celery
import logging
import subprocess
import gzip
import os
import boto
from tempfile import mkstemp


def dpkg_scan(repo_path, extra_overrides_file):
    try:
        package_gz = gzip.open(os.path.join(repo_path, "Packages.gz"), "wb")
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
def dpkg_update_index(local_repo_path, bucket_name, index_key_path,
                      overrides=None):
    tmpfile = None
    if overrides:
        _, tmpfile = mkstemp()
        with open(tmpfile, "wb") as tmp:
            for entry in overrides:
                tmp.write("%s %s %s\n" % (str(entry[0]),
                                          str(entry[1]),
                                          str(entry[2])))
    if not dpkg_scan(local_repo_path, tmpfile):
        os.unlink(tmpfile)
        logging.error("dpkg-scanpackages just failed, stop updating index")
        return False
    os.unlink(tmpfile)

    upload_to_s3.delay(bucket_name, index_key_path, tmpfile, False)
