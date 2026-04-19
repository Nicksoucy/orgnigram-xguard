#!/usr/bin/env python3
"""Heidys Daily v3 — Wrapper: runs original sync + Haiku scoring + email."""
import subprocess, sys, os

PYTHON = sys.executable
CRONS = os.path.dirname(os.path.abspath(__file__))

# Step 1: Run original Heidys daily sync (transcription)
print("=== Step 1: Heidys Daily Sync ===")
r1 = subprocess.run([PYTHON, os.path.join(CRONS, "nitro_heidys_daily.py")],
                    cwd=CRONS, timeout=7200)

# Step 2: Run Haiku scoring + email
print("=== Step 2: Haiku Scoring + Email ===")
env = {**os.environ, "CLAUDE_CODE_GIT_BASH_PATH": r"C:\Program Files\Git\bin\bash.exe"}
r2 = subprocess.run([PYTHON, os.path.join(CRONS, "heidys_haiku_patch.py")],
                    cwd=CRONS, timeout=600, env=env)

sys.exit(r1.returncode)
