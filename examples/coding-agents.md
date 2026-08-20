# Coding agent skills

PythonHere gives Python coding agents a live Android runtime to work with. It
includes a `pythonhere` skill for working with the running Kivy application and
Android environment, while its `herethere` dependency provides the `there-cli`
skill for connecting, executing code, and transferring files.

## Prerequisites

Install and start PythonHere on the Android device as described in
[Installation](../install.md#remote-side).

The setup below uses Python 3.10 or newer and
[uv](https://docs.astral.sh/uv/).

## Create a local workspace

Create a minimal project and install PythonHere:

```console
uv init --bare my-pythonhere-project
cd my-pythonhere-project
uv add pythonhere
```

## Install the skills

Run [Library Skills](https://library-skills.io/) from the workspace:

```console
uvx library-skills --skill pythonhere --skill there-cli
```

Library Skills links the selected skills into the project's `.agents/skills`
directory. The explicit selectors include `there-cli` from the `herethere`
dependency without selecting skills from other transitive packages. Add
`--claude` to also install and manage the skills in `.claude/skills`.

Run the command again after upgrading PythonHere or `herethere` so Library Skills
can check and repair the managed links.

## Connect to PythonHere

Create a `there.env` file in the workspace and fill it with the host, port,
username, and password shown in the PythonHere app's Settings screen. See the
[`there.env` example](commands.md#there-env-example)
for the file format.

With PythonHere running on the Android device, check the connection:

```console
uv run there --json ping
```

The CLI finds `there.env` in the current directory or a parent directory. See
[The `there` command-line interface](there-cli.md)
for execution, inspection, file-transfer, and troubleshooting commands.

## What the skills cover

The [`there-cli` skill](https://github.com/b3b/herethere/blob/master/herethere/.agents/skills/there-cli/SKILL.md)
documents the generic `herethere` connection, CLI syntax, remote execution,
structured results, and file transfers.

The [`pythonhere` skill](https://github.com/b3b/pythonhere/blob/master/pythonhere/.agents/skills/pythonhere/SKILL.md)
adds PythonHere-specific knowledge about the running Kivy application, Android
environment, and `tools_here` helpers for UI snapshots, runtime information,
and screenshots.

Once `uv run there --json ping` succeeds, the workspace is ready for the coding
agent to use the installed skills with the running PythonHere application.
