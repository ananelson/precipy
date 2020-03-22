from precipy.main import render_data
import tests.analytics

def test_render_data():
    config = {
        # The report template
        'template' : """foo is {{ foo }}""",
        # Sources for data prep & asset gen (plots, json data)
        'analytics' : [
            ['wavy_line_plot', {'a' : 7, 'b' : 4}]
            ]
        }

    output_filename = render_data(config, analytics_modules=[tests.analytics])
    with open(output_filename, 'r') as f:
        assert f.read() == "foo is 100"
