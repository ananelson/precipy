"""
Example main.py functions.

You need to write your own python script so you can import analytics modules and then pass them as a list.

It is recommended to import render_file from here into your script.
"""
from precipy.batch import Batch
import importlib
import json
import sys


def render_file(filepath, raw_analytics_modules, storages=None, custom_render_fns=None):
    with open(filepath, 'r') as f:
        info = json.load(f)
    return render_data(info, raw_analytics_modules,
            storages=storages,
            custom_render_fns=custom_render_fns)

def import_module_or_file(ram):
    try:
        return importlib.import_module(ram)
    except ModuleNotFoundError:
        spec = importlib.util.spec_from_file_location(ram, "%s.py" % ram)
        module = importlib.util.module_from_spec(spec)
        sys.modules[ram] = module
        spec.loader.exec_module(module)
        return module

def render_data(info, raw_analytics_modules, storages=None, custom_render_fns=None):
    """
    Runs all analytics then generates any reports, per the configuration file specified by filepath.

    Requires a list of python modules which will be searched for analytics functions specified in configuration file.

    You can provide additional document rendering tools via custom_render_fns which should be a list of functions.
    Function names should be of the form do_x where x is the name of the document filter, e.g. do_markdown
    See precipy/output_filters.py for examples.
    """
    if custom_render_fns:
        info['custom_render_fns'] = custom_render_fns
    if storages:
        info['storages'] = storages

    analytics_modules = []
    for ram in raw_analytics_modules:
        if isinstance(ram, str):
            am = import_module_or_file(ram)
        else:
            am = ram
        analytics_modules.append(am)

    batch = Batch(info)
    batch.run(analytics_modules)
    return batch
