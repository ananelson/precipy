from main import render

def test_render_template():
    response = render(MockRequest({
        # The report template
        'template' : """

        show me the plot {{ plot('two_subplots.png') }}
        foo is {{ foo }}

        """,
        # Sources for data prep & asset gen (plots, json data)
        'analytics' : [
            ['wavy_line_plot', {'a' : 7, 'b' : 4}]
            ]
        }))
    assert response == "foo is 100"

class MockRequest(object):
    def __init__(self, data):
        self.data = data
        self.args = None

    def get_json(self):
        return self.data
