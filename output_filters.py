import pypandoc

def do_pandoc(batch, input_filepath, output_filepath):
    pypandoc.convert_file(input_filepath, outputfile=output_filepath)
    #subprocess.run(['pandoc', input_filepath, '-o', output_filepath], cwd=batch.workdir.name, capture_output=False, check=True)
