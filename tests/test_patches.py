import pytest
from version_here import __version__

from kivy.factory import Factory


@pytest.mark.asyncio
async def test_factory_patch_applied(capfd, app_instance, there):
    await there.runcode("from kivy.lang import Builder")
    await there.runcode("from kivy.uix.label import Label")

    await there.runcode("class T0(Label):\n    text = 'first'")
    await there.runcode("Builder.load_string('T0:')")

    await there.runcode("class T0(Label):\n    text = 'second'")
    await there.runcode("t0 = Builder.load_string('T0:')")

    await there.runcode("print(t0.text)")
    captured = capfd.readouterr()
    assert captured.out == "second\n"


@pytest.mark.asyncio
async def test_builderbase_match_patch_applied(capfd, app_instance, there):
    await there.runcode("from kivy.lang import Builder")
    await there.runcode("Builder.load_string('<T1@Label>:\\n    pos_x: 10', filename='1234')")
    await there.runcode("Builder.load_string('<T1@Label>:\\n    pos_y: 20', filename='12345')")

    await there.runcode("t1 = Builder.load_string('T1:', filename='123456')")
    await there.runcode("print(t1.pos_y)")
    captured = capfd.readouterr()
    assert captured.out == "20\n"

    await there.runcode("print(t1.pos_x)")
    captured = capfd.readouterr()
    assert 'AttributeError' in captured.err
