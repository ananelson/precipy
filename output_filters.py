import pypandoc
import os

def do_pandoc(batch, input_filepath, output_filepath, output_ext, args):
    curdir = os.getcwd()
    os.chdir(batch.workdir.name)
    pypandoc.convert_file(input_filepath, output_ext, outputfile=output_filepath)
    os.chdir(curdir)
