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

# Setup-time requirements
setup_requires = [
    "setuptools_scm==1.15.6",
    "pytest-runner==5.1",
]

# Installation (application runtime) requirements
install_requires = []

# Test dependencies
tests_require = []

# Sphinx documentation requirements
docs_require = []

# Optional installation dependencies
extras_require = {
    # Recommended extra for development
    "dev": []
}

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
    setup_requires=setup_requires,
    tests_require=tests_require,
    install_requires=install_requires,
    extras_require=extras_require,
)
