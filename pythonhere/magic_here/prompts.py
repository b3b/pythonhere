"""PythonHere prompt sections for ``%%there ai``."""

from importlib.resources import files

from herethere.there.ai import register_ai_prompt, set_ai_prompts

PYTHONHERE_AI_ACTIVE_PROMPTS = (
    "kivy-runtime",
    "kivy-kv",
    "android-runtime",
    "jnius",
    "android-permissions",
    "android-packages",
    "android-media",
    "plyer",
)

PYTHONHERE_AI_PROMPTS = (
    *PYTHONHERE_AI_ACTIVE_PROMPTS,
    "able",
    "midi",
)


def _read_prompt(name: str) -> str:
    return (
        files("pythonhere.magic_here")
        .joinpath("prompts", f"{name}.md")
        .read_text(encoding="utf-8")
    )


def register_pythonhere_ai_prompts() -> None:
    """Register PythonHere Android/Kivy prompt sections as the active AI stack."""
    for name in PYTHONHERE_AI_PROMPTS:
        register_ai_prompt(name, _read_prompt(name))
    set_ai_prompts("default", *PYTHONHERE_AI_ACTIVE_PROMPTS)
