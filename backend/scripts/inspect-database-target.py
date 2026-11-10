#!/usr/bin/env python3
"""Safe production target inspection. Intentionally does not read any dotenv file."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ops.database_target import main

if __name__ == "__main__":
    raise SystemExit(main())
