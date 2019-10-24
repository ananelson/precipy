import subprocess

def do_pandoc(batch, input_filepath, output_filepath, output_ext, filter_args):
    p = subprocess.run(['which', 'pandoc'], capture_output=True)
    print(p.stderr)
    print(p.stdout)

    p = subprocess.run(['/opt/local/bin/pandoc', input_filepath, '-o', output_filepath], cwd=batch.workdir.name, capture_output=True, check=True)
    print(p.stderr)
    print(p.stdout)
