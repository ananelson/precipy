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
    print()
    print("generatimg hash from")
    print(description)
    print()
    return hashlib.sha256(description.encode('utf-8')).hexdigest()

def hash_for_fn(fn, kwargs):
    return hash_for_dict({
            'canonical_function_name' : fn.__name__,
            'batch_source' : inspect.getsource(batch),
            'fn_source' : inspect.getsource(fn),
            'arg_values' : kwargs
            })

def hash_for_item(canonical_filename):
    analytics_frameinfo = inspect.stack()[2]
    frame = analytics_frameinfo.frame 

    print()
    print("analytics frame:")
    print(frame)
    print()

    return hash_for_dict({
            'canonical_filename' : canonical_filename,
            'batch_source' : inspect.getsource(batch),
            'frame_source' : inspect.getsource(frame),
            'values' : inspect.getargvalues(frame)
            })
