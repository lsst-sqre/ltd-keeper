#!/usr/bin/env python

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


setup(
    name='lsst-the-docs-keeper',
    description='LSST the Docs API server',
    long_description=read_file('README.rst'),
    url='https://ltd-keeper.lsst.io',
    author='Association of Universities for Research in Astronomy, Inc.',
    author_email='jsick@lsst.org',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: MIT License',
        'Framework :: Flask',
        'Intended Audience :: Science/Research',
        'Topic :: Documentation',
    ],
    keywords='lsst lsst-the-docs',
    packages=find_packages(exclude=('tests',)),
    use_scm_version=True,
    setup_requires=[
        'setuptools_scm==1.15.6'
    ],
    install_requires=[
        'Flask==0.10.1',
        'uWSGI==2.0.15',
        'Flask-SQLAlchemy==2.1',
        'PyMySQL==0.7.6',
        'Flask-HTTPAuth==2.2.1',
        'Flask-Script==2.0.5',
        'Flask-Migrate==1.8.0',
        'python-dateutil==2.4.2',
        'boto3==1.2.3',
        'requests==2.10.0',
    ],
    extras_require={
        'dev': [
            'pytest==3.2.5',
            'pytest-cov==2.4.0',
            'pytest-flake8==0.9.1',
            'responses==0.5.1',
            'Sphinx==1.5.1',
            'sphinx-rtd-theme==0.1.9',
            'numpydoc==0.5',
            'sphinxcontrib-httpdomain==1.4.0',
            'httpie'],
    },
    entry_points={
        'console_scripts': []
    }
)
