import pytest
from io import StringIO
from contextlib import redirect_stdout
from version_here import __version__


def test_dev_version_is_set():
    assert __version__ == "0.0.0"


@pytest.mark.asyncio
async def test_connect_label_shown(app_instance):
    assert "Connect" in app_instance.root.children[-2].text


@pytest.mark.asyncio
async def test_code_line_executed(app_instance, there):
    out = StringIO()
    with redirect_stdout(out):
        await there.runcode("print('hello there')")
    assert out.getvalue() == "hello there\n"


@pytest.mark.asyncio
async def test_button_created(app_instance, there):
    out = StringIO()
    with redirect_stdout(out):
        await there.runcode(
            "\n".join(
                (
                    "from kivy.app import App",
                    "from kivy.uix.button import Button",
                    "app = App.get_running_app()",
                    "root = app.root",
                    "root.add_widget(Button(text='button there'))",
                    "print(root.children[0].text)",
                )
            )
        )
    assert out.getvalue() == "button there\n"
