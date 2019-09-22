import hashlib
import inspect

def cache_filename_for_fn(h):
    return "%s.json" % h

def cache_info_for_fn(h):
    with open(cache_filename_for_fn(h), 'w') as f:
        f.write()

def hash_for_dict(info_dict):
    description = u";".join("%s: %s" % (k, v) 
            for k, v in info_dict.items())
    print(description)
    return hashlib.sha256(description.encode('utf-8')).hexdigest()

def hash_for_fn(fn, kwargs):
    return hash_for_dict({
            'canonical_filename' : fn.__name__,
            'source' : inspect.getsource(fn),
            'values' : kwargs
            })

def hash_for_item(canonical_filename):
    analytics_frameinfo = inspect.stack()[-2]
    frame = analytics_frameinfo.frame 

    args_dict = {
            'canonical_filename' : canonical_filename,
            'source' : inspect.getsource(frame),
            'values' : inspect.getargvalues(frame)
            }

    description = u";".join("%s: %s" % (k, v) 
            for k, v in args_dict.items())

    return hashlib.sha256(description.encode('utf-8')).hexdigest()
