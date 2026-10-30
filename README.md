# Python command interpreter

A Python command interpreter with quoted-argument parsing, filesystem commands, input validation, and interactive command suggestions. Built with the Python standard library.

Open a terminal in the project folder and run:

```bash
python3 main.py
```

Commands operate relative to the interpreter's current directory. This is not a
sandbox: absolute paths and `cd` can reach files outside the project folder.
For a demonstration, use a disposable directory and disposable files.

## Commands

| Syntax | Behavior |
| --- | --- |
| `pwd` | Print the current directory. |
| `ls` | List current-directory entries, including hidden entries; order is unspecified. |
| `cd [path]` | Change directory; no argument goes home. Expands `~`. |
| `touch file` or `ni file` | Create an empty file if absent; preserve existing contents. Existing-file timestamps are not explicitly updated. |
| `mkdir directory` | Create one directory; its parent must exist. |
| `rm file` | Remove a file without confirmation; refuse directories and symlinks to directories. File symlinks and broken symlinks are unlinked. |
| `rmdir directory` | Remove an empty directory without confirmation. |
| `cat file` | Display text without adding a newline, using Python's default text encoding. Decoding failures display an error. |
| `cp source destination` | Copy a non-directory source to a file or into a directory. |
| `mv source destination` | Move a non-directory source to a path or into a directory. |
| `exit` | Exit; no arguments accepted. |

Parsing uses `shlex`, so quote filenames containing spaces:

```text
mkdir "demo folder"
cd "demo folder"
touch "notes one.txt"
cp "notes one.txt" "notes two.txt"
mv "notes two.txt" "renamed notes.txt"
```

Unrecognized commands may receive one typo suggestion. Confirm with `y`, `yes`,
or `yeah`; other answers decline it. EOF at either prompt exits cleanly. Ctrl+C
at either prompt cancels that input and returns to the main prompt without
executing the pending command.

## File changes and limitations

- Copy and move operations do not request overwrite confirmation.
- `cp source existing_file` replaces its contents. Copying into a directory can
  overwrite a same-named file inside it.
- On Linux, `mv source existing_file` can replace the destination. Moving into a
  directory refuses an already existing same-named destination. Exact replacement
  behavior follows the operating system and Python's `shutil` functions.
- Copying is not atomic. A failed copy can leave a destination created, truncated,
  or partially changed. A move that falls back to copying across filesystems can
  also leave destination changes after failure. Errors do not imply rollback.
- Deletion has no undo or confirmation. `rmdir` refuses nonempty directories.
- Directory copying/moving, recursive operations, command options, multiple file
  operands, external commands, pipes, redirection, wildcard expansion, and
  environment-variable expansion are unsupported. Only `cd` expands `~`.
- Ctrl+C recovery is implemented at the prompts; interruption of a running
  filesystem operation is not handled. `cat` can display some text before a later
  read or decoding error.

## Checks

From a terminal in the project folder:

```bash
python3 -m unittest -v test_main.py
```

Tests use temporary directories, restore the original working directory, and mock
permission failures and races. Existing sample files are not used or changed.
