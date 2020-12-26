"""%there magic Python code shortcuts."""
# pylint: disable=invalid-name

import click
from herethere.there.commands import there_code_shortcut

KV_COMMAND_TEMPLATE = r"""
from window_here import load_kv_string
load_kv_string(r'''{code} ''', clear_style={clear_style})
"""


@there_code_shortcut
@click.option(
    "-c", "--clear-style", is_flag=True, help="Unload previously applied rules."
)
def kv(code: str, clear_style: bool) -> str:
    """Insert given rules into the Kivy Language Builder.

    :param code: KV language rules
    """
    code = "# %%there ... \n" + code.replace("'''", '"""')
    return KV_COMMAND_TEMPLATE.format(code=code, clear_style=clear_style)
