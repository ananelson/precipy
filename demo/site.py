from pathlib import Path
from precipy.batch import Batch
from precipy.mock import Request
import cherrypy
import os
import requests
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape

import analytics
analytics_modules = [analytics]

TEMPLATE_BACKUP = "precipy_test_backup.md"
TEMPLATE_EDITOR_URL = "https://etherpad.wikimedia.org/p/precipy_test"
TEMPLATE_URL = "https://etherpad.wikimedia.org/p/precipy_test/export/txt"
CONFIG_PATH = "html_only.json"
OUTPUT_DIR = "precipy_demo_output"
STATIC_DIR = Path(os.getcwd()) / "static"

jinja_env = Environment(
    loader = FileSystemLoader("templates/"),
    autoescape=select_autoescape(['html', 'xml'])
    )

class PrecipySite(object):
    @cherrypy.expose
    def index(self):
        response = requests.get(TEMPLATE_URL)
        template_text = response.text

        # save a backup in case the online file disappears
        with open(TEMPLATE_BACKUP, 'w') as f:
            f.write(template_text)

        request = Request(CONFIG_PATH, template_text)
        batch = Batch(request)
        batch.generate_analytics(analytics_modules)
        batch.process_filters()

        site_template = jinja_env.get_template("site.html")

        return site_template.render({
                "editor_url" : TEMPLATE_EDITOR_URL,
                "rendered_document" : batch.output_documents[-1]['url']
                })

cherrypy.config.update('server.conf')
cherrypy.tree.mount(PrecipySite(), '/', {})

cherrypy.engine.start()
cherrypy.engine.block()
