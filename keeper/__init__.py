"""Application initialization.
"""

__all__ = ('__version__', 'flask_app')

from .version import get_version
from .appfactory import create_flask_app


__version__ = get_version()

flask_app = create_flask_app()
