from pathlib import Path
from precipy.identifiers import FileType
from precipy.identifiers import GeneratedFile
from precipy.identifiers import hash_for_fn
from precipy.identifiers import hash_for_supplemental_file
import os
import pickle
import shutil
import tempfile
import time
import inspect

class AnalyticsFunction(object):
    metadata_filename = "metadata.pkl"
    metadata_keys = ["function_name", "function_source", "function_output", "kwargs", "files", "function_elapsed_seconds"]

    def __init__(self, fn, kwargs, key=None, previous_functions=None, storages=None, cachePath=None, constants=None):
        """
        Arguments:

            fn - a function object representing the analytics function to be called
            kwargs - a dictionary of argument names and values to be passed to the function when called
            previous_functions - a dictionary of function keys:hashcodes for previously run functions
            cachePath - an optional Path object representing the Batch's cache path, can be blank for testing
        """
        self.is_populated = False
        self.key = key or fn.__name__
        self.fn = fn
        for k, v in (constants or {}).items():
            self.fn.__globals__[k] = v
        self.kwargs = kwargs
        self.args = self.kwargs
        self.previous_functions = previous_functions or []
        self.generate_hash(self.fn, self.kwargs)
        self.set_cache_path(cachePath)
        self.setup_files()
        self.function_output = None
        self.storages = storages or []

    def function_name(self):
        return self.fn.__name__

    def function_source(self):
        return inspect.getsource(self.fn)

    def generate_hash(self, fn, kwargs):
        """
        Set the .h attribute containing a caching hash which will be different
        if the function source code, arguments, or dependencies change.
        """
        self.depends_function_hashes = None
        if 'depends' in kwargs:
            self.depends_function_keys = kwargs['depends']
            self.depends_function_hashes = [self.previous_functions[k] for k in self.depends_function_keys]
            del kwargs['depends']

        self.h = hash_for_fn(fn, kwargs, self.depends_function_hashes)
            
    def set_cache_path(self, cachePath):
        """
        Utility for setting a safe cachePath when one is not supplied - intended for testing.
        """
        if cachePath == None:
            tempdir = tempfile.gettempdir()
            cachePath = Path(tempdir) / "precipy" / "cache"
        self.cachePath = cachePath

    def setup_files(self):
        self.files = {}
        if not self.metadata_filename in self.files:
            self.files[self.metadata_filename] = GeneratedFile(self.metadata_filename, self.h,
                    FileType.METADATA, cache_filepath = self.metadata_cache_filepath())

    def cache_dir(self, h):
        """
        Returns a Path to the directory in which a cache file should be stored,
        creating the directory if it doesn't exist.
        """
        prefix = h[0:2]
        parent_dir = self.cachePath / prefix
        os.makedirs(parent_dir, exist_ok=True)
        return parent_dir

    def call_function(self):
        return self.fn(self, **self.kwargs)

    def run_function(self):
        start_time = time.time()
        self.function_output = self.call_function()
        self.function_elapsed_seconds = time.time() - start_time
        self.save_metadata()
        return self.function_metadata()

    def upload_to_storages(self, canonical_filename, cache_filepath):
        for storage in self.storages:
            public_url = storage.upload_cache(cache_filepath)
            self.files[canonical_filename].public_urls.append(public_url)

    def download_from_storages(self, cache_filepath):
        for storage in self.storages:
            if storage.download_cache(cache_filepath):
                return True
        return False

    def function_metadata(self):
        def get_or_run_attr(self, key):
            attr = getattr(self, key, None)
            if callable(attr):
                return attr()
            else:
                return attr
        return dict((k, get_or_run_attr(self, k)) for k in self.metadata_keys)

    def metadata_cache_filename(self):
        return "%s.pkl" % self.h

    def metadata_cache_filepath(self):
        return self.cache_dir(self.h) / self.metadata_cache_filename()

    def metadata_path_exists(self):
        return os.path.exists(self.metadata_cache_filepath())

    def save_metadata(self):
        filepath = self.metadata_cache_filepath()
        with open(filepath, 'wb') as f:
            pickle.dump(self.function_metadata(), f)
        self.upload_to_storages(self.metadata_filename, filepath)
    
    def read_metadata(self):
        with open(self.metadata_cache_filepath(), 'rb') as f:
            return pickle.load(f)

    def load_metadata(self):
        meta = self.read_metadata()
        for k, v in meta.items():
            setattr(self, k, v)
        self.is_populated = True
        return meta

    def supplemental_file_hash(self, canonical_filename, fn_h=None):
        return hash_for_supplemental_file(canonical_filename, fn_h or self.h)

    def supplemental_file_cache_filepath(self, canonical_filename, fn_h=None):
        ext = os.path.splitext(canonical_filename)[1]
        h = self.supplemental_file_hash(canonical_filename, fn_h)
        cache_filename = "%s%s" % (h, ext)
        return self.cache_dir(h) / cache_filename

    def generate_file(self, canonical_filename, mode='w'):
        cache_filepath = self.supplemental_file_cache_filepath(canonical_filename)
        with open(cache_filepath, mode) as f:
            yield f
        self.append_generated_file(canonical_filename)

    def add_existing_file(self, filepath, canonical_filename=None, remove=False):
        if canonical_filename is None:
            canonical_filename = os.path.basename(filepath)
        cache_filepath = self.supplemental_file_cache_filepath(canonical_filename)
        shutil.copyfile(filepath, cache_filepath)
        self.append_generated_file(canonical_filename)
        if remove:
            os.remove(filepath)

    def path_to_cached_file(self, canonical_filename, fn_key=None):
        if fn_key:
            fn_h = self.previous_functions[fn_key]
        else:
            fn_h = self.h
        return self.supplemental_file_cache_filepath(canonical_filename, fn_h)

    def read_file(self, canonical_filename, fn_key=None, mode='r'):
        cache_filepath = self.path_to_cached_file(canonical_filename, fn_key) 
        with open(cache_filepath, mode) as f:
            yield f

    def append_generated_file(self, canonical_filename):
        """
        Adds file to list of supplemental files.
        """
        # verify that file exists in cache already
        filepath = self.supplemental_file_cache_filepath(canonical_filename)
        assert os.path.exists(filepath), "file must be in cache before calling append_generated_file"

        h = self.supplemental_file_hash(self.h, canonical_filename)
        self.files[canonical_filename] = GeneratedFile(canonical_filename, h, cache_filepath = filepath)

        self.upload_to_storages(canonical_filename, filepath)
