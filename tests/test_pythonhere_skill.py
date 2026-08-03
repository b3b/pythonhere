import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

PROJECT_DIR = Path(__file__).parents[1]
PACKAGE_DIR = PROJECT_DIR / "pythonhere"
PROMPTS_DIR = PACKAGE_DIR / "magic_here" / "prompts"
SKILL_DIR = PACKAGE_DIR / ".agents" / "skills" / "pythonhere"
REFERENCES_DIR = SKILL_DIR / "references"

REFERENCE_NAMES = {
    "able.md",
    "android-media.md",
    "android-packages.md",
    "android-permissions.md",
    "android-runtime.md",
    "jnius.md",
    "kivy-kv.md",
    "kivy-runtime.md",
    "midi.md",
    "plyer.md",
}


def test_pythonhere_skill_files_exist():
    assert (SKILL_DIR / "SKILL.md").is_file()
    assert (SKILL_DIR / "agents" / "openai.yaml").is_file()
    assert {path.name for path in REFERENCES_DIR.glob("*.md")} == REFERENCE_NAMES


def test_pythonhere_skill_is_included_in_wheel(tmp_path):
    project_copy = tmp_path / "project"
    shutil.copytree(PACKAGE_DIR, project_copy / "pythonhere")
    shutil.copy2(PROJECT_DIR / "pyproject.toml", project_copy)
    shutil.copy2(PROJECT_DIR / "README.rst", project_copy)

    wheel_dir = tmp_path / "wheel"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--outdir",
            str(wheel_dir),
        ],
        cwd=project_copy,
        check=True,
        capture_output=True,
        text=True,
    )

    wheels = list(wheel_dir.glob("*.whl"))
    assert len(wheels) == 1
    with ZipFile(wheels[0]) as wheel:
        wheel_files = set(wheel.namelist())

    skill_prefix = "pythonhere/.agents/skills/pythonhere"
    expected_skill_files = {
        f"{skill_prefix}/SKILL.md",
        f"{skill_prefix}/agents/openai.yaml",
        *(f"{skill_prefix}/references/{name}" for name in REFERENCE_NAMES),
    }
    assert expected_skill_files <= wheel_files


def test_pythonhere_skill_references_cover_runtime_prompts():
    for name in REFERENCE_NAMES:
        prompt = (PROMPTS_DIR / name).read_text()
        reference = (REFERENCES_DIR / name).read_text()

        assert reference
        assert reference.splitlines()[0] == prompt.splitlines()[0]


def test_pythonhere_skill_uses_cli_execution_language():
    references = "\n".join(
        (REFERENCES_DIR / name).read_text() for name in REFERENCE_NAMES
    )

    assert "generated PythonHere cells" not in references
    assert "Jupyter/PythonHere cell" not in references
    assert "notebook output capture" not in references
    assert "later cells" not in references
