## Precipy

A cloud-enabled, analytics-focused document generation tool from the author of [dexy.it](Dexy).

## Example Usage

See demo/ directory for an example.

Your data analysis scripts should be imported into a script like main.py
(filename does not matter), and a list of references to these modules should be
passed to the `batch.generate_analytics` function.

`hello.json` contains an example configuration.

Each configuration file is for a single document.

## Config Options

### `cache_bucket_name`

Name of google cloud storage bucket to hold cache files (will be created if doesn't exist).

### `output_bucket_name`

Name of google cloud storage bucket to hold final output files (will be created if doesn't exist).

### `logfile`

If specified, logs will be written to this file. Can also specify `loglevel`.

### `analytics`

A list of (key, args) tuples representing functions to be called in the analytics phase of document generation.

Functions will be called in the order listed. Function results will be cached if nothing has changed since the last time they were run. To indicate that a function should be re-run if another function changes, use the 'depends' argument below.

The `key` may be a function name (optionally qualified with `module:function_name` if necessary), or any other unique key. If key is not the function name then `function_name` must be specified in args.

The `args` dict is primarily for specifying named arguments to be passed to the function when called.

You can also pass some special arguments:

function_name: to specify the name of the function to be called, where the key isn't a function name

depends: a list of other keys on which this function depends, and if they are not cached this function should be re-run

### `template_file`

Name of template file. Templates use jinja2 templating system. hello.md template has an example of navigating the generated files to create an automated catalog of assets. In practice you would directly reference the canonical names of files you are generating.

### `filters`

List of (filter, output_ext) tuples representing filters to be run after templating is complete, to convert document to different formats.
