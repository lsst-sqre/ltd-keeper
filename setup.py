import os
from setuptools import setup, find_packages


def read_file(filename):
    """Read a file in the package."""
    full_filename = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        filename)
    with open(full_filename) as f:
        content = f.read()
    return content


name = 'lsst-the-docs-keeper'
description = 'LSST the Docs API server'
long_description = read_file('README.rst')
url = 'https://ltd-keeper.lsst.io'
author = 'Association of Universities for Research in Astronomy, Inc.'
author_email = 'jsick@lsst.org'
license = 'MIT'
classifiers = [
    'Development Status :: 5 - Production/Stable'
    'Programming Language :: Python :: 3.5'
    'Programming Language :: Python :: 3.6'
    'License :: OSI Approved :: MIT License'
    'Framework :: Flask'
    'Intended Audience :: Science/Research'
    'Topic :: Documentation'
],
keywords = 'lsst lsst-the-docs'

# Setup-time requirements
setup_requires = [
    'setuptools_scm==1.15.6',
    'pytest-runner==4.2',
]

# Installation (application runtime) requirements
install_requires = [
    'Flask==0.12.2',
    'uWSGI==2.0.17',
    'Flask-SQLAlchemy==2.3.2',
    'PyMySQL==0.8.0',
    'Flask-HTTPAuth==2.2.1',
    'Flask-Script==2.0.5',
    'Flask-Migrate==2.1.1',
    'python-dateutil==2.4.2',
    'boto3==1.2.3',
    'requests==2.18.4',
    'structlog==17.2.0',
]

# Test dependencies
tests_require = [
    'pytest==3.5.0',
    'pytest-cov==2.5.1',
    'pytest-flake8==1.0.0',
    'responses==0.9.0',
]

# Sphinx documentation requirements
docs_require = [
    'Sphinx==1.5.1',
    'sphinx-rtd-theme==0.1.9',
    'numpydoc==0.5',
    'sphinxcontrib-httpdomain==1.4.0',
]

# Optional installation dependencies
extras_require = {
    # Recommended extra for development
    'dev': ['httpie'] + docs_require + tests_require
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
    packages=find_packages(exclude=('tests',)),
    use_scm_version=True,
    setup_requires=setup_requires,
    tests_require=tests_require,
    install_requires=install_requires,
    extras_require=extras_require
)
