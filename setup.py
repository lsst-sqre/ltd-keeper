import os

from setuptools import find_packages, setup


def read_file(filename):
    """Read a file in the package."""
    full_filename = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), filename
    )
    with open(full_filename) as f:
        content = f.read()
    return content


name = "lsst-the-docs-keeper"
description = "LSST the Docs API server"
long_description = read_file("README.rst")
url = "https://ltd-keeper.lsst.io"
author = "Association of Universities for Research in Astronomy, Inc."
author_email = "jsick@lsst.org"
license = "MIT"
classifiers = (
    [
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: MIT License",
        "Framework :: Flask",
        "Intended Audience :: Science/Research",
        "Topic :: Documentation",
    ],
)
keywords = "lsst lsst-the-docs"

setup(
    name=name,
    description=description,
    long_description=long_description,
    url=url,
    author=author,
    author_email=author_email,
    license=license,
    classifiers=classifiers,
    keywords=keywords,
    packages=find_packages(exclude=("tests",)),
    use_scm_version=True,
)
