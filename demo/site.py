from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape
from pathlib import Path
from precipy.batch import Batch
from precipy.mock import Request
import cherrypy
import configparser
import jinja2
import json
import requests
import traceback

import analytics
analytics_modules = [analytics]

cf = Path("config")
config = configparser.ConfigParser()
config.read(cf / "site.cfg")

jinja_env = Environment(
        loader = FileSystemLoader("templates/"),
        autoescape=select_autoescape(['html', 'xml'])
        )
site_template = jinja_env.get_template("site.html")

class PrecipySite(object):
    @cherrypy.expose
    def index(self):
        response = requests.get(config['template']['txt_url'])
        template_text = response.text

        # save a backup in case the online file disappears
        if 'backup_to' in config['template']:
            with open(config['template']['backup_to'], 'w') as f:
                f.write(template_text)

        request = Request(cf / config['precipy']['config_file'], template_text)
        batch = Batch(request)
        batch.generate_analytics(analytics_modules)

        render_args = {
                "config" : json.dumps(batch.info['analytics'], sort_keys=True, indent=4),
                'editor_url' : config['template']['editor_url'],
                }

        try:
            batch.process_filters()
            render_args['menu'] = batch.render_alternate_template("menu.html")
            render_args["rendered_document"] = batch.output_documents[-1]['url']
        except jinja2.exceptions.TemplateError as e:
            print("jinja exception occurred")
            print(str(e))
            render_args['jinjs_exception'] = traceback.format_exc(limit=-2)

        return site_template.render(render_args)


cherrypy.config.update(str(cf / config['cherrypy']['server_conf']))
cherrypy.tree.mount(PrecipySite(), '/', {})

cherrypy.engine.start()
cherrypy.engine.block()
