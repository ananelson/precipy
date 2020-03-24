from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape
from pathlib import Path
from precipy.analytics_function import AnalyticsFunction
from precipy.identifiers import FileType
from precipy.identifiers import GeneratedFile
from precipy.identifiers import hash_for_document
from precipy.identifiers import hash_for_template_file
from precipy.identifiers import hash_for_template_text
from uuid import uuid4
import datetime
import glob
import json
import logging
import os
import precipy.output_filters as output_filters
import shutil
import tempfile

class Batch(object):
    def __init__(self, config):
        self.config = config
        self.h = str(uuid4())
        self.setup_logging()
        self.setup_work_dirs()
        self.setup_template_environment()
        self.setup_document_templates()
        self.setup_storages()
        self.functions = {}
        self.documents = {}

    def setup_storages(self):
        self.storages = self.config.get('storages', [])
        for storage in self.storages:
            storage.init(self)
            storage.connect()

    def upload_to_storages(self, canonical_filename, cache_filepath):
        for storage in self.storages:
            public_url = storage.upload_cache(cache_filepath)
            self.documents[canonical_filename].public_urls.append(public_url)

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
        self.outputPath = self.tempdir / self.output_bucket_name / "output"

        os.makedirs(self.cachePath, exist_ok=True)
        shutil.rmtree(self.outputPath, ignore_errors=True)
        os.makedirs(self.outputPath, exist_ok=True)

    def setup_template_environment(self):
        self.template_dir = self.config.get('template_dir', "templates")

        self.jinja_env = Environment(
            loader = FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml']))

        self.template_data = {}

    def setup_document_templates(self):
        self.logger.info("Collecting list of document templates to process...")
        self.template_filenames = []

        for key in ['templates', 'template_file', 'template_files']:
            self.logger.info("Looking for templates specified under config key '%s'" % key)
            entries = self.config.get(key, [])
            if isinstance(entries, str):
                entries = [entries]
            if entries:
                self.logger.info("  found template(s): %s" % ", ".join(entries))
            self.template_filenames += entries

        if "template" in self.config:
            # template content is embedded in config - mostly used for testing
            self.template_filenames += ["%s.md" % self.h]

        if len(self.template_filenames) == 0:
            self.logger.info("No specified templates found, will add all in %s directory" % self.template_dir)
            raw_template_files = glob.glob("%s/*" % self.template_dir)
            if raw_template_files:
                self.logger.info("  found template(s): %s" % ", ".join(raw_template_files))
            self.template_filenames += [f.split("/")[1] for f in raw_template_files]

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
                    if not self.download_from_storages(filepath):
                        raise Exception("Couldn't download storage for %s" % filepath)

        if not af.metadata_path_exists():
            af.run_function()
            af.save_metadata()
            af.from_cache = False
        else:
            if not af.function_output:
                af.load_metadata()

        self.functions[key] = af
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
            cachePath=self.cachePath,
            constants=self.config.get('constants', None)
            )

    def get_fn_object(self, module_name, function_name):
        for mod in self.analytics_modules:
            if module_name != None and mod.__name__ != module_name:
                pass
            else:
                fn = getattr(mod, function_name)
                if fn is not None:
                    return fn

    def populate_template_data(self):
        def read_file_contents(path):
            with open(self.outputPath / path, 'r') as f:
                return f.read()
        def load_json(path):
            with open(self.outputPath / path, 'r') as f:
                return json.load(f)
        def fn_params(qual_fn_name, param_name):
            return self.config['analytics'][qual_fn_name][param_name]

        self.template_data['batch'] = self
        self.template_data['keys'] = self.functions.keys()
        self.template_data['data'] = self.functions

        # functions/modules for use within templates
        self.template_data['read_file_contents'] = read_file_contents
        self.template_data['load_json'] = load_json
        self.template_data['fn_params'] = fn_params
        self.template_data['datetime'] = datetime

    def copy_all_supplemental_files(self):
        """
        Copies all supplemental files to the current working directory.
        """
        for af in self.functions.values():
            for gf in af.files.values():
                shutil.copyfile(gf.cache_filepath, gf.canonical_filename)

    def create_and_populate_work_dir(self, prev_doc):
        workPath = self.cachePath / "docs" / prev_doc.h
        os.makedirs(workPath, exist_ok=True)
        os.chdir(workPath)

        # write the previous document
        shutil.copyfile(prev_doc.cache_filepath, prev_doc.canonical_filename)
        self.copy_all_supplemental_files()

        return workPath

    def render_and_save_template(self, template_file):
        if template_file == "%s.md" % self.h:
            pretty_name = "template.md"
            h, text = self.render_text_template()
        else:
            pretty_name = template_file
            h, text = self.render_file_template(template_file)

        with open(self.cachePath / template_file, 'w') as f:
            f.write(text)

        doc = GeneratedFile(pretty_name, h, file_type=FileType.TEMPLATE,
                cache_filepath=self.cachePath / template_file)
        self.documents[pretty_name] = doc

        return doc

    def generate_documents(self):
        """
        Render all the templates and apply all the document filters on them.
        """
        self.populate_template_data()

        # save current working directory so we can return to it later
        curdir = os.getcwd()
        
        for template_file in self.template_filenames:
            template_doc = self.render_and_save_template(template_file)
            doc = template_doc

            for filter_opts in self.config.get('filters', []):
                workPath = self.create_and_populate_work_dir(doc)

                if len(filter_opts) == 2:
                    filter_name, output_ext = filter_opts
                    filter_args = {}
                else:
                    filter_name, output_ext, filter_args = filter_opts

                filter_doc_hash = hash_for_document(template_doc.h, filter_name, output_ext, filter_args)
                result_filename = "%s.%s" % (os.path.splitext(doc.canonical_filename)[0], output_ext)
                filter_fn = output_filters.__dict__["do_%s" % filter_name]
                filter_fn(doc.canonical_filename, result_filename, output_ext, filter_args)
                
                doc = GeneratedFile(result_filename, filter_doc_hash, file_type=FileType.DOCUMENT, 
                    cache_filepath = workPath / result_filename)
                self.documents[result_filename] = doc
    
                self.upload_to_storages(result_filename, doc.cache_filepath)

        # change back to original working directory
        os.chdir(curdir)

    def publish_documents(self):
        curdir = os.getcwd()
        os.chdir(self.outputPath)

        for doc in self.documents.values():
            shutil.copyfile(doc.cache_filepath, doc.canonical_filename)
        self.copy_all_supplemental_files()

        os.chdir(curdir)
        print(self.outputPath)

    def render_text_template(self):
        template_text = self.config['template']
        h = hash_for_template_text(template_text)
        template = self.jinja_env.from_string(template_text)
        return h, template.render(self.template_data)

    def render_file_template(self, template_file):
        template = self.jinja_env.get_template(template_file)
        h = hash_for_template_file("templates/%s" % template_file)
        return h, template.render(self.template_data)
