#!/usr/bin/env python3
"""Run from the checkout; shares all provider storage/encryption logic with the API."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from app.llm.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
