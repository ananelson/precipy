from precipy.main import render_data
import tests.analytics

def test_render_data():
    config = {
        # The report template
        'template' : """a is {{ data['wavy_line_plot']['kwargs']['a'] }}""",
        # Sources for data prep & asset gen (plots, json data)
        'analytics' : [
            ['wavy_line_plot', {'a' : 7, 'b' : 4}]
            ]
        }

    batch = render_data(config, analytics_modules=[tests.analytics])
    output_filename = batch.files
    with open(output_filename, 'r') as f:
        assert f.read() == "a is 7"
