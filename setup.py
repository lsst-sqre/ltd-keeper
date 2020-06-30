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
    'Development Status :: 5 - Production/Stable',
    'Programming Language :: Python :: 3.6',
    'License :: OSI Approved :: MIT License',
    'Framework :: Flask',
    'Intended Audience :: Science/Research',
    'Topic :: Documentation',
],
keywords = 'lsst lsst-the-docs'

# Setup-time requirements
setup_requires = [
    'setuptools_scm==1.15.6',
    'pytest-runner==5.1',
]

# Installation (application runtime) requirements
install_requires = [
    'Flask==1.0.3',
    'uWSGI==2.0.18',
    'Flask-SQLAlchemy==2.4.0',
    'SQLAlchemy==1.3.4',
    'PyMySQL==0.9.3',
    'Flask-HTTPAuth==3.3.0',
    'Flask-Migrate==2.5.2',
    'flask-accept==0.0.6',
    'python-dateutil==2.4.2',
    'boto3==1.9.168',
    'requests==2.22.0',
    'structlog==17.2.0',
    'celery[redis]==4.2.0'
]

# Test dependencies
tests_require = [
    'pytest==5.4.3',
    'pytest-cov==2.10.0',
    'pytest-flake8==1.0.6',
    'responses==0.10.6',
    'pytest-mock==3.1.1',
    'mock==4.0.2',
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
    'dev': ['httpie', 'flower==0.9.2'] + docs_require + tests_require
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
