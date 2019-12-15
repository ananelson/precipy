import subprocess
from xhtml2pdf import pisa
import markdown
import os

def do_markdown(batch, input_filepath, output_filepath, output_ext, filter_args):
    print("in do_markdown with input %s output %s" % (input_filepath, output_filepath))
    print(os.getcwd())
    with open(input_filepath, 'r') as i_f:
        with open(output_filepath, 'w') as o_f:
            html = markdown.markdown(i_f.read())
            o_f.write(html)
    assert os.path.exists(output_filepath)

def do_xhtml2pdf(batch, input_filepath, output_filepath, output_ext, filter_args):
    with open(input_filepath, 'r') as i_f:
        with open(output_filepath, 'wb') as o_f:
            pisa.CreatePDF(i_f.read(), dest=o_f)

def do_pandoc(batch, input_filepath, output_filepath, output_ext, filter_args):
    subprocess.run(['/opt/local/bin/pandoc', input_filepath, '-o', output_filepath], cwd=batch.cache_dir.name, capture_output=True, check=True)
