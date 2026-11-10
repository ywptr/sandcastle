"""Versioned editorial planning presets, not validated media-generation claims."""
import copy
import json
from pathlib import Path
from fastapi import HTTPException


def styles():
    return json.loads(Path(__file__).with_name("styles.json").read_text())


def style_snapshot(style_id, version=None):
    found = next((s for s in styles() if s["id"] == style_id and (version is None or s["version"] == version)), None)
    if found is None:
        raise HTTPException(422, "Unknown storytelling style or version")
    return copy.deepcopy(found)
