import json
class Request(object):
    def __init__(self, filepath, template_text=None):
        with open(filepath, 'r') as f:
            self.info = json.load(f)
        # override template file with template text, if provided
        if template_text is not None:
            self.info['template'] = template_text
            if 'template_file' in self.info:
                del self.info['template_file']

    def get_json(self):
        return self.info
