import setuptools
from precipy import PRECIPY_VERSION

setuptools.setup(
    name="precipy",
    version=PRECIPY_VERSION,
    author="Ana Nelson",
    author_email="ana@ananelson.com",
    url="https://github.com/ananelson/precipy",
    packages=setuptools.find_packages(),
    install_requires = [
        "jinja2",
        "markdown",
        "pygments"
        ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    scripts = ["bin/precipy"],
    python_requires='>=3.6',
)
