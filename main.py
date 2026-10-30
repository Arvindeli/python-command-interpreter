import os
import shlex
import shutil
import difflib

VALID_COMMANDS = [
    "pwd",
    "ls",
    "cd",
    "touch",
    "ni",
    "mkdir",
    "rm",
    "rmdir",
    "cat",
    "exit",
    "cp",
    "mv",
]

def report_filesystem_error(command, error):
    reason = error.strerror or str(error) or "operation failed"
    path = f": {error.filename!r}" if error.filename is not None else ""
    print(f"error: {command}: {reason}{path}")


def handle_pwd():
    try:
        print(os.getcwd())
    except OSError as error:
        report_filesystem_error("pwd", error)


def handle_ls():
    try:
        for item in os.listdir("."):
            print(item)
    except OSError as error:
        report_filesystem_error("ls", error)


def handle_cd(path):
    try:
        os.chdir(os.path.expanduser(path))
    except OSError as error:
        report_filesystem_error("cd", error)


def handle_touch_ni(name):
    try:
        with open(name, "a"):
            pass
    except OSError as error:
        report_filesystem_error("touch/ni", error)


def handle_mkdir(name):
    try:
        os.mkdir(name)
    except OSError as error:
        report_filesystem_error("mkdir", error)


def handle_rm(oldfile):
    if os.path.isdir(oldfile):
        print(f"error: cannot remove '{oldfile}': is a directory")
        return
    try:
        os.remove(oldfile)
    except OSError as error:
        report_filesystem_error("rm", error)


def handle_rmdir(olddir):
    try:
        os.rmdir(olddir)
    except OSError as error:
        report_filesystem_error("rmdir", error)


def handle_cat(file):
    try:
        with open(file, "r", newline="") as text_file:
            for line in text_file:
                print(line, end="")
    except UnicodeDecodeError:
        print("error: cat: cannot decode file using the current text encoding")
    except OSError as error:
        report_filesystem_error("cat", error)


def handle_cp(source, destination):
    try:
        if not validate_source_and_destination(source, destination):
            return
        shutil.copy(source, destination)
    except shutil.SameFileError:
        print("error: source and destination are the same file")
    except OSError as error:
        report_filesystem_error("cp", error)


def handle_mv(source, destination):
    try:
        if not validate_source_and_destination(source, destination):
            return
        shutil.move(source, destination)
    except shutil.SameFileError:
        print("error: source and destination are the same file")
    except OSError as error:
        report_filesystem_error("mv", error)


def handle_functions(command, args, args_length):
    if command == "pwd":
        if args_length == 0:
            handle_pwd()
        else:
            print("usage: pwd")
    elif command == "ls":
        if args_length == 0:
            handle_ls()
        else:
            print("usage: ls")
    elif command == "cd":
        if args_length == 0:
            handle_cd("~")
        elif args_length == 1:
            handle_cd(args[0])
        else:
            print("usage: cd path")
    elif command in ["ni", "touch"]:
        if args_length == 0:
            print("missing file operand")
        elif args_length == 1:
            handle_touch_ni(args[0])
        else:
            print("usage: touch/ni file")
    elif command == "mkdir":
        if args_length == 0:
            print("missing directory operand")
        elif args_length == 1:
            handle_mkdir(args[0])
        else:
            print("usage: mkdir directory")
    elif command == "rm":
        if args_length == 0:
            print("missing file operand")
        elif args_length == 1:
            handle_rm(args[0])
        else:
            print("usage: rm file")
    elif command == "rmdir":
        if args_length == 0:
            print("missing directory operand")
        elif args_length == 1:
            handle_rmdir(args[0])
        else:
            print("usage: rmdir directory")
    elif command == "cat":
        if args_length == 0:
            print("missing file operand")
        elif args_length == 1:
            handle_cat(args[0])
        else:
            print("usage: cat file")
    elif command == "cp":
        if args_length == 0:
            print("missing source and destination operand")
        elif args_length == 1:
            print("missing destination operand")
        elif args_length == 2:
            handle_cp(args[0], args[1])
        else:
            print("usage: cp source destination")
    elif command == "mv":
        if args_length == 0:
            print("missing source and destination operand")
        elif args_length == 1:
            print("missing destination operand")
        elif args_length == 2:
            handle_mv(args[0], args[1])
        else:
            print("usage: mv source destination")

def validate_source_and_destination(source, destination):
    os.stat(source)

    if os.path.isdir(source):
        print(f"error: source is a directory: '{source}'")
        return False

    destination_parent = os.path.dirname(destination)
    if destination_parent == "":
        destination_parent = "."

    os.stat(destination_parent)

    if not os.path.isdir(destination_parent):
        print(f"error: destination parent is not a directory: '{destination_parent}'")
        return False

    return True

def main():
    while True:
        try:
            text = input("simple-shell>").strip()
        except EOFError:
            print()
            return
        except KeyboardInterrupt:
            print()
            continue

        try:
            parts = shlex.split(text)
        except ValueError:
            print("syntax error")
            continue
        except SyntaxError:
            print("syntax error")
            continue

        if not parts:
            continue

        command = parts[0]
        args = parts[1:]
        args_length = len(args)

        if command == "exit":
            if args_length != 0:
                print("usage: exit")
                continue
            else:
                break

        elif command in VALID_COMMANDS:
            handle_functions(command, args, args_length)
        else:
            matches = difflib.get_close_matches(command, VALID_COMMANDS, n=1, cutoff=0.6)

            if matches:
                try:
                    user_input = input(f"did you mean '{matches[0]}'? [y/n] ")
                except EOFError:
                    print()
                    return
                except KeyboardInterrupt:
                    print()
                    continue
                command = matches[0]

                if user_input.lower() in ["y", "yes", "yeah"]:
                    if command == "exit":
                        if args_length != 0:
                            print("usage: exit")
                            continue
                        else:
                            break
                    else:
                        handle_functions(command, args, args_length)
                else:
                    continue
            else:
                print(f"command not found: {command}")


if __name__ == "__main__":
    main()
