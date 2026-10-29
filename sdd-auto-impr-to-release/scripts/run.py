#!/usr/bin/env python3
"""Local helpers for the GigaCode orchestrator. Jira/Bitbucket writes stay in atomic skills."""

from __future__ import annotations

import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SRC = SKILL_DIR / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sdd_auto_impr_to_release.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
