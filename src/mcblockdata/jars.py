"""Mojang公式server jarの取得とキャッシュ。"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.request
from pathlib import Path
from zipfile import ZipFile

VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


def cache_dir() -> Path:
    """OSごとのmc-blueprint jarキャッシュを返す。"""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if os.name == "nt" and local_app_data:
        return Path(local_app_data) / "mc-blueprint" / "cache" / "jars"
    return Path.home() / ".cache" / "mc-blueprint" / "jars"


def download_server_jar(version: str, dest_dir: Path | None = None) -> Path:
    return _download_jar(version, "server", dest_dir)


def download_client_jar(version: str, dest_dir: Path | None = None) -> Path:
    """Mojang公式manifestからclient jarを取得し、SHA-1検証してキャッシュする。"""
    return _download_jar(version, "client", dest_dir)


def _download_jar(version: str, side: str, dest_dir: Path | None = None) -> Path:
    """Mojang公式manifestから指定側のjarを取得し、SHA-1検証してキャッシュする。"""
    dest_dir = dest_dir or cache_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    jar_path = dest_dir / f"{side}-{version}.jar"
    manifest = _fetch_json(VERSION_MANIFEST_URL)
    entry = next((item for item in manifest["versions"] if item["id"] == version), None)
    if entry is None:
        raise ValueError(f"Mojang version manifestに版 {version!r} がありません")
    download = _fetch_json(entry["url"])["downloads"][side]
    expected = download["sha1"]
    if jar_path.is_file() and _sha1(jar_path) == expected:
        return jar_path

    with tempfile.NamedTemporaryFile(dir=dest_dir, prefix=f"{jar_path.name}.", delete=False) as f:
        temporary = Path(f.name)
    try:
        urllib.request.urlretrieve(download["url"], temporary)
        if _sha1(temporary) != expected:
            raise ValueError(f"取得した{side} jarのSHA-1が一致しません: {version}")
        try:
            temporary.replace(jar_path)
        except PermissionError:
            # Windowsでは同時replaceが拒否される。先行取得の検証済みjarだけ再利用する。
            if not jar_path.is_file() or _sha1(jar_path) != expected:
                raise
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


def read_server_entries(server_jar: Path, prefix: str) -> dict[str, bytes]:
    """Bundler形式を含むserver jarから指定prefixのデータを読む。"""
    import io

    with ZipFile(server_jar) as outer:
        nested_name = next(
            (
                name
                for name in outer.namelist()
                if name.startswith("META-INF/versions/") and name.endswith(".jar")
            ),
            None,
        )
        if nested_name is None:
            return {name: outer.read(name) for name in outer.namelist() if name.startswith(prefix)}
        with ZipFile(io.BytesIO(outer.read(nested_name))) as inner:
            return {name: inner.read(name) for name in inner.namelist() if name.startswith(prefix)}
