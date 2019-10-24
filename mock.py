import json
class Request(object):
    def __init__(self, filepath):
        with open(filepath, 'r') as f:
            self.info = json.load(f)

    def get_json(self):
        return self.info
