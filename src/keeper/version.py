"""Access app version string.
"""

__all__ = ['get_version']

from pkg_resources import get_distribution, DistributionNotFound


def get_version():
    """Get the app version.

    Returns
    -------
    version : `str`
        Semantic version string, matching the package version.
        See https://github.com/pypa/setuptools_scm for details on the
        semantic version formatting used.
    """
    try:
        return get_distribution('lsst-the-docs-keeper').version
    except DistributionNotFound:
        # Package is not installed
        return '0.0.0'
