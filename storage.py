# abstraction of working and caching storage
# for now, write to a local tempfile then push to google cloud storage bucket
import tempfile
from google.cloud import storage

BUCKET_NAME = "oa_artifacts"

storage_client = None
storage_bucket = None

def init_storage():
    global storage_client
    global storage_bucket

    if storage_client is None:
        storage_client = storage.Client()

    if storage_bucket is None:
        storage_bucket = storage_client.get_bucket(BUCKET_NAME)

def load_if_cached(hashed_filename):
    init_storage()
    blob = storage_bucket.get_blob(hashed_filename)
    print(dir(blob))
