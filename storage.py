# abstraction of working and caching storage
# for now, write to a local tempfile then push to google cloud storage bucket
import tempfile
import json
from identifiers import cache_filename_for_fn
from google.api_core.exceptions import NotFound
from google.cloud import storage
from pathlib import Path

DEFAULT_BUCKET_NAME = "oa_artifacts"

storage_client = None
storage_bucket = None

def init_storage(bucket_name = DEFAULT_BUCKET_NAME):
    global storage_client
    global storage_bucket

    if storage_client is None:
        storage_client = storage.Client()

    if storage_bucket is not None and storage_bucket.name != bucket_name:
        storage_bucket = None

    if storage_bucket is None:
        try:
            storage_bucket = storage_client.get_bucket(bucket_name)
        except NotFound:
            storage_bucket = storage_client.create_bucket(bucket_name)

def load_if_cached(h, bucket_name=DEFAULT_BUCKET_NAME):
    init_storage(bucket_name)

    hashed_filename = cache_filename_for_fn(h)
    blob = storage_bucket.get_blob(hashed_filename)

    if blob is None:
        return

    with tempfile.TemporaryDirectory() as tmpdirname:
        fn = Path(tmpdirname) / hashed_filename
        print(fn)
        blob.download_to_filename(fn)

        with open(fn, 'r') as ff:
            json.load(ff)

def save_to_cache(h, data, bucket_name=DEFAULT_BUCKET_NAME):
    init_storage(bucket_name)

    hashed_filename = cache_filename_for_fn(h)
    blob = storage_bucket.get_blob(hashed_filename)

    with tempfile.TemporaryDirectory() as tmpdirname:
        fn = Path(tmpdirname) / hashed_filename
        with open(fn, 'w') as ff:
            json.dump(data, ff)
        blob.upload_from_filename(fn)

