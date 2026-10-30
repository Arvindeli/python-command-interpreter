import contextlib
import errno
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main as shell


class InterpreterTests(unittest.TestCase):
    def setUp(self):
        original_directory = os.getcwd()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.chdir, original_directory)
        os.chdir(temporary.name)
        self.directory = Path(temporary.name)

    def output(self, function, *args):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            function(*args)
        return buffer.getvalue()

    def session(self, inputs):
        with patch("builtins.input", side_effect=inputs) as prompt:
            result = self.output(shell.main)
        return result, prompt

    def test_quoted_filesystem_sequence(self):
        result, _ = self.session([
            'mkdir "demo folder"', 'cd "demo folder"',
            'touch "notes one.txt"', 'cp "notes one.txt" "notes two.txt"',
            'mv "notes two.txt" "renamed notes.txt"', 'cat "renamed notes.txt"',
            'rm "notes one.txt"', 'rm "renamed notes.txt"',
            'cd ..', 'rmdir "demo folder"', 'exit',
        ])
        self.assertEqual(result, "")
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_pwd_ls_cd_and_touch_alias(self):
        Path(".hidden").write_text("keep")
        shell.handle_functions("ni", ["created"], 1)
        self.assertEqual(Path("created").read_bytes(), b"")
        self.assertEqual(self.output(shell.handle_pwd).strip(), str(self.directory))
        self.assertEqual(set(self.output(shell.handle_ls).splitlines()), {".hidden", "created"})
        with patch.dict(os.environ, {"HOME": str(self.directory)}):
            self.assertEqual(self.output(shell.handle_functions, "cd", [], 0), "")
            self.assertEqual(os.getcwd(), str(self.directory))
        shell.handle_touch_ni(".hidden")
        self.assertEqual(Path(".hidden").read_text(), "keep")

    def test_cat_preserves_text_and_line_endings(self):
        for content in (b"", b"hello", b"hello\n", b"one\r\ntwo\r\n"):
            with self.subTest(content=content):
                Path("text").write_bytes(content)
                self.assertEqual(self.output(shell.handle_cat, "text"), content.decode("ascii"))

    def test_cat_reports_decoding_failure(self):
        error = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        with patch("builtins.open", side_effect=error):
            self.assertIn("cannot decode", self.output(shell.handle_cat, "text"))

    def test_copy_and_move_overwrite_behavior(self):
        Path("source").write_text("new contents")
        Path("target").write_text("old contents")
        shell.handle_cp("source", "target")
        self.assertEqual(Path("target").read_text(), "new contents")
        Path("folder").mkdir()
        Path("folder/source").write_text("old contents")
        shell.handle_cp("source", "folder")
        self.assertEqual(Path("folder/source").read_text(), "new contents")
        self.assertIn("error:", self.output(shell.handle_mv, "source", "folder"))
        self.assertTrue(Path("source").exists())
        shell.handle_mv("source", "target")
        self.assertFalse(Path("source").exists())
        self.assertEqual(Path("target").read_text(), "new contents")

    def test_same_file_and_directory_sources(self):
        Path("file").write_text("keep")
        Path("folder").mkdir()
        self.assertIn("same file", self.output(shell.handle_cp, "file", "file"))
        for handler in (shell.handle_cp, shell.handle_mv):
            self.assertIn("source is a directory", self.output(handler, "folder", "target"))
        self.assertEqual(Path("file").read_text(), "keep")

    def test_missing_paths_and_invalid_parent(self):
        Path("file").write_text("keep")
        for path in ("missing/child", "file/child"):
            for handler in (shell.handle_cd, shell.handle_cat, shell.handle_touch_ni,
                            shell.handle_mkdir, shell.handle_rm, shell.handle_rmdir):
                with self.subTest(path=path, handler=handler.__name__):
                    self.assertIn("error:", self.output(handler, path))
            for handler in (shell.handle_cp, shell.handle_mv):
                self.assertIn("error:", self.output(handler, path, "target"))
                self.assertIn("error:", self.output(handler, "file", path))
        self.assertEqual(Path("file").read_text(), "keep")

    def test_existing_and_nonempty_directories(self):
        Path("folder").mkdir()
        Path("folder/child").write_text("keep")
        for handler in (shell.handle_mkdir, shell.handle_rm, shell.handle_rmdir):
            self.assertIn("error:", self.output(handler, "folder"))
        self.assertEqual(Path("folder/child").read_text(), "keep")

    def test_permission_failures(self):
        Path("source").write_text("keep")
        cases = (
            ("os.getcwd", shell.handle_pwd, ()),
            ("os.listdir", shell.handle_ls, ()),
            ("os.chdir", shell.handle_cd, ("folder",)),
            ("builtins.open", shell.handle_touch_ni, ("file",)),
            ("builtins.open", shell.handle_cat, ("source",)),
            ("os.mkdir", shell.handle_mkdir, ("folder",)),
            ("os.remove", shell.handle_rm, ("source",)),
            ("os.rmdir", shell.handle_rmdir, ("folder",)),
            ("shutil.copy", shell.handle_cp, ("source", "target")),
            ("shutil.move", shell.handle_mv, ("source", "target")),
        )
        for target, handler, args in cases:
            with self.subTest(target=target, handler=handler.__name__):
                with patch(target, side_effect=PermissionError(errno.EACCES, "Permission denied")):
                    self.assertIn("Permission denied", self.output(handler, *args))

    def test_operation_time_failures(self):
        Path("source").write_text("keep")
        for target, handler, args in (
            ("os.remove", shell.handle_rm, ("source",)),
            ("shutil.copy", shell.handle_cp, ("source", "target")),
            ("shutil.move", shell.handle_mv, ("source", "target")),
        ):
            with self.subTest(target=target):
                with patch(target, side_effect=FileNotFoundError(errno.ENOENT, "No such file")):
                    self.assertIn("No such file", self.output(handler, *args))
        with patch("os.getcwd", side_effect=FileNotFoundError(errno.ENOENT, "Current directory removed")):
            self.assertIn("Current directory removed", self.output(shell.handle_pwd))

    def test_failed_copy_can_leave_partial_destination(self):
        Path("source").write_text("new contents")
        Path("target").write_text("old contents")

        def partial_copy(source, destination):
            Path(destination).write_text("partial")
            raise OSError(errno.ENOSPC, "No space left on device")

        with patch("shutil.copy", side_effect=partial_copy):
            self.assertIn("No space", self.output(shell.handle_cp, "source", "target"))
        self.assertEqual(Path("target").read_text(), "partial")

    def test_eof_at_either_prompt_exits_without_execution(self):
        for inputs in ([EOFError], ["pwwd", EOFError]):
            with self.subTest(inputs=inputs), patch.object(shell, "handle_functions") as dispatch:
                _, prompt = self.session(inputs)
                dispatch.assert_not_called()
                self.assertEqual(prompt.call_count, len(inputs))

    def test_interrupt_at_either_prompt_cancels_then_accepts_next_command(self):
        for inputs in ([KeyboardInterrupt, "pwd", "exit"],
                       ["pwwd", KeyboardInterrupt, "pwd", "exit"]):
            with self.subTest(inputs=inputs), patch.object(shell, "handle_functions") as dispatch:
                self.session(inputs)
                dispatch.assert_called_once_with("pwd", [], 0)

    def test_typo_acceptance_and_decline(self):
        for answer, executions in (("y", 1), ("yes", 1), ("yeah", 1), ("n", 0)):
            with self.subTest(answer=answer), patch.object(shell, "handle_functions") as dispatch:
                _, prompt = self.session(["pwwd", answer, "exit"])
                self.assertIn("pwd", prompt.call_args_list[1].args[0])
                self.assertEqual(dispatch.call_count, executions)

    def test_syntax_unknown_command_and_argument_counts(self):
        result, _ = self.session(['touch "unfinished', "zzzzzzzz", "exit extra", "", "exit"])
        self.assertIn("syntax error", result)
        self.assertIn("command not found", result)
        self.assertIn("usage: exit", result)
        for command in shell.VALID_COMMANDS:
            if command != "exit":
                self.assertIn("usage:", self.output(shell.handle_functions, command, ["a", "b", "c"], 3))


if __name__ == "__main__":
    unittest.main()
