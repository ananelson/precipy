from identifiers import hash_for_fn
from jinja2 import Environment, select_autoescape
from storage import load_if_cached
import analytics

# declare 'heavy' resources as globals
jinja_env = None

def init_jinja_env():
    return Environment(
            autoescape=select_autoescape(['html', 'xml'])
            )

def render(request):
    # declare and lazy load globals
    global jinja_env
    if jinja_env is None:
        jinja_env = init_jinja_env()
    # https://cloud.google.com/functions/docs/bestpractices/tips

    request_json = request.get_json()
    bucket_name = request_json.get('bucket_name')

    # process data sources 
    for function_name, kwargs in request_json['analytics']:
        # get function object from function name
        # TODO generalize module name
        fn = getattr(analytics, function_name)

        h = hash_for_fn(fn, kwargs)
        print(h)

        data = load_if_cached("%s.json" % h, bucket_name)
        print(data)

        # look for report from previous run of this hash

    # render the template
    if request.args and 'template' in request.args:
        template_text = request.template
    elif request_json and 'template' in request_json:
        template_text = request_json['template']

    template = jinja_env.from_string(template_text)
    return template.render({'foo' : 200})
