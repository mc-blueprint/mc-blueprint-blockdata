"""Mojang公式server jarの取得とキャッシュ。"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path

VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


def cache_dir() -> Path:
    """OSごとのmc-blueprint jarキャッシュを返す。"""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if os.name == "nt" and local_app_data:
        return Path(local_app_data) / "mc-blueprint" / "cache" / "jars"
    return Path.home() / ".cache" / "mc-blueprint" / "jars"


def download_server_jar(version: str, dest_dir: Path | None = None) -> Path:
    """Mojang公式manifestからserver jarを取得し、SHA-1検証してキャッシュする。"""
    dest_dir = dest_dir or cache_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    jar_path = dest_dir / f"server-{version}.jar"
    manifest = _fetch_json(VERSION_MANIFEST_URL)
    entry = next((item for item in manifest["versions"] if item["id"] == version), None)
    if entry is None:
        raise ValueError(f"Mojang version manifestに版 {version!r} がありません")
    server = _fetch_json(entry["url"])["downloads"]["server"]
    expected = server["sha1"]
    if jar_path.is_file() and _sha1(jar_path) == expected:
        return jar_path

    temporary = jar_path.with_suffix(".jar.tmp")
    try:
        urllib.request.urlretrieve(server["url"], temporary)
        if _sha1(temporary) != expected:
            raise ValueError(f"取得したserver jarのSHA-1が一致しません: {version}")
        temporary.replace(jar_path)
    finally:
        temporary.unlink(missing_ok=True)
    return jar_path


def _fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def _sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
