try:
    from google.api_core.exceptions import NotFound
    from google.cloud import storage
    GOOGLE_CLOUD_AVAILABLE = True
except Exception as e:
    print("error loading google cloud functions: %s" % str(e))
    print("disabling google cloud for now")
    GOOGLE_CLOUD_AVAILABLE = False

from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape
from pathlib import Path
from precipy.identifiers import cache_filename_for_fn
from precipy.identifiers import hash_for_fn
from precipy.identifiers import hash_for_template
from uuid import uuid4
import datetime
import json
import os
import precipy.output_filters as output_filters
import shutil
import tempfile
import time

import logging


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

        if 'tempdir' in self.info:
            self.tempdir = self.info['tempdir']
        else:
            self.tempdir = tempfile.gettempdir()

        self.cache_dir = os.path.join(self.tempdir, self.cache_bucket_name)
        self.output_dir = os.path.join(self.tempdir, self.output_bucket_name, self.uuid)
        self.cachePath = Path(self.cache_dir)
        self.outputPath = Path(self.output_dir)
        self.tempdirOutputPath = Path(self.tempdir) / "output"

        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.tempdirOutputPath, exist_ok=True)

        if 'template_file' in self.info:
            self.template_name = self.info['template_file']
            self.template_ext = os.path.splitext(self.info['template_file'])[1]
        else:
            self.template_ext = ".md"

        # set up logging
        print("setting up logging...")
        self.logger = logging.getLogger(name="precipy")

        # log to file if specified, else stderr
        if "logfile" in self.info:
            handler = logging.FileHandler(self.info['logfile'])
        else:
            handler = logging.StreamHandler()

        # default to INFO unless specified
        level = self.info.get('loglevel', "INFO")
        handler.setLevel(level)
        self.logger.setLevel(level)
        
        # attach handler
        logging.getLogger('precipy').addHandler(handler)
        self.logger.info("logging!")

    def init_storage(self):
        if GOOGLE_CLOUD_AVAILABLE:
            self.init_google_cloud_storage()

    def init_google_cloud_storage(self):
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
            self.logger.info("no remote cached file found for %s" % cache_filename)
            return False

        fn = self.cachePath / cache_filename
        if not os.path.exists(fn):
            self.logger.info("downloading '%s' to local cache" % cache_filename)
            blob.download_to_filename(fn)
        else:
            self.logger.info("cache file %s already present locally" % cache_filename)

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
            local_cache_path = str(self.cachePath / generated_file_info['cache_file'])
            # update function metadata with updated value of local_path (which might change between runs)
            fn_data['files'][cn]['local_cache_path'] = local_cache_path

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
                pass
            else:
                fn = getattr(mod, function_name)
                if fn is not None:
                    return fn

    def generate_analytics(self, analytics_modules):
        self.logger.debug("in generate_analytics with available modules: " + ", ".join(
            str(m) for m in analytics_modules))
        for key, kwargs in self.info.get('analytics', []):
            if 'function_name' in kwargs:
                qual_function_name = kwargs['function_name']
                del kwargs['function_name']
            else:
                qual_function_name = key

            if "." in qual_function_name:
                module_name, function_name = qual_function_name.split(".")
            else:
                module_name = None
                function_name = qual_function_name
            self.current_function_name = function_name

            if 'depends' in kwargs:
                depends_on_keys = kwargs['depends']
                depends_on_hashes = [self.template_data[k]['h'] for k in depends_on_keys]
                kwargs['depends'] = depends_on_hashes

            # get function object from function name
            fn = self.get_fn_object(module_name, function_name, analytics_modules)
            if fn is None:
                errmsg_raw = "couldn't find a function %s in modules %s"
                errmsg = errmsg_raw % (function_name, ", ".join(str(m) for m in analytics_modules))
                raise Exception(errmsg)
            self.logger.info("matched function %s to fn %s" % (qual_function_name, str(fn)))

            h = hash_for_fn(fn, kwargs)

            if 'depends' in kwargs:
                del kwargs['depends']

            self.logger.debug("hash for fn %s is %s" % (fn, h))

            self.current_function_data = self.load_function_data_if_cached(h)

            if self.current_function_data is None:
                self.current_function_data = {}
                start_time = time.time()
                # run the actual function
                output = fn(self, **kwargs)
                self.current_function_data['h'] = h
                self.current_function_data['function_elapsed_seconds'] = time.time() - start_time
                self.current_function_data['function_output'] = output
                self.save_function_data(h, self.current_function_data)
            else:
                self.current_function_data['from_cache'] = True

            for filename, file_metadata in self.current_function_data.get('files', {}).items():
                shutil.copyfile(
                    self.cachePath / file_metadata['cache_file'],
                    self.outputPath / filename
                    )

            self.template_data[key] = self.current_function_data

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
        return blob.public_url

    def upload_canonical_file(self, canonical_file):
        local_filepath = self.outputPath / canonical_file
        assert os.path.exists(local_filepath), "no file at %s" % local_filepath
        blob = self.output_storage_bucket.blob(canonical_file)
        blob.upload_from_filename(str(local_filepath))
        return blob.public_url

    def generate_and_upload_file(self, canonical_filename, write_mode='w'):
        """
        Standardize how analytics client libraries should generate additional files.

        Wrap this function to provide more specific utility functions,
        e.g. save_matplotlib_plt
        """
        local_canonical_filepath = self.outputPath / canonical_filename
        h = hash_for_template(canonical_filename, self.template_text())
        ext = os.path.splitext(canonical_filename)[1]
        cache_filename = "%s%s" % (h, ext)
        local_cache_filepath = self.cachePath / cache_filename

        #if os.path.exists(local_cache_filepath):
        #    raise Exception("generating a cache file %s that already exists!" % local_cache_filepath)

        # yield the cache location so file can be written
        with open(local_cache_filepath, write_mode) as f:
            yield h, f

        assert os.path.exists(local_cache_filepath)
        shutil.copyfile(local_cache_filepath, self.outputPath / canonical_filename)

        self.logger.debug("uploading generated %s (%s) to %s" % (canonical_filename, local_cache_filepath, cache_filename))
        blob = self.cache_storage_bucket.blob(cache_filename)
        blob.upload_from_filename(str(local_cache_filepath))

        if self.current_function_data is None:
            return

        if not "files" in self.current_function_data:
            self.current_function_data['files'] = {}

        self.current_function_data['files'][canonical_filename] = {
                'ext' : ext,
                'cache_file' : cache_filename,
                'canonical_name' : canonical_filename,
                'local_canonical_path' : str(local_canonical_filepath),
                'url' : blob.public_url
                }

    def save_plain_text(self, text, canonical_filename):
        for h, f in self.generate_and_upload_file(canonical_filename, 'w'):
            f.write(text)

    def save_dict_as_json(self, info, canonical_filename):
        for h, f in self.generate_and_upload_file(canonical_filename, 'w'):
            json.dump(info, f)

    def save_binary(self, canonical_filename):
        for h, f in self.generate_and_upload_file(canonical_filename, 'wb'):
            yield(h, f)

    def read_binary(self, canonical_filename):
        self.logger.debug("opening file %s in dir %s" % (canonical_filename, self.outputPath))
        with open(self.outputPath / canonical_filename, 'rb') as f:
            yield f

    def save_matplotlib_plt(self, plt, canonical_filename):
        for h, f in self.generate_and_upload_file(canonical_filename, 'wb'):
            plt.savefig(f, dpi=300, bbox_inches='tight')

    # TODO find a nicer way to detect if template file has changed - md5?
    def template_text(self):
        if 'template_file' in self.info:
            with open("templates/%s" % self.info['template_file'], 'r') as f:
                return f.read()
        else:
            return self.info['template']

    def create_document_template(self):
        if 'template_file' in self.info:
            self.logger.info("Loading template from file %s"% self.info['template_file'])
            return self.jinja_env.get_template(self.info['template_file'])
        else:
            self.logger.info("Creating template from string...")
            return self.jinja_env.from_string(self.info['template'])

    def setup_template_environment(self):
        def read_file_contents(path):
            with open(self.outputPath / path, 'r') as f:
                return f.read()
        def load_json(path):
            with open(self.outputPath / path, 'r') as f:
                return json.load(f)
        def fn_params(qual_fn_name, param_name):
            return self.info['analytics'][qual_fn_name][param_name]

        self.template_data['batch'] = self
        self.template_data['keys'] = self.template_data.keys()
        self.template_data['data'] = self.template_data
        self.template_data['read_file_contents'] = read_file_contents
        self.template_data['load_json'] = load_json
        self.template_data['fn_params'] = fn_params
        self.template_data['datetime'] = datetime

    def render_template(self):
        self.setup_template_environment()
        template = self.create_document_template()
        return template.render(self.template_data)

    def render_alternate_template(self, template_name):
        template = self.jinja_env.get_template(template_name)
        return template.render(self.template_data)

    def process_filters(self):
        self.output_documents = []
        template_basename = os.path.splitext(self.template_name)[0]

        # write the template to a file on disk
        # run jinja process
        prev_filename = self.template_name
        canonical_filename = prev_filename

        for h, f in self.generate_and_upload_file(canonical_filename):
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
            self.logger.info("generated %s" % output_filename)

            # upload cache and canonical files
            shutil.copyfile(output_filename, self.cachePath / output_filename)
            self.upload_existing_file(output_filename)
            shutil.copyfile(output_filename, self.outputPath / canonical_filename)
            document_url = self.upload_canonical_file(output_filename)

            self.output_documents.append({'url' : document_url})

            prev_filename = output_filename

        os.chdir(curdir)

        # copy files to local folder named output_bucket_name
        if os.path.exists(self.output_bucket_name):
            print("Folder %s already exists, not copying files. Remove/rename and rerun to copy files to this dir." % self.output_bucket_name)
        else:
            print("Copying files to %s" % self.output_bucket_name)
            shutil.copytree(self.output_dir, self.output_bucket_name)

        # copy files to root of tempdir
        shutil.rmtree(self.tempdirOutputPath)
        shutil.copytree(self.output_dir, self.tempdirOutputPath)

        return self.outputPath / canonical_filename
