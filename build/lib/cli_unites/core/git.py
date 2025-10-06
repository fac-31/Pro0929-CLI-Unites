"""Helpers to capture Git metadata without hard failures when outside a repo."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, Optional


def _run_git_command(args: list[str], cwd: Optional[Path] = None) -> Optional[str]:
    try:
        output = subprocess.check_output(
            ["git", *args],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return output.decode().strip() or None


def get_git_context(cwd: Optional[Path] = None) -> Dict[str, Optional[str]]:
    if os.environ.get("CLI_UNITES_DISABLE_GIT") == "1":
        return {"commit": None, "branch": None, "root": None}

    commit = _run_git_command(["rev-parse", "HEAD"], cwd=cwd)
    branch = _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    root = _run_git_command(["rev-parse", "--show-toplevel"], cwd=cwd)
    return {"commit": commit, "branch": branch, "root": root}
