"""
Example main.py functions.

You need to write your own python script so you can import analytics modules and then pass them as a list.

It is recommended to import render_file from here into your script.
"""

from precipy.batch import Batch
import json

def render_file(filepath, analytics_modules, storages=None, custom_render_fns=None):
    with open(filepath, 'r') as f:
        info = json.load(f)
    return render_data(info, analytics_modules, 
            storages=storages,
            custom_render_fns=custom_render_fns)

def render_data(info, analytics_modules, storages=None, custom_render_fns=None):
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
    batch = Batch(info)
    batch.generate_analytics(analytics_modules)
    batch.generate_documents()
    print("abuot to publish documents...")
    batch.publish_documents()
    return batch
