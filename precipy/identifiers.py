import hashlib
import inspect
from enum import Enum
import os

class FileType(Enum):
    ANALYTICS = "analytics"
    METADATA = "metadata"
    TEMPLATE = "template"
    DOCUMENT = "document"

class GeneratedFile(object):
    def __init__(self, canonical_filename, h, file_type=FileType.ANALYTICS, cache_filepath=None):
        self.canonical_filename = canonical_filename
        self.h = h
        self.file_type = file_type
        self.cache_filepath = cache_filepath
        self.ext = os.path.splitext(canonical_filename)[1]
        self.public_urls = []

def hash_for_dict(info_dict):
    description = u";".join("%s: %s" % (k, info_dict)
            for k in sorted(info_dict))
    return hashlib.sha256(description.encode('utf-8')).hexdigest()

def hash_for_fn(fn, kwargs, depends=None):
    import precipy.batch as batch
    import precipy.analytics_function as analytics_function
    return hash_for_dict({
            'canonical_function_name' : fn.__name__,
            'fn_source' : inspect.getsource(fn),
            'depends' : depends,
            'arg_values' : kwargs,
            'batch_source' : inspect.getsource(batch),
            'analytics_function_source' : inspect.getsource(analytics_function)
            })

def hash_for_supplemental_file(canonical_filename, fn_h):
    return hash_for_dict({
        "fn_hash" : fn_h,
        "filename" : canonical_filename
        })

def hash_for_template_text(text):
    m = hashlib.md5()
    m.update(text.encode('utf-8'))
    return m.hexdigest()

def hash_for_template_file(filepath):
    m = hashlib.md5()
    with open(filepath, 'rb') as f:
        m.update(f.read())
    return m.hexdigest()

def hash_for_document(template_hash, filter_name, filter_ext, filter_args):
    x = { "template_hash" : template_hash,
          "filter_name" : filter_name,
          "filter_ext" : filter_ext}
    x.update(filter_args)
    return hash_for_dict(x)

def hash_for_doc(canonical_filename, hash_args=None):
    import precipy.batch as batch
    analytics_frameinfo = inspect.stack()[2]
    frame = analytics_frameinfo.frame 

    d = { 
            'canonical_filename' : canonical_filename,
            'batch_source' : inspect.getsource(batch),
            'frame_source' : inspect.getsource(frame),
            'values' : inspect.getargvalues(frame).args
            }

    if hash_args is not None:
        d.update(hash_args)

    return hash_for_dict(d)
