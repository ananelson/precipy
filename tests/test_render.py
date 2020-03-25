from precipy.main import render_data
import tests.analytics

def test_render_data():
    config = {
        # The report template
        'template' : """a is {{ wavy_line_plot.args.a }}""",
        # Sources for data prep & asset gen (plots, json data)
        'analytics' : [
            ['wavy_line_plot', {'a' : 7, 'b' : 4}]
            ]
        }

    batch = render_data(config, [tests.analytics])
    final_doc = list(batch.documents.values())[0]
    with open(final_doc.cache_filepath, 'r') as f:
        assert f.read() == "a is 7"
