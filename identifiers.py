import batch
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
    return hashlib.sha256(description.encode('utf-8')).hexdigest()

def hash_for_fn(fn, kwargs):
    return hash_for_dict({
            'canonical_function_name' : fn.__name__,
            'batch_source' : inspect.getsource(batch),
            'fn_source' : inspect.getsource(fn),
            'arg_values' : kwargs
            })

def hash_for_item(canonical_filename):
    for s in inspect.stack():
        print("")
        print(str(s))
    analytics_frameinfo = inspect.stack()[-3]
    frame = analytics_frameinfo.frame 

    args_dict = {
            'canonical_filename' : canonical_filename,
            'source' : inspect.getsource(frame),
            'values' : inspect.getargvalues(frame)
            }

    description = u";".join("%s: %s" % (k, v) 
            for k, v in args_dict.items())

    return hashlib.sha256(description.encode('utf-8')).hexdigest()
