---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.19.3
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Usage scenarios

These scenarios show complete `%%there ai` workflows: generated cells, remote
state retrieval, file download and a `--fix` iteration.

```{code-cell}
%load_ext pythonhere
%connect-there
```

## App Usage Chart

```{code-cell}
:tags: ["remove-output"]
%%there ai
Show a chart of foreground app usage statistics in last 24 hours.
Save the results in a `usage` variable and in a `usage.csv` file.
Print instructions for drawing a usage pie chart locally with pandas and matplotlib.
UI should be optimised for the Android Portrait mode.
```

```{code-cell}
---
tags:
  - hide-input
jupyter:
  source_hidden: true
---
%%there
# Generated locally by %%there ai. Review before running.
from pathlib import Path
from csv import DictWriter

from jnius import autoclass
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup

usage = []
usage_status = {
    "ok": False,
    "stage": "starting",
    "message": "Starting usage statistics view.",
    "error": None,
}
usage_label_cache = globals().get("usage_label_cache", {})
usage_label_errors = []
usage_csv_path = "usage.csv"


def _show_usage_error_popup(message):
    content = Label(
        text=str(message),
        font_size=sp(15),
        halign="left",
        valign="top",
        text_size=(dp(300), None),
    )
    popup = Popup(
        title="Usage statistics error",
        content=content,
        size_hint=(0.9, None),
        height=dp(240),
    )
    popup.open()


def _format_duration(seconds):
    seconds = int(max(0, seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _get_android_context_and_activity():
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    activity = PythonActivity.mActivity
    if activity is not None:
        return activity, activity

    try:
        PythonService = autoclass("org.kivy.android.PythonService")
        service = PythonService.mService
        if service is not None:
            return service, None
    except Exception as exc:
        Logger.info(f"PythonHere: PythonService fallback unavailable: {type(exc).__name__}: {exc}")

    return None, None


def _check_usage_access(context):
    VERSION = autoclass("android.os.Build$VERSION")
    AppOpsManager = autoclass("android.app.AppOpsManager")
    Context = autoclass("android.content.Context")

    sdk_int = int(VERSION.SDK_INT)
    package_name = str(context.getPackageName())
    uid = int(context.getApplicationInfo().uid)

    app_ops_service = Context.APP_OPS_SERVICE or "appops"
    app_ops = context.getSystemService(app_ops_service)
    if app_ops is None:
        return {
            "granted": False,
            "sdk_int": sdk_int,
            "package_name": package_name,
            "mode": None,
            "mode_name": "app_ops_unavailable",
            "error": "AppOps service is unavailable.",
        }

    op_name = AppOpsManager.OPSTR_GET_USAGE_STATS or "android:get_usage_stats"
    mode = int(app_ops.checkOpNoThrow(op_name, uid, package_name))

    mode_names = {
        int(AppOpsManager.MODE_ALLOWED): "allowed",
        int(AppOpsManager.MODE_IGNORED): "ignored",
        int(AppOpsManager.MODE_DEFAULT): "default",
        int(AppOpsManager.MODE_ERRORED): "errored",
    }
    mode_foreground = getattr(AppOpsManager, "MODE_FOREGROUND", None)
    if mode_foreground is not None:
        mode_names[int(mode_foreground)] = "foreground"

    return {
        "granted": mode == int(AppOpsManager.MODE_ALLOWED),
        "sdk_int": sdk_int,
        "package_name": package_name,
        "mode": mode,
        "mode_name": mode_names.get(mode, str(mode)),
        "error": None,
    }


def _resolve_app_label(package_manager, package_name, sdk_int, application_info_flags_class):
    if package_name in usage_label_cache:
        return usage_label_cache[package_name]

    try:
        if sdk_int >= 33 and application_info_flags_class is not None:
            app_info = package_manager.getApplicationInfo(
                package_name,
                application_info_flags_class.of(0),
            )
        else:
            app_info = package_manager.getApplicationInfo(package_name, 0)
        label = package_manager.getApplicationLabel(app_info)
        label_text = str(label) if label is not None else package_name
    except Exception as exc:
        label_text = package_name
        error_text = f"{package_name}: {type(exc).__name__}: {exc}"
        usage_label_errors.append(error_text)
        Logger.info(f"PythonHere: Could not resolve app label: {error_text}")

    usage_label_cache[package_name] = label_text
    return label_text


def _write_usage_csv(rows):
    output_path = Path(usage_csv_path)
    fieldnames = [
        "rank",
        "app_label",
        "package",
        "foreground_seconds",
        "foreground_minutes",
        "foreground_hours",
        "percent",
        "foreground_ms",
        "first_time_stamp_ms",
        "last_time_stamp_ms",
        "last_time_used_ms",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})
    return output_path.name


def _load_usage_stats():
    context, activity = _get_android_context_and_activity()
    if context is None:
        output_name = _write_usage_csv([])
        return [], {
            "ok": False,
            "stage": "android_context",
            "message": "Android context is unavailable. Usage statistics cannot be queried.",
            "error": "Android context is unavailable.",
            "output_path": output_name,
        }

    access = _check_usage_access(context)
    end_ms = int(__import__("time").time() * 1000)
    begin_ms = end_ms - (24 * 60 * 60 * 1000)

    if not access["granted"]:
        output_name = _write_usage_csv([])
        return [], {
            "ok": False,
            "stage": "usage_access",
            "message": (
                "Usage access is not enabled for this app. Tap Open Settings, "
                "enable usage access for this app if it is listed, return here, "
                "then tap Refresh. If the app is not listed, the manifest must "
                "declare android.permission.PACKAGE_USAGE_STATS."
            ),
            "error": None,
            "access_granted": False,
            "app_ops_mode": access["mode"],
            "app_ops_mode_name": access["mode_name"],
            "sdk_int": access["sdk_int"],
            "package_name": access["package_name"],
            "window_start_ms": begin_ms,
            "window_end_ms": end_ms,
            "rows": 0,
            "output_path": output_name,
        }

    VERSION = autoclass("android.os.Build$VERSION")
    Context = autoclass("android.content.Context")
    UsageStatsManager = autoclass("android.app.usage.UsageStatsManager")

    sdk_int = int(VERSION.SDK_INT)
    usage_service = Context.USAGE_STATS_SERVICE or "usagestats"
    usage_manager = context.getSystemService(usage_service)
    if usage_manager is None:
        output_name = _write_usage_csv([])
        return [], {
            "ok": False,
            "stage": "usage_manager",
            "message": "UsageStatsManager is unavailable on this device.",
            "error": "UsageStatsManager is unavailable.",
            "access_granted": True,
            "sdk_int": sdk_int,
            "window_start_ms": begin_ms,
            "window_end_ms": end_ms,
            "rows": 0,
            "output_path": output_name,
        }

    package_manager = context.getPackageManager()
    application_info_flags_class = None
    if sdk_int >= 33:
        application_info_flags_class = autoclass("android.content.pm.PackageManager$ApplicationInfoFlags")

    interval_daily = int(UsageStatsManager.INTERVAL_DAILY)
    stats_list = usage_manager.queryUsageStats(interval_daily, begin_ms, end_ms)

    aggregate = {}
    queried_count = 0
    if stats_list is not None:
        queried_count = int(stats_list.size())
        for index in range(queried_count):
            stat = stats_list.get(index)
            package_name = stat.getPackageName()
            if package_name is None:
                continue
            package_name = str(package_name)

            foreground_ms = int(stat.getTotalTimeInForeground())
            if foreground_ms <= 0:
                continue

            record = aggregate.setdefault(
                package_name,
                {
                    "package": package_name,
                    "foreground_ms": 0,
                    "first_time_stamp_ms": None,
                    "last_time_stamp_ms": None,
                    "last_time_used_ms": None,
                },
            )
            record["foreground_ms"] += foreground_ms

            first_ts = int(stat.getFirstTimeStamp())
            last_ts = int(stat.getLastTimeStamp())
            last_used = int(stat.getLastTimeUsed())

            if record["first_time_stamp_ms"] is None or first_ts < record["first_time_stamp_ms"]:
                record["first_time_stamp_ms"] = first_ts
            if record["last_time_stamp_ms"] is None or last_ts > record["last_time_stamp_ms"]:
                record["last_time_stamp_ms"] = last_ts
            if record["last_time_used_ms"] is None or last_used > record["last_time_used_ms"]:
                record["last_time_used_ms"] = last_used

    total_ms = sum(item["foreground_ms"] for item in aggregate.values())
    rows = []
    for package_name, item in aggregate.items():
        app_label = _resolve_app_label(
            package_manager,
            package_name,
            sdk_int,
            application_info_flags_class,
        )
        seconds = item["foreground_ms"] / 1000.0
        rows.append(
            {
                "app_label": app_label,
                "package": package_name,
                "foreground_seconds": round(seconds, 3),
                "foreground_minutes": round(seconds / 60.0, 3),
                "foreground_hours": round(seconds / 3600.0, 4),
                "percent": round((item["foreground_ms"] / total_ms * 100.0), 3) if total_ms else 0.0,
                "foreground_ms": int(item["foreground_ms"]),
                "first_time_stamp_ms": item["first_time_stamp_ms"],
                "last_time_stamp_ms": item["last_time_stamp_ms"],
                "last_time_used_ms": item["last_time_used_ms"],
            }
        )

    rows.sort(key=lambda item: item["foreground_ms"], reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
        row["duration"] = _format_duration(row["foreground_seconds"])

    output_name = _write_usage_csv(rows)
    message = f"Loaded {len(rows)} apps with foreground usage in the last 24 hours. Saved {output_name}."
    if not rows:
        message = (
            "Usage access is enabled, but Android returned no foreground usage rows "
            "for the last 24 hours. The device may have no accessible records."
        )

    return rows, {
        "ok": True,
        "stage": "complete",
        "message": message,
        "error": None,
        "access_granted": True,
        "app_ops_mode": access["mode"],
        "app_ops_mode_name": access["mode_name"],
        "sdk_int": sdk_int,
        "package_name": access["package_name"],
        "window_start_ms": begin_ms,
        "window_end_ms": end_ms,
        "query_rows": queried_count,
        "rows": len(rows),
        "total_foreground_seconds": round(total_ms / 1000.0, 3),
        "output_path": output_name,
        "package_visibility_note": (
            "On Android 11 and newer, package label lookups can be affected by package visibility. "
            "UsageStats rows reflect accessible usage records."
            if sdk_int >= 30
            else ""
        ),
        "label_errors": list(usage_label_errors),
    }


def _make_chart_row(row, max_seconds):
    container = BoxLayout(
        orientation="vertical",
        size_hint_y=None,
        height=dp(82),
        padding=(0, dp(4), 0, dp(4)),
        spacing=dp(3),
    )

    header = BoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(28),
        spacing=dp(8),
    )

    name_label = Label(
        text=f"{row['rank']}. {row['app_label']}",
        font_size=sp(15),
        halign="left",
        valign="middle",
        shorten=True,
        shorten_from="right",
        text_size=(dp(210), dp(28)),
        size_hint_x=0.72,
    )
    time_label = Label(
        text=row.get("duration", _format_duration(row.get("foreground_seconds", 0))),
        font_size=sp(14),
        halign="right",
        valign="middle",
        text_size=(dp(90), dp(28)),
        size_hint_x=0.28,
    )
    header.add_widget(name_label)
    header.add_widget(time_label)

    progress = ProgressBar(
        max=100,
        value=(row["foreground_seconds"] / max_seconds * 100.0) if max_seconds else 0,
        size_hint_y=None,
        height=dp(18),
    )

    detail = Label(
        text=f"{row['percent']:.1f}%  {row['package']}",
        font_size=sp(12),
        halign="left",
        valign="middle",
        shorten=True,
        shorten_from="right",
        text_size=(dp(320), dp(20)),
        size_hint_y=None,
        height=dp(20),
    )

    container.add_widget(header)
    container.add_widget(progress)
    container.add_widget(detail)
    return container


def _update_usage_ui():
    ui = globals().get("usage_ui")
    if ui is None:
        return

    state = globals().get("usage_status", {})
    rows = globals().get("usage", [])

    message = state.get("message", "")
    if state.get("package_visibility_note"):
        message += "\n" + state["package_visibility_note"]
    ui.ids.status_label.text = message

    ui.ids.chart_box.clear_widgets()

    if rows:
        top_rows = rows[:20]
        max_seconds = max(row["foreground_seconds"] for row in top_rows) or 1
        for row in top_rows:
            ui.ids.chart_box.add_widget(_make_chart_row(row, max_seconds))
    else:
        empty_label = Label(
            text="No usage rows to chart yet.",
            font_size=sp(17),
            halign="center",
            valign="middle",
            text_size=(dp(320), None),
            size_hint_y=None,
            height=dp(140),
        )
        ui.ids.chart_box.add_widget(empty_label)

    ui.ids.summary_label.text = (
        f"Rows: {state.get('rows', len(rows))}    File: {state.get('output_path', usage_csv_path)}"
    )


def refresh_usage_stats(*args):
    global usage, usage_status
    try:
        usage_status = {
            "ok": False,
            "stage": "loading",
            "message": "Loading foreground usage statistics.",
            "error": None,
        }
        _update_usage_ui()

        rows, state = _load_usage_stats()
        usage = rows
        usage_status = state
        globals()["usage"] = usage
        globals()["usage_status"] = usage_status
        globals()["usage_label_cache"] = usage_label_cache
        globals()["usage_label_errors"] = usage_label_errors
        _update_usage_ui()
    except Exception as exc:
        Logger.exception("PythonHere: Could not load usage statistics")
        usage = []
        usage_status = {
            "ok": False,
            "stage": "exception",
            "message": f"Could not load usage statistics: {type(exc).__name__}: {exc}",
            "error": f"{type(exc).__name__}: {exc}",
            "output_path": usage_csv_path,
        }
        globals()["usage"] = usage
        globals()["usage_status"] = usage_status
        try:
            _write_usage_csv([])
        except Exception as csv_exc:
            Logger.exception("PythonHere: Could not write empty usage CSV after error")
            usage_status["csv_error"] = f"{type(csv_exc).__name__}: {csv_exc}"
        _update_usage_ui()
        _show_usage_error_popup(usage_status["message"])


def open_usage_access_settings(*args):
    global usage_status
    try:
        context, activity = _get_android_context_and_activity()
        if activity is None:
            usage_status = {
                **globals().get("usage_status", {}),
                "stage": "settings",
                "settings_opened": False,
                "message": "A foreground Android activity is required to open Usage Access Settings.",
                "error": "Foreground activity unavailable.",
            }
            globals()["usage_status"] = usage_status
            _update_usage_ui()
            return

        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")

        action = Settings.ACTION_USAGE_ACCESS_SETTINGS or "android.settings.USAGE_ACCESS_SETTINGS"
        intent = Intent(action)
        activity.startActivity(intent)

        usage_status = {
            **globals().get("usage_status", {}),
            "stage": "settings",
            "settings_opened": True,
            "settings_action": action,
            "message": (
                "Usage Access Settings opened. Enable usage access for this app if it is listed, "
                "return here, then tap Refresh."
            ),
            "error": None,
        }
        globals()["usage_status"] = usage_status
        _update_usage_ui()
    except Exception as exc:
        Logger.exception("PythonHere: Could not open Usage Access Settings")
        usage_status = {
            **globals().get("usage_status", {}),
            "stage": "settings_exception",
            "settings_opened": False,
            "message": f"Could not open Usage Access Settings: {type(exc).__name__}: {exc}",
            "error": f"{type(exc).__name__}: {exc}",
        }
        globals()["usage_status"] = usage_status
        _update_usage_ui()
        _show_usage_error_popup(usage_status["message"])


KV = """
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

BoxLayout:
    orientation: "vertical"
    padding: dp(12)
    spacing: dp(8)

    Label:
        id: title_label
        text: "Foreground app usage"
        size_hint_y: None
        height: dp(44)
        font_size: sp(22)
        bold: True
        halign: "center"
        valign: "middle"
        text_size: self.size

    Label:
        id: status_label
        text: "Preparing usage statistics."
        size_hint_y: None
        height: dp(112)
        font_size: sp(14)
        halign: "left"
        valign: "top"
        text_size: self.width, None

    BoxLayout:
        orientation: "horizontal"
        size_hint_y: None
        height: dp(52)
        spacing: dp(8)

        Button:
            id: refresh_button
            text: "Refresh"
            font_size: sp(16)

        Button:
            id: settings_button
            text: "Open Settings"
            font_size: sp(16)

    Label:
        id: summary_label
        text: "Rows: 0    File: usage.csv"
        size_hint_y: None
        height: dp(28)
        font_size: sp(13)
        halign: "left"
        valign: "middle"
        text_size: self.size

    ScrollView:
        do_scroll_x: False
        do_scroll_y: True

        GridLayout:
            id: chart_box
            cols: 1
            spacing: dp(8)
            padding: 0, dp(4)
            size_hint_y: None
            height: self.minimum_height
"""

try:
    usage_ui = Builder.load_string(KV)
    if usage_ui is None:
        raise RuntimeError("Builder.load_string returned None for usage UI.")

    usage_ui.ids.refresh_button.bind(on_release=refresh_usage_stats)
    usage_ui.ids.settings_button.bind(on_release=open_usage_access_settings)

    root.clear_widgets()
    root.add_widget(usage_ui)

    globals()["usage_ui"] = usage_ui
    globals()["refresh_usage_stats"] = refresh_usage_stats
    globals()["open_usage_access_settings"] = open_usage_access_settings

    refresh_usage_stats()

except Exception as exc:
    Logger.exception("PythonHere: Could not build usage statistics UI")
    usage_status = {
        "ok": False,
        "stage": "ui_exception",
        "message": f"Could not build usage statistics UI: {type(exc).__name__}: {exc}",
        "error": f"{type(exc).__name__}: {exc}",
        "output_path": usage_csv_path,
    }
    globals()["usage_status"] = usage_status
    _show_usage_error_popup(usage_status["message"])


print(f"%there download {Path(usage_csv_path).name}")
print(
    """
Local pie chart instructions with pandas and matplotlib:

1. Download usage.csv from this PythonHere session.
2. Put usage.csv in your local working directory.
3. Run this code locally:

import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("usage.csv")
df = df[df["foreground_seconds"] > 0].copy()

if df.empty:
    print("No usage rows found in usage.csv")
else:
    top = df.sort_values("foreground_seconds", ascending=False).head(10)
    other_seconds = df.loc[~df.index.isin(top.index), "foreground_seconds"].sum()
    if other_seconds > 0:
        top = pd.concat([
            top[["app_label", "foreground_seconds"]],
            pd.DataFrame([{"app_label": "Other", "foreground_seconds": other_seconds}]),
        ], ignore_index=True)

    ax = top.set_index("app_label")["foreground_seconds"].plot.pie(
        autopct="%1.1f%%",
        startangle=90,
        counterclock=False,
        figsize=(7, 7),
    )
    ax.set_ylabel("")
    ax.set_title("Foreground app usage, last 24 hours")
    plt.tight_layout()
    plt.show()
"""
)

```

