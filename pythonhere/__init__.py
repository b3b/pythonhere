"""PythonHere Jupyter magic."""
from herethere.magic import load_ipython_extension

from .magic_here import shortcuts  # noqa
from .version_here import __version__  # noqa


__all__ = ("load_ipython_extension",)
