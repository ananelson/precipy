import subprocess
from xhtml2pdf import pisa
from weasyprint import HTML
import markdown
import os

def do_markdown(input_filepath, output_filepath, output_ext, filter_args):
    with open(input_filepath, 'r') as i_f:
        with open(output_filepath, 'w') as o_f:
            html = markdown.markdown(i_f.read())
            o_f.write(html)
    assert os.path.exists(output_filepath)

def do_xhtml2pdf(input_filepath, output_filepath, output_ext, filter_args):
    with open(input_filepath, 'r') as i_f:
        with open(output_filepath, 'wb') as o_f:
            pisa.CreatePDF(i_f.read(), dest=o_f)

def do_weasyprint(input_filepath, output_filepath, output_ext, filter_args):
    HTML(input_filepath).write_pdf(output_filepath)

def do_pandoc(input_filepath, output_filepath, output_ext, filter_args):
    subprocess.run(['/opt/local/bin/pandoc', input_filepath, '-o', output_filepath], capture_output=True, check=True)
