"""PythonHere Jupyter magic."""

from herethere.magic import load_ipython_extension as load_herethere_extension

from .magic_here import shortcuts  # noqa
from .magic_here.prompts import register_pythonhere_ai_prompts
from .version_here import __version__  # noqa

__all__ = ("load_ipython_extension",)


def load_ipython_extension(ipython):
    """Hook for `%load_extension pythonhere`."""
    register_pythonhere_ai_prompts()
    load_herethere_extension(ipython)
