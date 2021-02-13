"""Android specific functions."""
# pylint: disable=invalid-name,import-error,import-outside-toplevel
from pathlib import Path
from typing import Optional
import uuid

from android import activity as android_activity
from jnius import autoclass, cast
from kivy.logger import Logger


Context = autoclass("android.content.Context")
Icon = autoclass("android.graphics.drawable.Icon")
Intent = autoclass("android.content.Intent")
PythonActivity = autoclass("org.kivy.android.PythonActivity")
ShortcutInfoBuilder = autoclass("android.content.pm.ShortcutInfo$Builder")
System = autoclass("java.lang.System")
Uri = autoclass("android.net.Uri")


def get_current_intent() -> Intent:
    """Return the intent that started Python activity."""
    return PythonActivity.mActivity.getIntent()


def get_startup_script(intent: None = None) -> Optional[str]:
    """Return script entrypoint that was passed to a given, or current, intent."""
    if not intent:
        intent = get_current_intent()
    data = intent.getData()
    return data and data.toString()


def restart_app(script: str = None):
    """Restart app, with a script as a starting point if provided."""
    Logger.info("PythonHere: restart requested with a script: %s", script)
    activity = PythonActivity.mActivity
    intent = Intent(activity.getApplicationContext(), PythonActivity)
    intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK)

    if script:
        intent.setData(Uri.parse(script))

    activity.startActivity(intent)
    System.exit(0)


def bind_run_script_on_new_intent():
    """Add handler for new intent event:
    restart app with entrypoint of a new intent.
    """

    def on_new_intent(intent):
        Logger.info("PythonHere: on_new_intent")
        restart_app(get_startup_script(intent))
        Logger.error("PythonHere: app was not restarted")

    android_activity.bind(on_new_intent=on_new_intent)


def create_shortcut_icon() -> Icon:
    """Create icon to use for a shurtcut."""
    activity = PythonActivity.mActivity
    Drawable = autoclass("{}.R$drawable".format(activity.getPackageName()))
    context = cast("android.content.Context", activity.getApplicationContext())
    return Icon.createWithResource(context, Drawable.icon)


def resolve_script_path(script: str) -> str:
    """Resolve path against upload directory."""
    from kivy.app import App

    if script.startswith("/"):
        path = Path(script)
    else:
        app = App.get_running_app()
        path = Path(app.upload_dir) / script
    return str(path.resolve(strict=True))


def pin_shortcut(script: str, label: str):
    """Request a pinned shortcut creation to run a Python script."""
    activity = PythonActivity.mActivity
    context = cast("android.content.Context", activity.getApplicationContext())

    intent = Intent(activity.getApplicationContext(), PythonActivity)
    intent.setAction(Intent.ACTION_MAIN)
    intent.setData(Uri.parse(resolve_script_path(script)))

    shortcut = (
        ShortcutInfoBuilder(context, f"pythonhere-{uuid.uuid4().hex}")
        .setShortLabel(label)
        .setLongLabel(label)
        .setIntent(intent)
        .setIcon(create_shortcut_icon())
        .build()
    )

    manager = activity.getSystemService(Context.SHORTCUT_SERVICE)
    manager.requestPinShortcut(shortcut, None)
