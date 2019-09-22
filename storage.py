# abstraction of working and caching storage
# for now, write to a local tempfile then push to google cloud storage bucket
#import tempfile
from google.api_core.exceptions import NotFound
from google.cloud import storage

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

def load_if_cached(hashed_filename, bucket_name=DEFAULT_BUCKET_NAME):
    init_storage(bucket_name)
    blob = storage_bucket.get_blob(hashed_filename)
    print(dir(blob))
