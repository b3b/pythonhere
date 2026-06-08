import pytest
from herethere.there.ai import prompts

import pythonhere
from pythonhere.magic_here.prompts import (
    PYTHONHERE_AI_ACTIVE_PROMPTS,
    PYTHONHERE_AI_PROMPTS,
    register_pythonhere_ai_prompts,
)


@pytest.fixture(autouse=True)
def preserve_ai_prompt_store():
    original_active_prompts = prompts._ai_prompt_store.active_prompts
    original_registry = dict(prompts._ai_prompt_store.registry)
    prompts.reset_ai_prompt_store()
    yield
    prompts._ai_prompt_store.active_prompts = original_active_prompts
    prompts._ai_prompt_store.registry.clear()
    prompts._ai_prompt_store.registry.update(original_registry)


def test_pythonhere_ai_prompts_are_registered_as_active_stack():
    register_pythonhere_ai_prompts()

    assert prompts._ai_prompt_store.active_prompts == (
        "default",
        *PYTHONHERE_AI_ACTIVE_PROMPTS,
    )
    for name in PYTHONHERE_AI_PROMPTS:
        assert name in prompts.list_ai_prompts()
    assert "able" not in prompts._ai_prompt_store.active_prompts
    assert "midi" not in prompts._ai_prompt_store.active_prompts

    template = prompts.get_ai_template()
    assert "Kivy" in template
    assert "Android" in template
    assert "Pyjnius" in template
    assert "Kv design" in template
    assert "Plyer helpers" in template
    assert "Android Package Inventory" in template
    assert "Android Intents and Settings flows" not in template
    assert "Android BLE" not in template
    assert "MIDI playback" not in template


def test_load_ipython_extension_preloads_pythonhere_ai_prompts(mocker):
    load_herethere_extension = mocker.patch("pythonhere.load_herethere_extension")
    ipython = mocker.Mock()

    pythonhere.load_ipython_extension(ipython)

    assert prompts._ai_prompt_store.active_prompts == (
        "default",
        *PYTHONHERE_AI_ACTIVE_PROMPTS,
    )
    load_herethere_extension.assert_called_once_with(ipython)