Check the remote usage query status and preview the first row before downloading
the CSV:

```{code-cell}
%there get {"status": usage_status, "first_row": usage[:1]}
```

```{code-cell}
%there download usage.csv
```

After the remote cell writes `usage.csv`, download it and analyze it locally in
the notebook.

```{code-cell}
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("usage.csv")
df = df[df["foreground_seconds"] > 0].copy()

top = df.sort_values("foreground_seconds", ascending=False).head(5)

ax = top.set_index("app_label")["foreground_seconds"].plot.pie(
    labels=None,
    autopct="%1.1f%%",
    startangle=90,
    counterclock=False,
    figsize=(3, 3),
)

plt.show()
```

## Accelerometer Maze

```{code-cell}
:tags: ["remove-output"]
%%there ai
A maze game controlled by accelerometer.
- portrait mode
- screen should be blocked from rotation
```

```{code-cell}
---
tags:
  - hide-input
jupyter:
  source_hidden: true
---
%%there
# Generated locally by %%there ai. Review before running.
from math import floor
from random import shuffle

from kivy.clock import Clock
from kivy.factory import Factory
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.metrics import dp
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget

from plyer import accelerometer


def _maze_show_error(title, message):
    globals()["maze_game_last_error"] = str(message)
    try:
        Popup(
            title=title,
            content=Label(
                text=str(message)[:900],
                text_size=(dp(280), None),
                halign="center",
                valign="middle",
            ),
            size_hint=(0.88, 0.45),
        ).open()
    except Exception:
        Logger.exception("PythonHere: Could not show maze error popup")


def _make_accel_maze(cols=15, rows=21):
    if cols % 2 == 0:
        cols += 1
    if rows % 2 == 0:
        rows += 1

    maze = [[1 for _ in range(cols)] for _ in range(rows)]
    start = (1, rows - 2)
    goal = (cols - 2, 1)

    stack = [start]
    maze[start[1]][start[0]] = 0

    while stack:
        c, r = stack[-1]
        choices = []
        for dc, dr in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            nc, nr = c + dc, r + dr
            if 1 <= nc < cols - 1 and 1 <= nr < rows - 1 and maze[nr][nc] == 1:
                choices.append((nc, nr, dc, dr))
        if choices:
            shuffle(choices)
            nc, nr, dc, dr = choices[0]
            maze[r + dr // 2][c + dc // 2] = 0
            maze[nr][nc] = 0
            stack.append((nc, nr))
        else:
            stack.pop()

    maze[start[1]][start[0]] = 0
    maze[goal[1]][goal[0]] = 0
    return maze, start, goal


class AccelMazeBoard(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.maze = []
        self.cols = 0
        self.rows = 0
        self.start_cell = None
        self.goal_cell = None
        self.cell = 0
        self.board_x = 0
        self.board_y = 0
        self.ball_x = None
        self.ball_y = None
        self.ball_radius = 8
        self.velocity_x = 0
        self.velocity_y = 0
        self.won = False
        self.bind(pos=self._on_layout_change, size=self._on_layout_change)

    def configure(self, maze, start_cell, goal_cell):
        self.maze = maze
        self.rows = len(maze)
        self.cols = len(maze[0]) if self.rows else 0
        self.start_cell = start_cell
        self.goal_cell = goal_cell
        self.won = False
        self.velocity_x = 0
        self.velocity_y = 0
        self.ball_x = None
        self.ball_y = None
        self._update_metrics()
        self._ensure_ball_position()
        self._redraw()

    def reset_ball(self):
        self.velocity_x = 0
        self.velocity_y = 0
        self.won = False
        self.ball_x = None
        self.ball_y = None
        self._ensure_ball_position()
        self._redraw()

    def _on_layout_change(self, *args):
        old_cell = self.cell
        old_rel_x = None
        old_rel_y = None
        if self.ball_x is not None and old_cell:
            old_rel_x = (self.ball_x - self.board_x) / old_cell
            old_rel_y = (self.ball_y - self.board_y) / old_cell

        self._update_metrics()

        if old_rel_x is not None and self.cell:
            self.ball_x = self.board_x + old_rel_x * self.cell
            self.ball_y = self.board_y + old_rel_y * self.cell
            self.ball_radius = max(6, self.cell * 0.30)
        else:
            self._ensure_ball_position()

        self._redraw()

    def _update_metrics(self):
        if not self.cols or not self.rows or self.width <= 0 or self.height <= 0:
            self.cell = 0
            return
        self.cell = min(self.width / self.cols, self.height / self.rows)
        self.board_x = self.x + (self.width - self.cell * self.cols) / 2
        self.board_y = self.y + (self.height - self.cell * self.rows) / 2
        self.ball_radius = max(6, self.cell * 0.30)

    def _cell_center(self, cell):
        c, r = cell
        return (
            self.board_x + (c + 0.5) * self.cell,
            self.board_y + (self.rows - r - 0.5) * self.cell,
        )

    def _cell_at_point(self, x, y):
        if not self.cell:
            return None
        c = int(floor((x - self.board_x) / self.cell))
        bottom_row = int(floor((y - self.board_y) / self.cell))
        r = self.rows - 1 - bottom_row
        if 0 <= c < self.cols and 0 <= r < self.rows:
            return c, r
        return None

    def _ensure_ball_position(self):
        if self.ball_x is None and self.start_cell and self.cell:
            self.ball_x, self.ball_y = self._cell_center(self.start_cell)
            self.ball_radius = max(6, self.cell * 0.30)

    def _circle_hits_wall(self, x, y):
        if not self.cell or not self.maze:
            return True

        radius = self.ball_radius
        c0 = int(floor((x - radius - self.board_x) / self.cell))
        c1 = int(floor((x + radius - self.board_x) / self.cell))
        b0 = int(floor((y - radius - self.board_y) / self.cell))
        b1 = int(floor((y + radius - self.board_y) / self.cell))

        for c in range(c0, c1 + 1):
            for bottom_row in range(b0, b1 + 1):
                r = self.rows - 1 - bottom_row
                if c < 0 or c >= self.cols or r < 0 or r >= self.rows:
                    return True
                if self.maze[r][c] == 1:
                    left = self.board_x + c * self.cell
                    bottom = self.board_y + bottom_row * self.cell
                    right = left + self.cell
                    top = bottom + self.cell
                    closest_x = min(max(x, left), right)
                    closest_y = min(max(y, bottom), top)
                    dx = x - closest_x
                    dy = y - closest_y
                    if dx * dx + dy * dy < radius * radius:
                        return True
        return False

    def step(self, dt, accel_x, accel_y):
        if self.won:
            return

        self._update_metrics()
        self._ensure_ball_position()
        if self.ball_x is None or not self.cell:
            return

        dt = min(max(dt, 0.0), 0.05)

        dead_zone = 0.04
        if abs(accel_x) < dead_zone:
            accel_x = 0
        if abs(accel_y) < dead_zone:
            accel_y = 0

        force = self.cell * 36.0
        self.velocity_x += accel_x * force * dt
        self.velocity_y += accel_y * force * dt

        friction = max(0.0, 1.0 - 2.1 * dt)
        self.velocity_x *= friction
        self.velocity_y *= friction

        max_speed = self.cell * 7.5
        speed_sq = self.velocity_x * self.velocity_x + self.velocity_y * self.velocity_y
        if speed_sq > max_speed * max_speed:
            scale = max_speed / (speed_sq ** 0.5)
            self.velocity_x *= scale
            self.velocity_y *= scale

        next_x = self.ball_x + self.velocity_x * dt
        if not self._circle_hits_wall(next_x, self.ball_y):
            self.ball_x = next_x
        else:
            self.velocity_x *= -0.25

        next_y = self.ball_y + self.velocity_y * dt
        if not self._circle_hits_wall(self.ball_x, next_y):
            self.ball_y = next_y
        else:
            self.velocity_y *= -0.25

        current_cell = self._cell_at_point(self.ball_x, self.ball_y)
        if current_cell == self.goal_cell:
            self.won = True
            self.velocity_x = 0
            self.velocity_y = 0

        self._redraw()

    def _redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(0.06, 0.07, 0.09, 1)
            Rectangle(pos=self.pos, size=self.size)

            if not self.maze or not self.cell:
                return

            board_w = self.cell * self.cols
            board_h = self.cell * self.rows

            Color(0.13, 0.15, 0.18, 1)
            Rectangle(pos=(self.board_x, self.board_y), size=(board_w, board_h))

            if self.goal_cell:
                gc, gr = self.goal_cell
                Color(0.12, 0.72, 0.30, 1)
                Rectangle(
                    pos=(self.board_x + gc * self.cell, self.board_y + (self.rows - 1 - gr) * self.cell),
                    size=(self.cell, self.cell),
                )

            Color(0.82, 0.84, 0.88, 1)
            for r, row in enumerate(self.maze):
                for c, value in enumerate(row):
                    if value == 1:
                        Rectangle(
                            pos=(self.board_x + c * self.cell, self.board_y + (self.rows - 1 - r) * self.cell),
                            size=(self.cell, self.cell),
                        )

            Color(0.02, 0.03, 0.04, 1)
            Line(rectangle=(self.board_x, self.board_y, board_w, board_h), width=max(1, self.cell * 0.05))

            if self.ball_x is not None:
                Color(0.08, 0.38, 0.95, 1)
                Ellipse(
                    pos=(self.ball_x - self.ball_radius, self.ball_y - self.ball_radius),
                    size=(self.ball_radius * 2, self.ball_radius * 2),
                )


Factory.register("AccelMazeBoard", cls=AccelMazeBoard)


class AccelerometerMazeController:
    def __init__(self, ui, previous_orientation=None, orientation_locked=False):
        self.ui = ui
        self.board = ui.ids.board_widget
        self.status_label = ui.ids.status_label
        self.previous_orientation = previous_orientation
        self.orientation_locked = orientation_locked
        self.event = None
        self.paused = False
        self.accelerometer_enabled = False
        self.calibration = None
        self.last_status_update = 0
        self.last_error = None
        self.state = {
            "ok": True,
            "stage": "starting",
            "message": "Starting maze game.",
            "error": None,
            "orientation_locked": bool(orientation_locked),
            "accelerometer_enabled": False,
            "paused": False,
            "won": False,
        }
        globals()["maze_game_state"] = self.state

    def start(self):
        self.restart()
        try:
            accelerometer.enable()
            self.accelerometer_enabled = True
            self.state["accelerometer_enabled"] = True
            self._set_status("Ready. Hold the phone normally, then tilt to move.")
        except Exception as exc:
            Logger.exception("PythonHere: Could not enable accelerometer")
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.state.update(
                ok=False,
                stage="enable_accelerometer",
                error=self.last_error,
                message="Accelerometer could not be enabled.",
            )
            self._set_status("Accelerometer error: " + self.last_error)

        self.event = Clock.schedule_interval(self._tick, 1 / 60.0)
        self.state["stage"] = "running"

    def cleanup(self, restore_orientation=False):
        if self.event is not None:
            self.event.cancel()
            self.event = None
        try:
            if self.accelerometer_enabled:
                accelerometer.disable()
        except Exception:
            Logger.exception("PythonHere: Could not disable accelerometer")
        self.accelerometer_enabled = False
        self.state["accelerometer_enabled"] = False

        if restore_orientation and self.previous_orientation is not None:
            try:
                from jnius import autoclass

                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                activity = PythonActivity.mActivity
                if activity is not None:
                    activity.setRequestedOrientation(int(self.previous_orientation))
                    self.state["orientation_locked"] = False
            except Exception:
                Logger.exception("PythonHere: Could not restore previous orientation")

    def restart(self, *args):
        maze, start, goal = _make_accel_maze()
        self.board.configure(maze, start, goal)
        self.paused = False
        self.calibration = None
        self.state.update(
            ok=True,
            stage="running",
            message="New maze started.",
            error=None,
            paused=False,
            won=False,
            rows=len(maze),
            cols=len(maze[0]) if maze else 0,
        )
        self.ui.ids.pause_button.text = "Pause"
        self._set_status("New maze. Tilt to move the blue ball to the green goal.")

    def calibrate(self, *args):
        raw = self._read_acceleration()
        if raw is None:
            self._set_status("Waiting for accelerometer data. Try again in a moment.")
            self.state["message"] = "Calibration waiting for accelerometer data."
            return
        self.calibration = (raw[0], raw[1])
        self.state["calibration"] = {"x": raw[0], "y": raw[1]}
        self._set_status("Calibrated. Tilt gently to move.")

    def toggle_pause(self, *args):
        self.paused = not self.paused
        self.state["paused"] = self.paused
        self.ui.ids.pause_button.text = "Resume" if self.paused else "Pause"
        self._set_status("Paused." if self.paused else "Running. Tilt to move.")

    def _set_status(self, message):
        self.status_label.text = str(message)
        self.state["message"] = str(message)

    def _read_acceleration(self):
        raw = accelerometer.acceleration
        if not raw or len(raw) < 2:
            return None
        if raw[0] is None or raw[1] is None:
            return None
        return float(raw[0]), float(raw[1])

    def _tick(self, dt):
        try:
            if self.paused:
                return

            raw = self._read_acceleration()
            if raw is None:
                if Clock.get_time() - self.last_status_update > 1.5:
                    self.last_status_update = Clock.get_time()
                    self._set_status("Waiting for accelerometer data.")
                return

            if self.calibration is None:
                self.calibration = (raw[0], raw[1])
                self.state["calibration"] = {"x": raw[0], "y": raw[1]}

            accel_x = raw[0] - self.calibration[0]
            accel_y = raw[1] - self.calibration[1]
            self.state["last_acceleration"] = {"x": raw[0], "y": raw[1]}
            self.board.step(dt, accel_x, accel_y)

            if self.board.won and not self.state.get("won"):
                self.state["won"] = True
                self.state["stage"] = "won"
                self._set_status("You reached the goal. Press Restart for a new maze.")

        except Exception as exc:
            Logger.exception("PythonHere: Maze game loop failed")
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.state.update(
                ok=False,
                stage="game_loop",
                error=self.last_error,
                message="Maze game loop error.",
            )
            self._set_status("Game error: " + self.last_error)
            self.paused = True
            self.state["paused"] = True


def _install_accelerometer_maze_game():
    try:
        old_cleanup = globals().get("maze_game_cleanup")
        if callable(old_cleanup):
            try:
                old_cleanup(restore_orientation=False)
            except Exception:
                Logger.exception("PythonHere: Previous maze cleanup failed")
    except Exception:
        Logger.exception("PythonHere: Could not inspect previous maze cleanup")

    previous_orientation = None
    orientation_locked = False

    try:
        from jnius import autoclass

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ActivityInfo = autoclass("android.content.pm.ActivityInfo")
        activity = PythonActivity.mActivity
        if activity is not None:
            try:
                previous_orientation = int(activity.getRequestedOrientation())
            except Exception:
                previous_orientation = None
            activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT)
            orientation_locked = True
    except Exception as exc:
        Logger.exception("PythonHere: Could not lock screen orientation")
        globals()["maze_game_orientation_error"] = f"{type(exc).__name__}: {exc}"

    KV = """
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

BoxLayout:
    orientation: "vertical"
    padding: dp(10)
    spacing: dp(8)

    Label:
        id: title_label
        text: "Accel Maze"
        size_hint_y: None
        height: dp(40)
        font_size: sp(24)
        bold: True
        halign: "center"
        valign: "middle"
        text_size: self.size

    Label:
        id: instruction_label
        text: "Tilt the phone to move the blue ball to the green goal."
        size_hint_y: None
        height: dp(48)
        font_size: sp(15)
        halign: "center"
        valign: "middle"
        text_size: self.size

    AccelMazeBoard:
        id: board_widget
        size_hint_y: 1

    GridLayout:
        cols: 3
        spacing: dp(8)
        size_hint_y: None
        height: dp(56)

        Button:
            id: calibrate_button
            text: "Calibrate"
            font_size: sp(16)

        Button:
            id: restart_button
            text: "Restart"
            font_size: sp(16)

        Button:
            id: pause_button
            text: "Pause"
            font_size: sp(16)

    Label:
        id: status_label
        text: "Starting."
        size_hint_y: None
        height: dp(54)
        font_size: sp(14)
        halign: "center"
        valign: "middle"
        text_size: self.size
"""

    try:
        ui = Builder.load_string(KV)
        if ui is None:
            raise RuntimeError("Builder.load_string returned None")

        root.clear_widgets()
        root.add_widget(ui)

        controller = AccelerometerMazeController(
            ui,
            previous_orientation=previous_orientation,
            orientation_locked=orientation_locked,
        )

        ui.ids.calibrate_button.bind(on_release=controller.calibrate)
        ui.ids.restart_button.bind(on_release=controller.restart)
        ui.ids.pause_button.bind(on_release=controller.toggle_pause)

        globals()["maze_game_ui"] = ui
        globals()["maze_game_controller"] = controller

        def maze_game_cleanup(restore_orientation=False):
            controller.cleanup(restore_orientation=restore_orientation)

        globals()["maze_game_cleanup"] = maze_game_cleanup

        controller.start()

        if orientation_locked:
            controller.state["orientation_message"] = "Portrait orientation locked."
        else:
            controller.state["orientation_message"] = "Portrait lock was not confirmed."

    except Exception as exc:
        Logger.exception("PythonHere: Could not load accelerometer maze game")
        globals()["maze_game_state"] = {
            "ok": False,
            "stage": "install",
            "error": f"{type(exc).__name__}: {exc}",
            "message": "Could not load accelerometer maze game.",
        }
        _maze_show_error("Maze error", f"{type(exc).__name__}: {exc}")


_install_accelerometer_maze_game()
```

