from google.api_core.exceptions import NotFound
from identifiers import hash_for_item
from jinja2 import Environment, select_autoescape
from google.cloud import storage
from identifiers import cache_filename_for_fn
from identifiers import hash_for_fn
from pathlib import Path
import analytics
import json
import tempfile

DEFAULT_BUCKET_NAME = "artifacts"

class Batch(object):
    def __init__(self, request):
        self.request = request
        self.info = request.get_json()
        self.bucket_name = self.info.get('bucket_name', DEFAULT_BUCKET_NAME)
        self.init_storage()
        self.jinja_env = Environment(
            autoescape=select_autoescape(['html', 'xml'])
            )
        self.template_data = {}

    def init_storage(self):
        self.storage_client = storage.Client()
        try:
            self.storage_bucket = self.storage_client.get_bucket(self.bucket_name)
        except NotFound:
            self.storage_bucket = self.storage_client.create_bucket(self.bucket_name)

    def load_if_cached(self, h):
        hashed_filename = cache_filename_for_fn(h)
        blob = self.storage_bucket.get_blob(hashed_filename)
    
        if blob is None:
            return
    
        with tempfile.TemporaryDirectory() as tmpdirname:
            fn = Path(tmpdirname) / hashed_filename
            print(fn)
            blob.download_to_filename(fn)
    
            with open(fn, 'r') as ff:
                json.load(ff)

    def save_to_cache(self, h, data):
        hashed_filename = cache_filename_for_fn(h)
        blob = self.storage_bucket.blob(hashed_filename)
    
        with tempfile.TemporaryDirectory() as tmpdirname:
            fn = Path(tmpdirname) / hashed_filename
            with open(fn, 'w') as ff:
                json.dump(data, ff)
    
            blob.upload_from_filename(str(fn))

    def generate_analytics(self):
        for function_name, kwargs in self.info.get('analytics', []):
            # get function object from function name
            fn = getattr(analytics, function_name)
            # TODO generalize module name beyond hard-coded 'analytics'

            h = hash_for_fn(fn, kwargs)
            data = self.load_if_cached(h)

            if data is None:
                # TODO add registered output files + hashes to data
                data = {}
                data['function_output'] = fn(self, **kwargs)
                self.save_to_cache(h, data)

            self.template_data[function_name] = data

    def save_matplotlib_plt(self, plt, canonical_filename):
        h = hash_for_item(canonical_filename)
        with tempfile.TemporaryDirectory() as tmpdirname:
            filepath = Path(tmpdirname) / canonical_filename
            with open(filepath, 'w+b') as f:
                plt.savefig(f, dpi=300, bbox_inches='tight')
            cache_path = "%s%s" % (h, filepath.suffix)
            blob = self.storage_bucket.blob(cache_path)
            blob.upload_from_filename(filepath)

    def template_text(self):
        return self.info.get("template")

    def render_template(self):
        self.template_data['batch'] = self
        template = self.jinja_env.from_string(self.template_text())
        return template.render(self.template_data)
