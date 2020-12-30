import os
from pathlib import Path

import pytest
from herethere.there.commands import ContextObject

from magic_here import shortcuts  # noqa


@pytest.mark.asyncio
async def test_kv_command_runcode_called(call_there_group, mocker):
    runcode = mocker.patch.object(ContextObject, 'runcode', autospec=True)

    call_there_group(["kv"], "Label:")

    runcode.assert_called_once()
    ctx_obj = runcode.call_args[0][0]
    assert "load_kv_string(r'''# %%there ... \nLabel: '''" in ctx_obj.code


@pytest.mark.asyncio
async def test_kv_command_executed(capfd, app_instance, call_there_group):
    assert not getattr(app_instance.root, "text", "")
    call_there_group(["kv"], "Label:\n    text: '''Hello there'''")
    captured = capfd.readouterr()
    assert not captured.out and not captured.err
    assert app_instance.root.text == "Hello there"


@pytest.mark.asyncio
async def test_screenshot_command_executed(app_instance, call_there_group):
    call_there_group(["screenshot"], "")


@pytest.mark.asyncio
async def test_screenshot_saved_to_file(tmpdir, app_instance, call_there_group):
    output = Path(tmpdir) / "test.png"
    assert not os.path.exists(output)
    call_there_group(["screenshot", "-o", output], "")
    assert os.path.exists(output)
