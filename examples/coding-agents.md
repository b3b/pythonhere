# Coding agent skills

PythonHere includes a `pythonhere` agent skill with instructions for working
inside the running Kivy and Android application. Its Herethere dependency also
includes a `there-cli` skill for the transport, command syntax, structured
results, and file transfers.

## Install the skills

After installing PythonHere in your project environment, run
[Library Skills](https://library-skills.io/) from that project:

```console
uvx library-skills --skill pythonhere --skill there-cli
```

Library Skills links the selected skills into the project's `.agents/skills`
directory. The explicit selectors include `there-cli` even though Herethere is
a transitive dependency, without selecting skills from every transitive
package. Add `--claude` to also install and manage the skills in
`.claude/skills`.

Run the command again after upgrading PythonHere or Herethere so Library Skills
can check and repair the managed links.

## What the skill uses

The `pythonhere` skill uses the `there` CLI to execute code and inspect the
running application. It also uses PythonHere's `tools_here` runtime helpers for
UI snapshots, runtime information, and screenshots. See
[The `there` command-line interface](https://herethere.me/pythonhere/examples/there-cli.html)
for the commands and helper examples.
