"""Mojang data generator reportsの変換。"""

from __future__ import annotations

import json
from pathlib import Path


def convert_blocks(blocks_json: Path) -> dict[str, dict[str, object]]:
    """blocks.jsonを ``{id: {properties, default}}`` に変換する。"""
    raw = json.loads(blocks_json.read_text(encoding="utf-8"))
    result = {}
    for block_id, info in sorted(raw.items()):
        properties = {name: list(values) for name, values in info.get("properties", {}).items()}
        default = next(
            (state.get("properties", {}) for state in info["states"] if state.get("default")),
            {},
        )
        result[block_id] = {"properties": properties, "default": dict(default)}
    return result


def read_data_version(server_jar: Path) -> int:
    """server jarのversion.jsonからDataVersionを読む。"""
    from zipfile import ZipFile

    with ZipFile(server_jar) as jar, jar.open("version.json") as stream:
        return int(json.load(stream)["world_version"])
