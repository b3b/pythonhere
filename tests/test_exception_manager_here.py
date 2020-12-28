import pytest
from exception_manager_here import (
    UnhandledExceptionPopupHere,
    show_exception_popup,
)


@pytest.mark.asyncio
async def test_exception_popup_shown(app_instance):
    show_exception_popup(Exception())
    assert isinstance(app_instance._app_window.children[0], UnhandledExceptionPopupHere)


@pytest.mark.asyncio
async def test_popup_shown_on_app_exception(app_instance, there):
    assert app_instance.get_running_app()
    await there.runcode("from kivy.clock import Clock")
    await there.runcode("Clock.schedule_once(lambda dt: 1 / 0, -1)")
    await there.runcode("Clock.idle()")
    assert isinstance(app_instance._app_window.children[0], UnhandledExceptionPopupHere)
