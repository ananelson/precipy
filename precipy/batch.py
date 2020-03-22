from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape
from pathlib import Path
from precipy.identifiers import hash_for_template
from precipy.analytics_function import AnalyticsFunction
from uuid import uuid4
import datetime
import json
import logging
import os
import precipy.output_filters as output_filters
import shutil
import tempfile


class Batch(object):
    def __init__(self, config):
        self.config = config
        self.uuid = str(uuid4())
        self.setup_logging()
        self.setup_work_dirs()
        self.setup_document_template()
        self.setup_storages()

    def setup_storages(self):
        self.storages = self.config.get('storages', [])
        for storage in self.storages:
            storage.init(self)
            storage.connect()

    def setup_logging(self):
        self.logger = logging.getLogger(name="precipy")

        if "logfile" in self.config:
            handler = logging.FileHandler(self.config['logfile'])
        else:
            # log to stderr if no logfile specified
            handler = logging.StreamHandler()

        level = self.config.get('loglevel', "INFO")
        handler.setLevel(level)
        self.logger.setLevel(level)

        self.logger.addHandler(handler)
        self.logger.info("logging!")

    def setup_work_dirs(self):
        self.cache_bucket_name = self.config.get('cache_bucket_name', "cache")
        self.output_bucket_name = self.config.get('output_bucket_name', "output")
        self.tempdir = Path(self.config.get('tempdir', tempfile.gettempdir())) / "precipy"

        self.cachePath = self.tempdir / self.cache_bucket_name
        self.outputPath = self.tempdir / self.output_bucket_name / self.uuid

        os.makedirs(self.cachePath, exist_ok=True)
        os.makedirs(self.outputPath, exist_ok=True)

    def setup_document_template(self):
        template_dir = self.config.get('template_dir', "templates")

        self.jinja_env = Environment(
            loader = FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']))

        self.template_data = {}

        if 'template_file' in self.config:
            self.template_name = self.config['template_file']
            self.template_ext = os.path.splitext(self.config['template_file'])[1]
        else:
            self.template_name = "template.md"
            self.template_ext = ".md"

    ## Analytics

    def generate_analytics(self, analytics_modules):
        self.analytics_modules = analytics_modules

        self.logger.debug("in generate_analytics with available modules: " + ", ".join(
            str(m) for m in analytics_modules))

        self.current_function_name = None
        self.current_function_data = None

        previous_functions = {}
        for key, kwargs in self.config.get('analytics', []):
            h = self.process_analytics_entry(key, kwargs, previous_functions)
            previous_functions[key] = h

        self.current_function_name = None
        self.current_function_data = None

    def process_analytics_entry(self, key, kwargs, previous_functions):
        af = self.resolve_function(key, kwargs, previous_functions)

        if not af.metadata_path_exists():
            if af.download_from_storages(af.metadata_cache_filepath()):
                af.load_metadata()
                for sf in af.supplemental_files:
                    filepath = af.supplemental_file_cache_filepath(sf.canonical_filename)
                    print("downloading file for %s" % filepath)
                    if not self.download_from_storages(filepath):
                        raise Exception("Couldn't download storage for %s" % filepath)

        if not af.metadata_path_exists():
            af.run_function()
            af.save_metadata()
            af.from_cache = False
        else:
            if not af.function_output:
                af.load_metadata()

        return af.h

    def resolve_function(self, key, kwargs, previous_functions):
        """
        Determines which function is to be run. Function name is generally the
        key, but if a function_name parameter is passed this is used instead
        (useful if you want to call the same function more than once).
        """

        if 'function_name' in kwargs:
            qual_function_name = kwargs['function_name']
            del kwargs['function_name']
        else:
            qual_function_name = key

        if "." in qual_function_name:
            module_name, function_name = qual_function_name.split(".")
        else:
            module_name, function_name = [None, qual_function_name]

        # get function object from function name
        fn = self.get_fn_object(module_name, function_name)
        if fn is None:
            errmsg_raw = "couldn't find a function %s in modules %s"
            errmsg = errmsg_raw % (function_name, ", ".join(str(m) for m in self.analytics_modules))
            raise Exception(errmsg)
        self.logger.info("matched function %s to fn %s" % (qual_function_name, str(fn)))

        return AnalyticsFunction(fn, kwargs,
            previous_functions=previous_functions, 
            storages=self.storages,
            cachePath=self.cachePath)

    def get_fn_object(self, module_name, function_name):
        for mod in self.analytics_modules:
            if module_name != None and mod.__name__ != module_name:
                pass
            else:
                fn = getattr(mod, function_name)
                if fn is not None:
                    return fn

    def save_function_data(self, h, data):
        hashed_filename = cache_filename_for_fn(h)
        if GOOGLE_CLOUD_AVAILABLE:
            blob = self.cache_storage_bucket.blob(hashed_filename)
    
        fn = self.cachePath / hashed_filename
        with open(fn, 'w') as ff:
            json.dump(data, ff)

        if GOOGLE_CLOUD_AVAILABLE:
            blob.upload_from_filename(str(fn))


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

    # TODO find a nicer way to detect if template file has changed - md5?
    def template_text(self):
        if 'template_file' in self.config:
            with open("templates/%s" % self.config['template_file'], 'r') as f:
                return f.read()
        else:
            return self.config['template']

    def create_document_template(self):
        if 'template_file' in self.config:
            self.logger.info("Loading template from file %s"% self.config['template_file'])
            return self.jinja_env.get_template(self.config['template_file'])
        else:
            self.logger.info("Creating template from string...")
            return self.jinja_env.from_string(self.config['template'])

    def setup_template_environment(self):
        def read_file_contents(path):
            with open(self.outputPath / path, 'r') as f:
                return f.read()
        def load_json(path):
            with open(self.outputPath / path, 'r') as f:
                return json.load(f)
        def fn_params(qual_fn_name, param_name):
            return self.config['analytics'][qual_fn_name][param_name]

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

    def render_filename(self):
        template = self.jinja_env.from_string(self.config['output_basename'])
        return template.render(self.config['analytics'])

    def process_filters(self):
        self.output_documents = []
        template_basename = os.path.splitext(self.template_name)[0]

        # write the template to a file on disk
        # run jinja process
        prev_filename = self.template_name
        canonical_filename = prev_filename

        for h, f in self.generate_and_upload_file(canonical_filename):
            f.write(self.render_template())

        if self.config.get("output_basename"):
            canonical_filename = self.render_filename()

        # then, run any filters on the resulting document
        # save starting working dir so we can go back later
        curdir = os.getcwd()
        os.chdir(self.outputPath)

        for filter_opts in self.config.get('filters', []):
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
            if GOOGLE_CLOUD_AVAILABLE:
                self.upload_existing_file(output_filename)

            shutil.copyfile(output_filename, self.outputPath / canonical_filename)

            if GOOGLE_CLOUD_AVAILABLE:
                document_url = self.upload_canonical_file(output_filename)
                self.output_documents.append({'url' : document_url})

            prev_filename = output_filename

        os.chdir(curdir)

        # copy files to local folder named output_bucket_name
        if os.path.exists(self.output_bucket_name):
            print("Folder %s already exists, not copying files. Remove/rename and rerun to copy files to this dir." % self.output_bucket_name)
        else:
            print("Copying files to %s" % self.output_bucket_name)
            shutil.copytree(self.outputPath, self.output_bucket_name)

        # copy files to root of tempdir
        shutil.rmtree(self.tempdirOutputPath, ignore_errors=True)
        if os.path.exists(self.outputPath):
            print("about to copy files from %s" % self.outputPath)
            shutil.copytree(self.outputPath, self.tempdirOutputPath)

        return self.outputPath / canonical_filename
