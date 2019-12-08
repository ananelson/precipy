from google.api_core.exceptions import NotFound
from google.cloud import storage
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape
from pathlib import Path
from precipy.identifiers import cache_filename_for_fn
from precipy.identifiers import hash_for_doc
from precipy.identifiers import hash_for_fn
import json
import os
import precipy.output_filters as output_filters
import shutil
import tempfile
import time
from uuid import uuid4

class Batch(object):
    """
    Encapsulates batch behavior.
    
    Generates a temporary working directory.
    """

    def __init__(self, request):
        self.uuid = str(uuid4())
        self.current_function_name = None
        self.request = request
        self.info = request.get_json()
        self.cache_bucket_name = self.info.get('cache_bucket_name')
        self.output_bucket_name = self.info.get('output_bucket_name')
        self.init_storage()
        self.jinja_env = Environment(
            loader = FileSystemLoader("templates/"),
            autoescape=select_autoescape(['html', 'xml'])
            )
        self.template_data = {}
        self.template_name = "template.md"
        self.tempdir = tempfile.gettempdir()

        self.cache_dir = os.path.join(self.tempdir, self.cache_bucket_name)
        self.output_dir = os.path.join(self.tempdir, self.output_bucket_name, self.uuid)
        self.cachePath = Path(self.cache_dir)
        self.outputPath = Path(self.output_dir)

        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        if 'template_file' in self.info:
            self.template_name = self.info['template_file']
            self.template_ext = os.path.splitext(self.info['template_file'])[1]
        else:
            self.template_ext = ".md"

    def init_storage(self):
        self.storage_client = storage.Client()
        try:
            self.cache_storage_bucket = self.storage_client.get_bucket(self.cache_bucket_name)
        except NotFound:
            self.cache_storage_bucket = self.storage_client.create_bucket(self.cache_bucket_name)
        try:
            self.output_storage_bucket = self.storage_client.get_bucket(self.output_bucket_name)
        except NotFound:
            self.output_storage_bucket = self.storage_client.create_bucket(self.output_bucket_name)

    def check_and_sync_caches(self, cache_filename):
        """
        Returns False if cache_filename is not cached.

        If cache_filename is present in remote cache, ensures it is also available locally.
        """
        blob = self.cache_storage_bucket.get_blob(cache_filename)

        if blob is None:
            print("no cached file found for %s" % cache_filename)
            return False

        fn = self.cachePath / cache_filename
        if not os.path.exists(fn):
            print("downloading %s to local cache" % cache_filename)
            blob.download_to_filename(fn)
        else:
            print("cache file already present locally")

        return True

    def load_function_data_if_cached(self, h):
        cache_filename = cache_filename_for_fn(h)
        if not self.check_and_sync_caches(cache_filename):
            return

        fn = self.cachePath / cache_filename
        with open(fn, 'r') as ff:
            fn_data = json.load(ff)

        for cn, generated_file_info in fn_data['files'].items():
            self.check_and_sync_caches(generated_file_info['cache_file'])
            local_path = str(self.cachePath / generated_file_info['cache_file'])
            # update function metadata with updated value of local_path (which might change between runs)
            fn_data['files'][cn]['local_path'] = local_path

        return fn_data

    def save_function_data(self, h, data):
        hashed_filename = cache_filename_for_fn(h)
        blob = self.cache_storage_bucket.blob(hashed_filename)
    
        fn = self.cachePath / hashed_filename
        with open(fn, 'w') as ff:
            json.dump(data, ff)

        blob.upload_from_filename(str(fn))

    def get_fn_object(self, module_name, function_name, loaded_modules):
        for mod in loaded_modules:
            if module_name != None and mod.__name__ != module_name:
                print("skipping module name %s" % mod.__name__)
            else:
                fn = getattr(mod, function_name)
                if fn is not None:
                    return fn

    def generate_analytics(self, analytics_modules):
        print("args are %s" % str(analytics_modules))
        for qual_function_name, kwargs in self.info.get('analytics', []):
            print(qual_function_name)
            if "." in qual_function_name:
                module_name, function_name = qual_function_name.split(".")
            else:
                module_name = None
                function_name = qual_function_name
            self.current_function_name = function_name

            # get function object from function name
            fn = self.get_fn_object(module_name, function_name, analytics_modules)
            print("got fn %s " % str(fn))

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
        if "/" in cache_file:
            local_filepath = cache_file
        else:
            local_filepath = self.cachePath / cache_file
        assert os.path.exists(local_filepath), "no file at %s" % local_filepath
        blob = self.cache_storage_bucket.blob(cache_file)
        blob.upload_from_filename(str(local_filepath))

    def upload_canonical_file(self, canonical_file):
        local_filepath = self.outputPath / canonical_file
        assert os.path.exists(local_filepath), "no file at %s" % local_filepath
        blob = self.output_storage_bucket.blob(canonical_file)
        blob.upload_from_filename(str(local_filepath))

    def generate_and_upload_file(self, canonical_filename, write_mode='w'):
        """
        Standardize how analytics client libraries should generate additional files.

        Wrap this function to provide more specific utility functions,
        e.g. save_matplotlib_plt
        """
        local_canonical_filepath = self.outputPath / canonical_filename
        h = hash_for_doc(canonical_filename)
        cache_filename = "%s.%s" % (h, canonical_filename.split(".")[1])
        local_cache_filepath = self.cachePath / cache_filename

        if os.path.exists(local_cache_filepath):
            raise Exception("generating a cache file %s that already exists!" % local_cache_filepath)

        # yield the cache location so file can be written
        with open(local_cache_filepath, write_mode) as f:
            yield h, f

        print("copying from %s to %s" % (local_cache_filepath, local_canonical_filepath))
        shutil.copyfile(local_cache_filepath, local_canonical_filepath)

        print("uploading to %s" % cache_filename)
        blob = self.cache_storage_bucket.blob(cache_filename)
        blob.upload_from_filename(str(local_cache_filepath))

        if self.current_function_data is None:
            return

        if not "files" in self.current_function_data:
            self.current_function_data['files'] = {}

        self.current_function_data['files'][canonical_filename] = {
                'cache_file' : cache_filename,
                'canonical_name' : canonical_filename,
                'local_path' : str(local_canonical_filepath),
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
        template_basename = os.path.splitext(self.template_name)[0]

        # write the template to a file on disk
        # run jinja process
        prev_filename = self.template_name
        canonical_filename = prev_filename

        for h, f in self.generate_and_upload_file(prev_filename):
            f.write(self.render_template())

        # then, run any filters on the resulting document
        # save starting working dir so we can go back later
        curdir = os.getcwd()
        os.chdir(self.output_dir)

        for filter_opts in self.info.get('filters', []):
            if len(filter_opts) == 2:
                filter_name, output_ext = filter_opts
                filter_args = {}
            else:
                filter_name, output_ext, filter_args = filter_opts

            filter_fn = output_filters.__dict__["do_%s" % filter_name]
            canonical_filename = "%s.%s" % (template_basename, output_ext)
            output_filename = "%s.%s" % (h, output_ext)
            filter_fn(self, prev_filename, output_filename, output_ext, filter_args)
            print("generated %s" % output_filename)

            # upload cache and canonical files
            shutil.copyfile(output_filename, self.cachePath / output_filename)
            self.upload_existing_file(output_filename)
            shutil.copyfile(output_filename, self.outputPath / canonical_filename)
            self.upload_canonical_file(canonical_filename)

            prev_filename = output_filename
        os.chdir(curdir)
        return self.outputPath / canonical_filename
