from pathlib import Path
from precipy.analytics_function import AnalyticsFunction
from precipy.batch import Batch
from precipy.storage import GoogleCloudStorage
import os

def bar(af):
    with open("hello.txt", 'w') as f:
        f.write("hello!")
    af.add_existing_file("hello.txt")
    os.remove("hello.txt")

af = AnalyticsFunction(bar, {})

storage = GoogleCloudStorage()
batch = Batch({
    'storages' : [storage],
    'cache_bucket_name' : 'precipy_testing_cache',
    'output_bucket_name' : 'precipy_testing_output'
    })

def test_connect():
    storage.init(batch)
    storage.connect()
    assert str(storage.cache_storage_bucket) == "<Bucket: precipy_testing_cache>"
    assert str(storage.output_storage_bucket) == "<Bucket: precipy_testing_output>"

def test_upload_and_download():
    af.storages = [storage]
    af.run_function()
    public_url = af.files["metadata.pkl"].public_urls[0]
    assert public_url.endswith(af.metadata_cache_filename())

    result = af.download_from_storages(af.metadata_cache_filepath())
    assert result

def test_invalid_upload():
    try:
        storage.upload_cache(Path("does-not-exist.txt"))
        assert False, "should throw FileNotFoundError"
    except FileNotFoundError:
        pass
