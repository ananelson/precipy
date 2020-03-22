## Batch

The Batch class encapsulates and orchestrates a single run.

### Initalization

It is initialized with a configuration dictionary:

{{ d['precipy/batch.py|pydoc']['Batch.__init__:source'] | highlight('py') }}

Each batch is given a random UUID which is used to create unique working
directories to separate information from different runs.

The `setup_logging()` method is:

{{ d['precipy/batch.py|pydoc']['Batch.setup_logging:source'] | highlight('py') }}

The `setup_work_dirs()` method is:

{{ d['precipy/batch.py|pydoc']['Batch.setup_work_dirs:source'] | highlight('py') }}

Precipy is designed to be strongly integrated with cloud storage, so that multiple people can work on a single document and only one of them needs to be able to run analytics functions. Storage functionality is encapsulated by the Storage class and its subclasses.

And finally, the `setup_document_template()` method is:

{{ d['precipy/batch.py|pydoc']['Batch.setup_document_template:source'] | highlight('py') }}

### Analytics

After initialization, the next stage is to run all analytics functions. These are the functions that do all data analysis and generate any assets you wish to incorporate in your documents.

The main `generate_analytics()` method iterates over each entry in the analytics configuration:

{{ d['precipy/batch.py|pydoc']['Batch.generate_analytics:source'] | highlight('py') }}

For each entry in the analytics list, the `process_analytics_entry()` method is called:

{{ d['precipy/batch.py|pydoc']['Batch.process_analytics_entry:source'] | highlight('py') }}

The `resolve_function()` method first returns a reference to the function object wrapped in an AnalyticsFunction objet wrapper:

{{ d['precipy/batch.py|pydoc']['Batch.resolve_function:source'] | highlight('py') }}


##### Hash Code

Validity is determined by generating a hash incorporating the function's source code, the arguments it is called with, and the source code of the Precipy system itself:


Here is the `hash_for_fn()` method:

{{ d['precipy/identifiers.py|pydoc']['hash_for_fn:source'] | highlight('py') }}

And the `hash_for_dict()` method it calls:

{{ d['precipy/identifiers.py|pydoc']['hash_for_dict:source'] | highlight('py') }}


#### 


## Analytics Function

The AnalyticsFunction class encapsulates running and caching the output from analytics functions.

{{ d['precipy/analytics_function.py|pydoc']['AnalyticsFunction.__init__:source'] | highlight('py') }}

On initialization, a hash code is set for caching the results of this function:

{{ d['precipy/analytics_function.py|pydoc']['AnalyticsFunction.generate_hash:source'] | highlight('py') }}


### Supplemental Files

Each function tracks various data files generated as a result of running the
function. The `metadata.pkl` is used to store information about the function
itself, and if the `metadata.pkl` file is present in the cache, then the
function will not be run again.

The SupplementalFile class is a lightweight class for easy access to attributes:

{{ d['precipy/analytics_function.py|pydoc']['SupplementalFile:source'] | highlight('py') }}



### Foo


The function object can be called by calling the `call_function()` method:

{{ d['precipy/analytics_function.py|pydoc']['AnalyticsFunction.call_function:source'] | highlight('py') }}

In practice, we want to call it with the `run_function()` method which adds some other metadata:

{{ d['precipy/analytics_function.py|pydoc']['AnalyticsFunction.run_function:source'] | highlight('py') }}

