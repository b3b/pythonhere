"""%there magic Python code shortcuts."""
# pylint: disable=invalid-name

from base64 import b64decode
from io import StringIO

from IPython.display import Image, display
import click
from herethere.there.commands import there_group, there_code_shortcut


KV_COMMAND_TEMPLATE = r"""
from window_here import load_kv_string
load_kv_string(r'''{code} ''', clear_style={clear_style})
"""

SCREENSHOT_COMMAND_TEMPLATE = """
import sys
from window_here import encoded_screenshot
sys.stderr.write(encoded_screenshot())
"""


@there_code_shortcut
@click.option(
    "-c", "--clear-style", is_flag=True, help="Unload previously applied rules"
)
def kv(code: str, clear_style: bool) -> str:
    """Insert given rules into the Kivy Language Builder.

    :param code: KV language rules
    """
    code = "# %%there ... \n" + code.replace("'''", '"""')
    return KV_COMMAND_TEMPLATE.format(code=code, clear_style=clear_style)


@there_group.command()
@click.pass_context
@click.option(
    "-w",
    "--width",
    type=int,
    default=None,
    help="Width in pixels to which to constrain a displayed image",
)
@click.option(
    "-o",
    "--output",
    type=click.File(mode="wb"),
    default=None,
    help="Path to a local file to save screenshot as PNG image",
)
def screenshot(ctx, width, output):
    """Display the actual image of the Kivy window."""
    out = StringIO()
    err = StringIO()
    ctx.obj.code = SCREENSHOT_COMMAND_TEMPLATE
    ctx.obj.stdout = out
    ctx.obj.stderr = err

    ctx.obj.runcode()
    data = b64decode(err.getvalue())

    if output:
        output.write(data)
        output.close()

    display(Image(data=data, width=width))
