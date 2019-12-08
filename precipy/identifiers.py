import precipy.batch as batch
import hashlib
import inspect

def cache_filename_for_fn(h):
    return "%s.json" % h

def hash_for_dict(info_dict):
    description = u";".join("%s: %s" % (k, v) 
            for k, v in info_dict.items())
    #print()
    #print("generatimg hash from")
    #print(sorted(info_dict.keys()))
    #print("--------------------------------------------------")
    #print(description)
    #print()
    return hashlib.sha256(description.encode('utf-8')).hexdigest()

def hash_for_fn(fn, kwargs):
    return hash_for_dict({
            'canonical_function_name' : fn.__name__,
            'batch_source' : inspect.getsource(batch),
            'fn_source' : inspect.getsource(fn),
            'arg_values' : kwargs
            })

def hash_for_template(template_filename, template_text):
    d = { 
            'template_filename' : template_filename,
            'template_contents' : template_text
            }

    return hash_for_dict(d)

def hash_for_doc(canonical_filename, hash_args=None):
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
