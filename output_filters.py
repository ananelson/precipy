import subprocess
from xhtml2pdf import pisa
import markdown

def do_markdown(batch, input_filepath, output_filepath, output_ext, filter_args):
    with open(input_filepath, 'r') as i_f:
        with open(output_filepath, 'w') as o_f:
            html = markdown.markdown(i_f.read())
            o_f.write(html)

def do_xhtml2pdf(batch, input_filepath, output_filepath, output_ext, filter_args):
    with open(input_filepath, 'r') as i_f:
        with open(output_filepath, 'wb') as o_f:
            pisaStatus = pisa.CreatePDF(i_f.read(), dest=o_f)
            print(pisaStatus)

def do_pandoc(batch, input_filepath, output_filepath, output_ext, filter_args):
    p = subprocess.run(['/opt/local/bin/pandoc', input_filepath, '-o', output_filepath], cwd=batch.workdir.name, capture_output=True, check=True)
    print(p.stderr)
    print(p.stdout)
