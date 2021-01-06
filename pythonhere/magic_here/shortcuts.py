"""%there magic Python code shortcuts."""
# pylint: disable=invalid-name

from base64 import b64decode
from io import BytesIO, StringIO

from PIL import Image as PILImage
from IPython.display import display
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
    """Insert given rules into the Kivy Language Builder."""
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

    img = PILImage.open(BytesIO(data)).convert("RGB")
    if width:
        height = int(width * img.size[1] // img.size[0])
        img = img.resize((width, height), PILImage.ANTIALIAS)

    if output:
        img.save(output)
        output.close()

    display(img)
