from precipy.analytics_function import AnalyticsFunction
import os

def foo(af):
    return 1

def bar(af):
    with open("hello.txt", 'w') as f:
        f.write("hello!")
    af.add_existing_file("hello.txt")
    os.remove("hello.txt")

def baz(af):
    for f in af.generate_file("hi.txt"):
        f.write("hi!")

    for f in af.generate_file("hola.txt"):
        f.write("hola!")

af = AnalyticsFunction(foo, {})
bf = AnalyticsFunction(bar, {})
cf = AnalyticsFunction(baz, {}, previous_functions={"bar": bf.h})

def test_function_name():
    assert af.function_name() == "foo"
    assert bf.function_name() == "bar"
    assert cf.function_name() == "baz"

def test_function_source():
    assert "def foo" in af.function_source()
    assert "def bar" in bf.function_source()
    assert "def baz" in cf.function_source()

def test_init_analytics_fn():
    assert len(af.h) == 64

def test_cache_filename():
    assert af.metadata_cache_filename().endswith(".pkl")

def test_cache_filepath():
    assert af.metadata_cache_filepath().suffix == ".pkl"
    assert "precipy" in str(af.metadata_cache_filepath())

def test_call_function():
    assert af.call_function() == 1

def test_run_metadata_before_run_function():
    meta = af.function_metadata()
    assert meta['function_output'] == None

def test_run_function():
    af.run_function()
    assert af.function_output == 1
    meta = af.function_metadata()
    print(meta)
    assert meta['function_output'] == 1

def test_add_existing_file():
    bf.call_function()
    sf = bf.files['hello.txt']
    assert sf.canonical_filename == "hello.txt"

def test_generate_file():
    cf.call_function()
    sf = cf.files['hi.txt']
    assert sf.canonical_filename == "hi.txt"

def test_reading_supplemental_files():
    for f in cf.read_file("hello.txt", "bar"):
        text = f.read()
        assert text == "hello!"
    for f in cf.read_file("hi.txt"):
        text = f.read()
        assert text == "hi!"
    for f in cf.read_file("hola.txt"):
        text = f.read()
        assert text == "hola!"

def test_save_metadata():
    cf.save_metadata()
    assert os.path.exists(cf.metadata_cache_filepath())
