from google.api_core.exceptions import NotFound
from google.cloud import storage
from identifiers import cache_filename_for_fn
from identifiers import hash_for_doc
from identifiers import hash_for_fn
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape
from pathlib import Path
import analytics
import json
import os
import output_filters
import time

class Batch(object):
    """
    Encapsulates batch behavior.
    
    Generates a temporary working directory.
    """

    def __init__(self, request):
        self.current_function_name = None
        self.request = request
        self.info = request.get_json()
        self.bucket_name = self.info.get('bucket_name')
        self.init_storage()
        self.jinja_env = Environment(
            loader = FileSystemLoader("templates/"),
            autoescape=select_autoescape(['html', 'xml'])
            )
        self.template_data = {}
        self.workdir = os.path.abspath("cache/%s" % self.info.get('bucket_name'))
        self.outdir = "generated"

        os.makedirs(self.workdir, exist_ok=True)
        os.makedirs(self.outdir, exist_ok=True)

        if 'template_file' in self.info:
            self.template_ext = os.path.splitext(self.info['template_file'])[1]
        else:
            self.template_ext = ".md"

    def init_storage(self):
        self.storage_client = storage.Client()
        if self.bucket_name is None:
            raise Exception("must provide a storage bucket name!")
        try:
            self.storage_bucket = self.storage_client.get_bucket(self.bucket_name)
        except NotFound:
            self.storage_bucket = self.storage_client.create_bucket(self.bucket_name)

    def check_and_sync_caches(self, cache_filename):
        """
        Returns False if cache_filename is not cached.

        If cache_filename is present in remote cache, ensures it is also available locally.
        """
        blob = self.storage_bucket.get_blob(cache_filename)

        if blob is None:
            print("no cached file found for %s" % cache_filename)
            return False

        fn = Path(self.workdir) / cache_filename
        if not os.path.exists(fn):
            print("downloading %s to local cache" % cache_filename)
            blob.download_to_filename(fn)
        else:
            print("cache file already present locally")

    def load_function_data_if_cached(self, h):
        cache_filename = cache_filename_for_fn(h)
        if not self.check_and_sync_caches(cache_filename):
            return

        fn = Path(self.workdir) / cache_filename
        with open(fn, 'r') as ff:
            fn_data = json.load(ff)

        for cn, generated_file_info in fn_data['files'].items():
            self.check_and_sync_caches(generated_file_info['cache_file'])
            local_path = str(Path(self.workdir) / generated_file_info['cache_file'])
            # update function metadata with updated value of local_path (which might change between runs)
            fn_data['files'][cn]['local_path'] = local_path

        return fn_data

    def save_function_data(self, h, data):
        hashed_filename = cache_filename_for_fn(h)
        blob = self.storage_bucket.blob(hashed_filename)
    
        fn = Path(self.workdir) / hashed_filename
        with open(fn, 'w') as ff:
            json.dump(data, ff)

        blob.upload_from_filename(str(fn))

    def generate_analytics(self):
        for function_name, kwargs in self.info.get('analytics', []):
            self.current_function_name  = function_name

            # get function object from function name
            fn = getattr(analytics, function_name)
            # TODO generalize module name beyond hard-coded 'analytics'

            h = hash_for_fn(fn, kwargs)
            self.current_function_data = self.load_function_data_if_cached(h)

            if self.current_function_data is None:
                self.current_function_data = {}
                start_time = time.time()
                # run the actual function
                output = fn(self, **kwargs)
                self.current_function_data['function_elapsed_seconds'] = time.time() - start_time
                self.current_function_data['function_output'] = output
                self.save_function_data(h, self.current_function_data)
            else:
                self.current_function_data['from_cache'] = True

            self.template_data[function_name] = self.current_function_data

        self.current_function_name = None
        self.current_function_data = None

    def upload_existing_file(self, cache_file):
        print(os.path.abspath(self.workdir))
        print(os.path.abspath(os.getcwd()))
        if os.path.abspath(os.getcwd()) == os.path.abspath(self.workdir):
            local_filepath = cache_file
        else:
            local_filepath = str(Path(self.workdir) / cache_file)
        assert os.path.exists(local_filepath), "no file at %s" % local_filepath
        blob = self.storage_bucket.blob(cache_file)
        blob.upload_from_filename(str(local_filepath))

    def generate_and_upload_file(self, canonical_filename, write_mode='w'):
        """
        Standardize how analytics client libraries should generate additional files.

        Wrap this function to provide more specific utility functions,
        e.g. save_matplotlib_plt
        """
        h = hash_for_doc(canonical_filename)
        filepath = Path(self.workdir) / canonical_filename
        cache_file = "%s%s" % (h, filepath.suffix)

        if os.path.exists(cache_file):
            raise Exception("generating a file %s that already exists!" % filepath)

        with open(cache_file, write_mode) as f:
            yield h, f
        print("uploading to %s" % cache_file)
        blob = self.storage_bucket.blob(cache_file)
        blob.upload_from_filename(str(filepath))

        if self.current_function_data is None:
            return

        if not "files" in self.current_function_data:
            self.current_function_data['files'] = {}

        self.current_function_data['files'][canonical_filename] = {
                'cache_file' : cache_file,
                'canonical_name' : canonical_filename,
                'local_path' : str(filepath),
                'url' : blob.public_url
                }

    def save_matplotlib_plt(self, plt, canonical_filename):
        for h, f in self.generate_and_upload_file(canonical_filename, 'wb'):
            plt.savefig(f, dpi=300, bbox_inches='tight')

    def create_document_template(self):
        if 'template_file' in self.info:
            print("Loading template from file %s"% self.info['template_file'])
            return self.jinja_env.get_template(self.info['template_file'])
        else:
            print("Creating template from string...")
            return self.jinja_env.from_string(self.info['template'])

    def render_template(self):
        self.template_data['batch'] = self
        self.template_data['keys'] = self.template_data.keys()
        self.template_data['data'] = self.template_data
        template = self.create_document_template()
        return template.render(self.template_data)

    def process_filters(self):
        # first, process the document template
        prev_filename = "output%s" % self.template_ext
        for h, f in self.generate_and_upload_file(prev_filename):
            f.write(self.render_template())

        uploaded_to = None
        # then, run any filters on the resulting document
        curdir = os.getcwd()
        os.chdir(self.workdir)
        for filter_opts in self.info.get('filters', []):
            if len(filter_opts) == 2:
                filter_name, output_ext = filter_opts
                filter_args = {}
            else:
                filter_name, output_ext, filter_args = filter_opts

            filter_fn = output_filters.__dict__["do_%s" % filter_name]
            output_filename = "%s.%s" % (h, output_ext)
            filter_fn(self, prev_filename, output_filename, output_ext, filter_args)
            print("generated %s" % output_filename)
            uploaded_to = self.upload_existing_file(output_filename)
            prev_filename = output_filename
        os.chdir(curdir)
        return uploaded_to
