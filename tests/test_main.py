import pytest
from version_here import __version__
from kivy.uix.settings import Settings


def test_dev_version_is_set():
    assert __version__ == "0.0.0"


@pytest.mark.asyncio
async def test_connect_label_shown(app_instance):
    assert "Connect" in app_instance.root.ids.address_info.children[-1].text


@pytest.mark.asyncio
async def test_code_line_executed(capfd, app_instance, there):
    await there.runcode("print('hello there')")
    assert capfd.readouterr().out == "hello there\n"


@pytest.mark.asyncio
async def test_button_created(capfd, app_instance, there):
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
    assert capfd.readouterr().out == "button there\n"


@pytest.mark.asyncio
async def test_root_object_is_in_context(capfd, app_instance, there):
    await there.runcode('print(root)')
    captured = capfd.readouterr()
    assert captured.out.startswith('<kivy.uix.')


@pytest.mark.asyncio
async def test_settings_opened_from_action_bar(app_instance, there):
    assert not isinstance(app_instance.root_window.children[0], Settings)
    await there.runcode("root.ids.settings_action.dispatch('on_press')")
    assert isinstance(app_instance.root_window.children[0], Settings)
