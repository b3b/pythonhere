"""Utilities for launching scripts."""
import os
from pathlib import Path
import runpy
import sys


from kivy.logger import Logger
from kivy import platform


def run_script(script: str):
    """Execute given script."""
    Logger.info("PythonHere: Run script %s", script)
    try:
        path = Path(script).resolve(strict=True)
    except FileNotFoundError:
        Logger.error("Script not found: %s", script)
        return

    original_cwd = str(Path.cwd())
    original_sys_path = sys.path[:]
    try:
        script_dir = path.parent
        os.chdir(str(script_dir))
        sys.path.insert(0, str(script_dir))
        runpy.run_path(str(path), run_name="__main__")
    finally:
        os.chdir(original_cwd)
        sys.path = original_sys_path


def try_startup_script():
    """Execute startup script, if it was passed to app."""
    if platform != "android":
        return
    import android_here  # pylint: disable=import-outside-toplevel

    try:
        android_here.bind_run_script_on_new_intent()
        script = android_here.get_startup_script()
        if script:
            run_script(script)
    except Exception:
        Logger.exception("PythonHere: Error while starting script")
