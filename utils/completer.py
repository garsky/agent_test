from __future__ import annotations

import os
from pathlib import Path

try:
    import readline
    _HAS_READLINE = True
except ImportError:
    _HAS_READLINE = False

COMMANDS = [
    "quit", "reset", "switch", "help", "config",
    "kb add", "kb update", "kb build", "kb list", "kb search",
    "platform list", "platform add vendor", "platform add sub",
    "platform remove vendor", "platform remove sub",
]

KB_SUB_COMMANDS = ["add", "update", "build", "list", "search"]
PLATFORM_SUB_COMMANDS = ["list", "add vendor", "add sub", "remove vendor", "remove sub"]

_completer_instance = None


class CDACompleter:
    def __init__(self):
        self.commands = COMMANDS
        self.matches = []

    def complete(self, text: str, state: int) -> str | None:
        if state == 0:
            line = readline.get_line_buffer().lstrip()
            self.matches = self._get_matches(line, text)
        if state < len(self.matches):
            return self.matches[state]
        return None

    def _get_matches(self, line: str, text: str) -> list[str]:
        if line.startswith("kb add "):
            return self._complete_kb_add(text, line)
        if line.startswith("kb "):
            return [c for c in KB_SUB_COMMANDS if c.startswith(text)]
        if line.startswith("platform "):
            return [c for c in PLATFORM_SUB_COMMANDS if c.startswith(text)]
        if " " not in line:
            return [c for c in self.commands if c.startswith(text)]
        return []

    def _complete_kb_add(self, text: str, line: str) -> list[str]:
        if text.startswith("--"):
            return [f for f in ("--global", "--vendor") if f.startswith(text)]
        return self._complete_file_path(text, line)

    def _complete_file_path(self, text: str, line: str) -> list[str]:
        prefix = line.split(" ", 2)[-1] if " --" not in line else text
        if not prefix:
            prefix = ""

        expanded = os.path.expanduser(prefix)
        expanded = os.path.expandvars(expanded)

        if not expanded:
            search_dir = "."
            base_name = ""
        elif expanded.endswith(os.sep) or expanded.endswith("/"):
            search_dir = expanded
            base_name = ""
        else:
            search_dir = os.path.dirname(expanded) or "."
            base_name = os.path.basename(expanded)

        try:
            entries = os.listdir(search_dir)
        except OSError:
            return []

        matches = []
        for entry in sorted(entries):
            if entry.startswith(".") and not base_name.startswith("."):
                continue
            if not entry.startswith(base_name):
                continue
            full = os.path.join(search_dir, entry)
            if os.path.isdir(full):
                matches.append(entry + os.sep)
            else:
                if entry.lower().endswith((".md", ".txt", ".pdf", ".docx", ".pptx", ".xlsx")):
                    matches.append(entry)

        return matches


def setup_readline():
    if not _HAS_READLINE:
        return

    global _completer_instance
    _completer_instance = CDACompleter()
    readline.set_completer(_completer_instance.complete)
    readline.parse_and_bind("tab: complete")
    readline.set_completer_delims(" \t\n;")
