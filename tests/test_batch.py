from precipy.batch import Batch
import tests.analytics
import os

config = {
    # The report template
    'template' : """a is {{ wavy_line_plot.args.a }}""",
    "filters" : [["markdown", "html"]],
    # Sources for data prep & asset gen (plots, json data)
    'analytics' : [
        ['wavy_line_plot', {'a' : 7, 'b' : 4}]
        ]
    }

def test_batch():
    batch = Batch({})
    assert batch.h
    assert os.path.exists(batch.cachePath)

def test_batch_integration():
    batch = Batch(config)
    batch.generate_analytics([tests.analytics])
    batch.generate_documents()

    print("Functions")
    print(batch.functions)
    print("documents")
    print(batch.documents)

    h, text = batch.render_text_template()
    print(batch.documents)

    assert batch.template_filenames == ["%s.md" % batch.h]