The first generated game works, but the next prompt asks for a visual direction
and a performance improvement. `--fix` uses the previous `%%there` cell as
context and inserts a replacement cell.

```{code-cell}
:tags: ["remove-output"]
%%there ai --fix
Apply style: bright paper map
- off-white paper background
- thin blueprint-style maze lines
- small colored player marker
- dotted trail like a route map
- goal marked with a flag
- subtle grid texture
UI controls should match the paper map style: buttons and HUD as paper cards
with light fills, thin blueprint-blue outlines, rounded corners and subtle shadows.
Keep gameplay smooth: don't redraw the full board every frame; cache the static map and only update the moving marker/trail.
```

```{code-cell}
%there -d 1 screenshot -w 250
```

```{code-cell}
---
tags:
  - hide-input
jupyter:
  source_hidden: true
---
%%there
# Generated locally by %%there ai. Review before running.
# AI mode: fix
# Fix: restyle the maze as a bright paper map and cache the static board so only the marker and route trail update each frame.
from math import floor
from random import shuffle

from kivy.clock import Clock
from kivy.factory import Factory
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.graphics.instructions import InstructionGroup
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.metrics import dp
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget

from plyer import accelerometer


PAPER_BG = (0.985, 0.965, 0.905, 1)
PAPER_CARD = (1.0, 0.988, 0.94, 1)
PAPER_CARD_DOWN = (0.955, 0.975, 0.985, 1)
BLUEPRINT = (0.075, 0.275, 0.55, 1)
BLUEPRINT_LIGHT = (0.42, 0.62, 0.78, 1)
TRAIL_BLUE = (0.08, 0.36, 0.70, 1)
PLAYER_RED = (0.92, 0.22, 0.18, 1)
FLAG_RED = (0.84, 0.16, 0.14, 1)


def _maze_show_error(title, message):
    globals()["maze_game_last_error"] = str(message)
    try:
        Popup(
            title=title,
            content=Label(
                text=str(message)[:900],
                text_size=(dp(280), None),
                halign="center",
                valign="middle",
            ),
            size_hint=(0.88, 0.45),
        ).open()
    except Exception:
        Logger.exception("PythonHere: Could not show maze error popup")


class PaperCanvasMixin:
    paper_radius = dp(14)

    def _setup_paper_canvas(self, fill=PAPER_CARD, outline=BLUEPRINT, shadow_alpha=0.14):
        self._paper_fill_rgba = fill
        self._paper_outline_rgba = outline
        self._paper_shadow_alpha = shadow_alpha
        with self.canvas.before:
            self._paper_shadow_color = Color(0.06, 0.12, 0.18, shadow_alpha)
            self._paper_shadow = RoundedRectangle(
                pos=(self.x + dp(2), self.y - dp(2)),
                size=self.size,
                radius=[self.paper_radius],
            )
            self._paper_fill_color = Color(*fill)
            self._paper_fill_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[self.paper_radius],
            )
        with self.canvas.after:
            self._paper_outline_color = Color(*outline)
            self._paper_outline = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, self.paper_radius),
                width=dp(1.2),
            )
        self.bind(pos=self._update_paper_canvas, size=self._update_paper_canvas)

    def _update_paper_canvas(self, *args):
        self._paper_shadow.pos = (self.x + dp(2), self.y - dp(2))
        self._paper_shadow.size = self.size
        self._paper_fill_rect.pos = self.pos
        self._paper_fill_rect.size = self.size
        self._paper_outline.rounded_rectangle = (
            self.x,
            self.y,
            self.width,
            self.height,
            self.paper_radius,
        )


class PaperButton(PaperCanvasMixin, Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = BLUEPRINT
        self.bold = True
        self._setup_paper_canvas()
        self.bind(state=self._on_paper_state)

    def _on_paper_state(self, *args):
        if self.state == "down":
            self._paper_fill_color.rgba = PAPER_CARD_DOWN
            self._paper_shadow_color.rgba = (0.06, 0.12, 0.18, 0.06)
            self._paper_shadow.pos = (self.x + dp(1), self.y - dp(1))
        else:
            self._paper_fill_color.rgba = PAPER_CARD
            self._paper_shadow_color.rgba = (0.06, 0.12, 0.18, self._paper_shadow_alpha)
            self._paper_shadow.pos = (self.x + dp(2), self.y - dp(2))


class PaperCardLabel(PaperCanvasMixin, Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = BLUEPRINT
        self.padding = (dp(10), dp(6))
        self._setup_paper_canvas()


def _make_accel_maze(cols=15, rows=21):
    if cols % 2 == 0:
        cols += 1
    if rows % 2 == 0:
        rows += 1

    maze = [[1 for _ in range(cols)] for _ in range(rows)]
    start = (1, rows - 2)
    goal = (cols - 2, 1)

    stack = [start]
    maze[start[1]][start[0]] = 0

    while stack:
        c, r = stack[-1]
        choices = []
        for dc, dr in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            nc, nr = c + dc, r + dr
            if 1 <= nc < cols - 1 and 1 <= nr < rows - 1 and maze[nr][nc] == 1:
                choices.append((nc, nr, dc, dr))
        if choices:
            shuffle(choices)
            nc, nr, dc, dr = choices[0]
            maze[r + dr // 2][c + dc // 2] = 0
            maze[nr][nc] = 0
            stack.append((nc, nr))
        else:
            stack.pop()

    maze[start[1]][start[0]] = 0
    maze[goal[1]][goal[0]] = 0
    return maze, start, goal


class AccelMazeBoard(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.maze = []
        self.cols = 0
        self.rows = 0
        self.start_cell = None
        self.goal_cell = None
        self.cell = 0
        self.board_x = 0
        self.board_y = 0
        self.ball_x = None
        self.ball_y = None
        self.ball_radius = 8
        self.velocity_x = 0
        self.velocity_y = 0
        self.won = False

        self.static_group = InstructionGroup()
        self.trail_group = InstructionGroup()
        self.marker_group = InstructionGroup()
        self.canvas.add(self.static_group)
        self.canvas.add(self.trail_group)
        self.canvas.add(self.marker_group)

        self.max_trail_dots = 80
        self.trail_points = []
        self.trail_refs = []
        self._last_trail_point = None
        self._build_dynamic_instruction_cache()

        self.bind(pos=self._on_layout_change, size=self._on_layout_change)

    def _build_dynamic_instruction_cache(self):
        for _index in range(self.max_trail_dots):
            dot_color = Color(TRAIL_BLUE[0], TRAIL_BLUE[1], TRAIL_BLUE[2], 0)
            dot = Ellipse(pos=(-100, -100), size=(0, 0))
            self.trail_group.add(dot_color)
            self.trail_group.add(dot)
            self.trail_refs.append((dot_color, dot))

        self.marker_shadow_color = Color(0.08, 0.10, 0.12, 0)
        self.marker_shadow = Ellipse(pos=(-100, -100), size=(0, 0))
        self.marker_fill_color = Color(*PLAYER_RED)
        self.marker_fill = Ellipse(pos=(-100, -100), size=(0, 0))
        self.marker_outline_color = Color(0.48, 0.04, 0.03, 0)
        self.marker_outline = Line(circle=(-100, -100, 1), width=dp(1.2))

        self.marker_group.add(self.marker_shadow_color)
        self.marker_group.add(self.marker_shadow)
        self.marker_group.add(self.marker_fill_color)
        self.marker_group.add(self.marker_fill)
        self.marker_group.add(self.marker_outline_color)
        self.marker_group.add(self.marker_outline)

    def configure(self, maze, start_cell, goal_cell):
        self.maze = maze
        self.rows = len(maze)
        self.cols = len(maze[0]) if self.rows else 0
        self.start_cell = start_cell
        self.goal_cell = goal_cell
        self.won = False
        self.velocity_x = 0
        self.velocity_y = 0
        self.ball_x = None
        self.ball_y = None
        self.trail_points = []
        self._last_trail_point = None
        self._update_metrics()
        self._ensure_ball_position()
        self._record_trail_point(force=True)
        self._redraw_static_map()
        self._update_trail_instructions()
        self._update_marker_instruction()

    def reset_ball(self):
        self.velocity_x = 0
        self.velocity_y = 0
        self.won = False
        self.ball_x = None
        self.ball_y = None
        self.trail_points = []
        self._last_trail_point = None
        self._ensure_ball_position()
        self._record_trail_point(force=True)
        self._update_trail_instructions()
        self._update_marker_instruction()

    def _on_layout_change(self, *args):
        old_cell = self.cell
        old_rel_x = None
        old_rel_y = None
        if self.ball_x is not None and old_cell:
            old_rel_x = (self.ball_x - self.board_x) / old_cell
            old_rel_y = (self.ball_y - self.board_y) / old_cell

        self._update_metrics()

        if old_rel_x is not None and self.cell:
            self.ball_x = self.board_x + old_rel_x * self.cell
            self.ball_y = self.board_y + old_rel_y * self.cell
            self.ball_radius = max(dp(4), self.cell * 0.22)
        else:
            self._ensure_ball_position()

        self._redraw_static_map()
        self._update_trail_instructions()
        self._update_marker_instruction()

    def _update_metrics(self):
        if not self.cols or not self.rows or self.width <= 0 or self.height <= 0:
            self.cell = 0
            return
        padding = dp(8)
        available_w = max(1, self.width - padding * 2)
        available_h = max(1, self.height - padding * 2)
        self.cell = min(available_w / self.cols, available_h / self.rows)
        self.board_x = self.x + (self.width - self.cell * self.cols) / 2
        self.board_y = self.y + (self.height - self.cell * self.rows) / 2
        self.ball_radius = max(dp(4), self.cell * 0.22)

    def _cell_center(self, cell):
        c, r = cell
        return (
            self.board_x + (c + 0.5) * self.cell,
            self.board_y + (self.rows - r - 0.5) * self.cell,
        )

    def _cell_at_point(self, x, y):
        if not self.cell:
            return None
        c = int(floor((x - self.board_x) / self.cell))
        bottom_row = int(floor((y - self.board_y) / self.cell))
        r = self.rows - 1 - bottom_row
        if 0 <= c < self.cols and 0 <= r < self.rows:
            return c, r
        return None

    def _ensure_ball_position(self):
        if self.ball_x is None and self.start_cell and self.cell:
            self.ball_x, self.ball_y = self._cell_center(self.start_cell)
            self.ball_radius = max(dp(4), self.cell * 0.22)

    def _circle_hits_wall(self, x, y):
        if not self.cell or not self.maze:
            return True

        radius = self.ball_radius
        c0 = int(floor((x - radius - self.board_x) / self.cell))
        c1 = int(floor((x + radius - self.board_x) / self.cell))
        b0 = int(floor((y - radius - self.board_y) / self.cell))
        b1 = int(floor((y + radius - self.board_y) / self.cell))

        for c in range(c0, c1 + 1):
            for bottom_row in range(b0, b1 + 1):
                r = self.rows - 1 - bottom_row
                if c < 0 or c >= self.cols or r < 0 or r >= self.rows:
                    return True
                if self.maze[r][c] == 1:
                    left = self.board_x + c * self.cell
                    bottom = self.board_y + bottom_row * self.cell
                    right = left + self.cell
                    top = bottom + self.cell
                    closest_x = min(max(x, left), right)
                    closest_y = min(max(y, bottom), top)
                    dx = x - closest_x
                    dy = y - closest_y
                    if dx * dx + dy * dy < radius * radius:
                        return True
        return False

    def _record_trail_point(self, force=False):
        if self.ball_x is None or not self.cell:
            return
        rel = (
            (self.ball_x - self.board_x) / self.cell,
            (self.ball_y - self.board_y) / self.cell,
        )
        if self._last_trail_point is not None and not force:
            dx = rel[0] - self._last_trail_point[0]
            dy = rel[1] - self._last_trail_point[1]
            if dx * dx + dy * dy < 0.16:
                return
        self.trail_points.append(rel)
        self.trail_points = self.trail_points[-self.max_trail_dots:]
        self._last_trail_point = rel
        self._update_trail_instructions()

    def step(self, dt, accel_x, accel_y):
        if self.won:
            return

        self._update_metrics()
        self._ensure_ball_position()
        if self.ball_x is None or not self.cell:
            return

        dt = min(max(dt, 0.0), 0.05)

        dead_zone = 0.04
        if abs(accel_x) < dead_zone:
            accel_x = 0
        if abs(accel_y) < dead_zone:
            accel_y = 0

        force = self.cell * 36.0
        self.velocity_x += accel_x * force * dt
        self.velocity_y += accel_y * force * dt

        friction = max(0.0, 1.0 - 2.1 * dt)
        self.velocity_x *= friction
        self.velocity_y *= friction

        max_speed = self.cell * 7.5
        speed_sq = self.velocity_x * self.velocity_x + self.velocity_y * self.velocity_y
        if speed_sq > max_speed * max_speed:
            scale = max_speed / (speed_sq ** 0.5)
            self.velocity_x *= scale
            self.velocity_y *= scale

        next_x = self.ball_x + self.velocity_x * dt
        if not self._circle_hits_wall(next_x, self.ball_y):
            self.ball_x = next_x
        else:
            self.velocity_x *= -0.25

        next_y = self.ball_y + self.velocity_y * dt
        if not self._circle_hits_wall(self.ball_x, next_y):
            self.ball_y = next_y
        else:
            self.velocity_y *= -0.25

        self._record_trail_point()
        current_cell = self._cell_at_point(self.ball_x, self.ball_y)
        if current_cell == self.goal_cell:
            self.won = True
            self.velocity_x = 0
            self.velocity_y = 0

        self._update_marker_instruction()

    def _add_static_line(self, points, width=None, color=BLUEPRINT):
        self.static_group.add(Color(color[0], color[1], color[2], color[3]))
        self.static_group.add(Line(points=points, width=width or max(dp(0.8), self.cell * 0.035)))

    def _redraw_static_map(self):
        self.static_group.clear()

        self.static_group.add(Color(*PAPER_BG))
        self.static_group.add(Rectangle(pos=self.pos, size=self.size))

        if not self.maze or not self.cell:
            return

        board_w = self.cell * self.cols
        board_h = self.cell * self.rows
        shadow_offset = dp(3)

        self.static_group.add(Color(0.08, 0.12, 0.16, 0.10))
        self.static_group.add(
            RoundedRectangle(
                pos=(self.board_x + shadow_offset, self.board_y - shadow_offset),
                size=(board_w, board_h),
                radius=[dp(16)],
            )
        )

        self.static_group.add(Color(1.0, 0.988, 0.94, 1))
        self.static_group.add(
            RoundedRectangle(
                pos=(self.board_x, self.board_y),
                size=(board_w, board_h),
                radius=[dp(16)],
            )
        )

        grid_width = max(dp(0.45), self.cell * 0.012)
        self.static_group.add(Color(0.38, 0.56, 0.72, 0.18))
        for c in range(self.cols + 1):
            x = self.board_x + c * self.cell
            self.static_group.add(Line(points=[x, self.board_y, x, self.board_y + board_h], width=grid_width))
        for r in range(self.rows + 1):
            y = self.board_y + r * self.cell
            self.static_group.add(Line(points=[self.board_x, y, self.board_x + board_w, y], width=grid_width))

        self.static_group.add(Color(0.12, 0.32, 0.58, 0.045))
        for r, row in enumerate(self.maze):
            for c, value in enumerate(row):
                if value == 1:
                    self.static_group.add(
                        Rectangle(
                            pos=(self.board_x + c * self.cell, self.board_y + (self.rows - 1 - r) * self.cell),
                            size=(self.cell, self.cell),
                        )
                    )

        line_width = max(dp(1.0), self.cell * 0.045)
        self.static_group.add(Color(*BLUEPRINT))
        for r, row in enumerate(self.maze):
            for c, value in enumerate(row):
                if value != 1:
                    continue

                left = self.board_x + c * self.cell
                bottom = self.board_y + (self.rows - 1 - r) * self.cell
                right = left + self.cell
                top = bottom + self.cell

                if r == 0 or self.maze[r - 1][c] == 0:
                    self.static_group.add(Line(points=[left, top, right, top], width=line_width))
                if r == self.rows - 1 or self.maze[r + 1][c] == 0:
                    self.static_group.add(Line(points=[left, bottom, right, bottom], width=line_width))
                if c == 0 or self.maze[r][c - 1] == 0:
                    self.static_group.add(Line(points=[left, bottom, left, top], width=line_width))
                if c == self.cols - 1 or self.maze[r][c + 1] == 0:
                    self.static_group.add(Line(points=[right, bottom, right, top], width=line_width))

        self.static_group.add(Color(0.02, 0.16, 0.34, 0.82))
        self.static_group.add(
            Line(
                rounded_rectangle=(self.board_x, self.board_y, board_w, board_h, dp(16)),
                width=max(dp(1.1), self.cell * 0.035),
            )
        )

        if self.goal_cell:
            cx, cy = self._cell_center(self.goal_cell)
            pole_bottom = cy - self.cell * 0.34
            pole_top = cy + self.cell * 0.36
            flag_w = self.cell * 0.48
            flag_h = self.cell * 0.24
            self.static_group.add(Color(0.08, 0.24, 0.43, 1))
            self.static_group.add(Line(points=[cx, pole_bottom, cx, pole_top], width=max(dp(1.2), self.cell * 0.045)))
            self.static_group.add(Color(*FLAG_RED))
            self.static_group.add(
                Rectangle(
                    pos=(cx, pole_top - flag_h),
                    size=(flag_w, flag_h),
                )
            )
            self.static_group.add(Color(0.55, 0.05, 0.04, 1))
            self.static_group.add(
                Line(
                    rectangle=(cx, pole_top - flag_h, flag_w, flag_h),
                    width=max(dp(0.8), self.cell * 0.025),
                )
            )

    def _update_trail_instructions(self):
        visible = self.trail_points[-self.max_trail_dots:]
        dot_radius = max(dp(1.7), self.cell * 0.075) if self.cell else dp(2)

        for index, (dot_color, dot) in enumerate(self.trail_refs):
            if index < len(visible) and self.cell:
                rel_x, rel_y = visible[index]
                px = self.board_x + rel_x * self.cell
                py = self.board_y + rel_y * self.cell
                age = index / max(1, len(visible) - 1)
                alpha = 0.16 + 0.58 * age
                dot_color.rgba = (TRAIL_BLUE[0], TRAIL_BLUE[1], TRAIL_BLUE[2], alpha)
                dot.pos = (px - dot_radius, py - dot_radius)
                dot.size = (dot_radius * 2, dot_radius * 2)
            else:
                dot_color.rgba = (TRAIL_BLUE[0], TRAIL_BLUE[1], TRAIL_BLUE[2], 0)
                dot.pos = (-100, -100)
                dot.size = (0, 0)

    def _update_marker_instruction(self):
        if self.ball_x is None or not self.cell:
            self.marker_shadow_color.rgba = (0.08, 0.10, 0.12, 0)
            self.marker_fill_color.rgba = (PLAYER_RED[0], PLAYER_RED[1], PLAYER_RED[2], 0)
            self.marker_outline_color.rgba = (0.48, 0.04, 0.03, 0)
            return

        radius = self.ball_radius
        self.marker_shadow_color.rgba = (0.08, 0.10, 0.12, 0.18)
        self.marker_shadow.pos = (
            self.ball_x - radius + dp(1.3),
            self.ball_y - radius - dp(1.3),
        )
        self.marker_shadow.size = (radius * 2, radius * 2)

        self.marker_fill_color.rgba = PLAYER_RED
        self.marker_fill.pos = (self.ball_x - radius, self.ball_y - radius)
        self.marker_fill.size = (radius * 2, radius * 2)

        self.marker_outline_color.rgba = (0.48, 0.04, 0.03, 1)
        self.marker_outline.circle = (self.ball_x, self.ball_y, radius)
        self.marker_outline.width = max(dp(1.0), self.cell * 0.035)


Factory.register("PaperButton", cls=PaperButton)
Factory.register("PaperCardLabel", cls=PaperCardLabel)
Factory.register("AccelMazeBoard", cls=AccelMazeBoard)


class AccelerometerMazeController:
    def __init__(self, ui, previous_orientation=None, orientation_locked=False):
        self.ui = ui
        self.board = ui.ids.board_widget
        self.status_label = ui.ids.status_label
        self.previous_orientation = previous_orientation
        self.orientation_locked = orientation_locked
        self.event = None
        self.paused = False
        self.accelerometer_enabled = False
        self.calibration = None
        self.last_status_update = 0
        self.last_error = None
        self.state = {
            "ok": True,
            "stage": "starting",
            "message": "Starting paper map maze.",
            "error": None,
            "orientation_locked": bool(orientation_locked),
            "accelerometer_enabled": False,
            "paused": False,
            "won": False,
            "style": "bright paper map",
            "static_map_cached": True,
        }
        globals()["maze_game_state"] = self.state

    def start(self):
        self.restart()
        try:
            accelerometer.enable()
            self.accelerometer_enabled = True
            self.state["accelerometer_enabled"] = True
            self._set_status("Ready. Hold the phone normally, then tilt to move.")
        except Exception as exc:
            Logger.exception("PythonHere: Could not enable accelerometer")
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.state.update(
                ok=False,
                stage="enable_accelerometer",
                error=self.last_error,
                message="Accelerometer could not be enabled.",
            )
            self._set_status("Accelerometer error: " + self.last_error)

        self.event = Clock.schedule_interval(self._tick, 1 / 60.0)
        self.state["stage"] = "running"

    def cleanup(self, restore_orientation=False):
        if self.event is not None:
            self.event.cancel()
            self.event = None
        try:
            if self.accelerometer_enabled:
                accelerometer.disable()
        except Exception:
            Logger.exception("PythonHere: Could not disable accelerometer")
        self.accelerometer_enabled = False
        self.state["accelerometer_enabled"] = False

        if restore_orientation and self.previous_orientation is not None:
            try:
                from jnius import autoclass

                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                activity = PythonActivity.mActivity
                if activity is not None:
                    activity.setRequestedOrientation(int(self.previous_orientation))
                    self.state["orientation_locked"] = False
            except Exception:
                Logger.exception("PythonHere: Could not restore previous orientation")

    def restart(self, *args):
        maze, start, goal = _make_accel_maze()
        self.board.configure(maze, start, goal)
        self.paused = False
        self.calibration = None
        self.state.update(
            ok=True,
            stage="running",
            message="New paper map maze started.",
            error=None,
            paused=False,
            won=False,
            rows=len(maze),
            cols=len(maze[0]) if maze else 0,
            trail_dots=0,
        )
        self.ui.ids.pause_button.text = "Pause"
        self._set_status("New map. Tilt to move the red marker to the flag.")

    def calibrate(self, *args):
        raw = self._read_acceleration()
        if raw is None:
            self._set_status("Waiting for accelerometer data. Try again in a moment.")
            self.state["message"] = "Calibration waiting for accelerometer data."
            return
        self.calibration = (raw[0], raw[1])
        self.state["calibration"] = {"x": raw[0], "y": raw[1]}
        self._set_status("Calibrated. Tilt gently to follow the route.")

    def toggle_pause(self, *args):
        self.paused = not self.paused
        self.state["paused"] = self.paused
        self.ui.ids.pause_button.text = "Resume" if self.paused else "Pause"
        self._set_status("Paused." if self.paused else "Running. Tilt to move.")

    def _set_status(self, message):
        self.status_label.text = str(message)
        self.state["message"] = str(message)

    def _read_acceleration(self):
        raw = accelerometer.acceleration
        if not raw or len(raw) < 2:
            return None
        if raw[0] is None or raw[1] is None:
            return None
        return float(raw[0]), float(raw[1])

    def _tick(self, dt):
        try:
            if self.paused:
                return

            raw = self._read_acceleration()
            if raw is None:
                if Clock.get_time() - self.last_status_update > 1.5:
                    self.last_status_update = Clock.get_time()
                    self._set_status("Waiting for accelerometer data.")
                return

            if self.calibration is None:
                self.calibration = (raw[0], raw[1])
                self.state["calibration"] = {"x": raw[0], "y": raw[1]}

            accel_x = raw[0] - self.calibration[0]
            accel_y = raw[1] - self.calibration[1]
            self.state["last_acceleration"] = {"x": raw[0], "y": raw[1]}
            self.board.step(dt, accel_x, accel_y)
            self.state["trail_dots"] = len(self.board.trail_points)

            if self.board.won and not self.state.get("won"):
                self.state["won"] = True
                self.state["stage"] = "won"
                self._set_status("You reached the flag. Press Restart for a new map.")

        except Exception as exc:
            Logger.exception("PythonHere: Maze game loop failed")
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.state.update(
                ok=False,
                stage="game_loop",
                error=self.last_error,
                message="Maze game loop error.",
            )
            self._set_status("Game error: " + self.last_error)
            self.paused = True
            self.state["paused"] = True


def _install_accelerometer_maze_game():
    try:
        old_cleanup = globals().get("maze_game_cleanup")
        if callable(old_cleanup):
            try:
                old_cleanup(restore_orientation=False)
            except Exception:
                Logger.exception("PythonHere: Previous maze cleanup failed")
    except Exception:
        Logger.exception("PythonHere: Could not inspect previous maze cleanup")

    previous_orientation = None
    orientation_locked = False

    try:
        from jnius import autoclass

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ActivityInfo = autoclass("android.content.pm.ActivityInfo")
        activity = PythonActivity.mActivity
        if activity is not None:
            try:
                previous_orientation = int(activity.getRequestedOrientation())
            except Exception:
                previous_orientation = None
            activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT)
            orientation_locked = True
    except Exception as exc:
        Logger.exception("PythonHere: Could not lock screen orientation")
        globals()["maze_game_orientation_error"] = f"{type(exc).__name__}: {exc}"

    KV = """
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

BoxLayout:
    orientation: "vertical"
    padding: dp(10)
    spacing: dp(8)
    canvas.before:
        Color:
            rgba: 0.985, 0.965, 0.905, 1
        Rectangle:
            pos: self.pos
            size: self.size

    PaperCardLabel:
        id: title_label
        text: "Paper Map Maze"
        size_hint_y: None
        height: dp(46)
        font_size: sp(24)
        bold: True
        halign: "center"
        valign: "middle"
        text_size: self.size

    PaperCardLabel:
        id: instruction_label
        text: "Tilt the phone to move the red marker to the flag."
        size_hint_y: None
        height: dp(50)
        font_size: sp(15)
        halign: "center"
        valign: "middle"
        text_size: self.size

    AccelMazeBoard:
        id: board_widget
        size_hint_y: 1

    GridLayout:
        cols: 3
        spacing: dp(8)
        size_hint_y: None
        height: dp(58)

        PaperButton:
            id: calibrate_button
            text: "Calibrate"
            font_size: sp(16)

        PaperButton:
            id: restart_button
            text: "Restart"
            font_size: sp(16)

        PaperButton:
            id: pause_button
            text: "Pause"
            font_size: sp(16)

    PaperCardLabel:
        id: status_label
        text: "Starting."
        size_hint_y: None
        height: dp(56)
        font_size: sp(14)
        halign: "center"
        valign: "middle"
        text_size: self.size
"""

    try:
        ui = Builder.load_string(KV)
        if ui is None:
            raise RuntimeError("Builder.load_string returned None")

        root.clear_widgets()
        root.add_widget(ui)

        controller = AccelerometerMazeController(
            ui,
            previous_orientation=previous_orientation,
            orientation_locked=orientation_locked,
        )

        ui.ids.calibrate_button.bind(on_release=controller.calibrate)
        ui.ids.restart_button.bind(on_release=controller.restart)
        ui.ids.pause_button.bind(on_release=controller.toggle_pause)

        globals()["maze_game_ui"] = ui
        globals()["maze_game_controller"] = controller

        def maze_game_cleanup(restore_orientation=False):
            controller.cleanup(restore_orientation=restore_orientation)

        globals()["maze_game_cleanup"] = maze_game_cleanup

        controller.start()

        if orientation_locked:
            controller.state["orientation_message"] = "Portrait orientation locked."
        else:
            controller.state["orientation_message"] = "Portrait lock was not confirmed."

    except Exception as exc:
        Logger.exception("PythonHere: Could not load accelerometer maze game")
        globals()["maze_game_state"] = {
            "ok": False,
            "stage": "install",
            "error": f"{type(exc).__name__}: {exc}",
            "message": "Could not load accelerometer maze game.",
        }
        _maze_show_error("Maze error", f"{type(exc).__name__}: {exc}")


_install_accelerometer_maze_game()
```

```{code-cell}
%there -d 1 screenshot -w 250
```
