from main import render

def test_render_template():
    response = render(MockRequest("foo is {{ foo }}"))
    assert response == "foo is 100"

class MockRequest(object):
    def __init__(self, template_string):
        self.data = {"template" : template_string}
        self.args = {}

    def get_json(self):
        return self.data
