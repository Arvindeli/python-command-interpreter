# Python command interpreter

A Python command interpreter with quoted-argument parsing, filesystem commands,
input validation, and interactive command suggestions. Built with the Python
standard library.

## Run

Open a terminal in the project folder and run:

```bash
python3 main.py
```

Commands operate on real files relative to the interpreter's current directory.
Absolute paths and `cd` can access other directories.

## Commands

| Syntax | Behavior |
| --- | --- |
| `pwd` | Print the current directory. |
| `ls` | List current-directory entries, including hidden entries. |
| `cd [path]` | Change directory; no argument goes home. Expands `~`. |
| `touch file` or `ni file` | Create a file if absent; preserve existing contents without explicitly updating timestamps. |
| `mkdir directory` | Create one directory; its parent must exist. |
| `rm file` | Remove a file or file symlink; refuse directories and symlinks to directories. Broken symlinks are unlinked. |
| `rmdir directory` | Remove an empty directory. |
| `cat file` | Display text using Python's default text encoding without adding a newline. |
| `cp source destination` | Copy a non-directory source to a file or into a directory. |
| `mv source destination` | Move a non-directory source to a path or into a directory. |
| `exit` | Exit the interpreter. |

Commands validate argument counts and report filesystem errors. Parsing uses
`shlex`, so filenames containing spaces can be quoted:

```text
mkdir "demo folder"
cd "demo folder"
touch "notes one.txt"
cp "notes one.txt" "notes two.txt"
mv "notes two.txt" "renamed notes.txt"
ls
```

Unrecognized commands may receive a suggested correction. Confirm with `y`,
`yes`, or `yeah`; other answers decline it. EOF at either prompt exits cleanly.
Ctrl+C at either prompt cancels the pending input and returns to the main prompt.

## File operations

- Copying, moving, and deletion proceed without confirmation; deletion has no undo.
- Copying to an existing file replaces its contents, including a same-named file
  inside a destination directory.
- On Linux, moving to an existing file can replace it. Moving into a directory
  refuses an existing same-named destination. Replacement behavior follows
  Python's `shutil` functions and the operating system.
- Copies and moves across filesystems are not atomic. A failed operation can
  leave a destination created or partially changed.
- `cat` reports decoding errors; text already displayed remains on screen.

## Scope

Implements built-in commands with one source operand and, for copy/move, one
destination. External programs, pipes, redirection, recursive directory
operations, command options, wildcards, and environment-variable expansion are
outside its scope. Only `cd` expands `~`. Ctrl+C cancellation applies at the
input prompts.

## Tests

From the project folder:

```bash
python3 -m unittest -v test_main.py
```

Tests cover quoted arguments, filesystem operations, overwrite behavior, input
handling, and error reporting. They use temporary directories and simulated
permission failures and races, restoring the original working directory afterward.
