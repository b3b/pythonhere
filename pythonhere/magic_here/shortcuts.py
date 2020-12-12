"""%there magic Python code shortcuts."""
# pylint: disable=invalid-name

import time

import click
from herethere.there.commands import there_code_shortcut

KV_COMMAND_TEMPLATE = r"""
from kivy.lang import Builder
{unload_files}
_pythonhere_new_root = Builder.load_string(r'''{code} ''', filename='{filename}')
if _pythonhere_new_root:
    root.clear_widgets()
    root.add_widget(_pythonhere_new_root)
del _pythonhere_new_root
"""

UNLOAD_KV_FILES_TEMPLATE = (
    "[Builder.unload_file(filename) for filename in "
    "[f for f in Builder.files if (f or '').isdigit()]]"
)


@there_code_shortcut
@click.option(
    "-c", "--clear-style", is_flag=True, help="Unload previously applied rules."
)
def kv(code: str, clear_style: bool) -> str:
    """Insert given rules into the Kivy Language Builder.

    :param code: KV language rules
    """
    unload_files = UNLOAD_KV_FILES_TEMPLATE if clear_style else ""
    code = code.replace("'''", '"""')
    return KV_COMMAND_TEMPLATE.format(
        code=code, unload_files=unload_files, filename=int(time.time())
    )
