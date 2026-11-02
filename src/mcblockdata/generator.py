"""Minecraft版ごとのblockdataを組み立てる。"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from mcblockdata import __version__
from mcblockdata.classification import classify_blocks
from mcblockdata.colors import extract_faces, extract_tints
from mcblockdata.reports import convert_blocks, read_data_version
from mcblockdata.visuals import enrich_blocks, read_biomes

REPOSITORY = "mc-blueprint/mc-blueprint-blockdata"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "blockdata.schema.json"


def run_data_generator(server_jar: Path, output_dir: Path, java: str = "java") -> Path:
    """Mojangのdata generatorを実行し、blocks.jsonを返す。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        java,
        "-DbundlerMainClass=net.minecraft.data.Main",
        "-jar",
        str(server_jar.resolve()),
        "--reports",
        "--output",
        str(output_dir.resolve()),
    ]
    try:
        subprocess.run(command, cwd=output_dir, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Mojang data generatorが終了コード{exc.returncode}で失敗しました。"
            "1.21系はJava 21、26系はJava 25を指定してください。"
        ) from exc
    blocks_json = output_dir / "reports" / "blocks.json"
    if not blocks_json.is_file():
        raise FileNotFoundError(f"data generatorがreportsを生成しませんでした: {blocks_json}")
    return blocks_json


def build_version(
    version: str, server_jar: Path, java: str = "java", client_jar: Path | None = None
) -> dict:
    """server jarから版データを生成する。client jarを渡すと面色も抽出する。"""
    with tempfile.TemporaryDirectory(prefix=f"mcblockdata-{version}-") as temporary:
        blocks_json = run_data_generator(server_jar, Path(temporary), java)
        blocks = convert_blocks(blocks_json)
    families = classify_blocks(blocks, server_jar)
    enrich_blocks(blocks)
    tints = {}
    if client_jar is not None:
        for block_id, faces in extract_faces(client_jar, blocks).items():
            blocks[block_id]["faces"] = faces
        tints = extract_tints(client_jar, read_biomes(server_jar))
    data = {
        "formatVersion": 1,
        "minecraftVersion": version,
        "dataVersion": read_data_version(server_jar),
        "generator": {"repository": REPOSITORY, "version": __version__, "commit": _commit()},
        "blocks": blocks,
        "families": families,
        "tints": tints,
    }
    validate(data)
    output = Path("dist") / f"blockdata-{version}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def validate(data: dict) -> None:
    """blockdata v1 JSON Schemaでデータを検証する。"""
    from jsonschema import Draft202012Validator, ValidationError

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(data)
    except ValidationError as exc:
        raise ValueError(f"blockdata schema検証に失敗しました: {exc.message}") from exc
    block_ids = data["blocks"]
    for family, shapes in data["families"].items():
        for shape, block_id in shapes.items():
            if block_id not in block_ids:
                raise ValueError(
                    f"family {family!r} の {shape!r} が存在しないブロックを参照します: {block_id}"
                )
            if block_ids[block_id].get("family") != family:
                raise ValueError(f"family {family!r} とブロック {block_id} の属性が一致しません")
    for block_id, block in block_ids.items():
        for target in block.get("weathering", {}).values():
            if target not in block_ids:
                raise ValueError(f"block {block_id} のweathering先が存在しません: {target}")


def write_checksums(paths: list[Path], output: Path = Path("dist/SHA256SUMS")) -> None:
    """生成したJSON資産のSHA-256一覧を書き出す。"""
    import hashlib

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
            for path in sorted(paths, key=lambda item: item.name)
        ),
        encoding="utf-8",
    )


def write_diff(old_version: str, new_version: str) -> Path:
    """隣接版のブロック追加・削除・状態変更をJSONに記録する。"""
    old = json.loads(Path("dist", f"blockdata-{old_version}.json").read_text(encoding="utf-8"))
    new = json.loads(Path("dist", f"blockdata-{new_version}.json").read_text(encoding="utf-8"))
    old_blocks, new_blocks = old["blocks"], new["blocks"]
    common = old_blocks.keys() & new_blocks.keys()
    changes = {
        "formatVersion": 1,
        "from": old_version,
        "to": new_version,
        "added": sorted(new_blocks.keys() - old_blocks.keys()),
        "removed": sorted(old_blocks.keys() - new_blocks.keys()),
        "changed": {
            key: {
                field: {
                    "from": old_blocks[key].get(field, {}),
                    "to": new_blocks[key].get(field, {}),
                }
                for field in ("properties", "default")
                if old_blocks[key].get(field, {}) != new_blocks[key].get(field, {})
            }
            for key in sorted(common)
            if any(
                old_blocks[key].get(field, {}) != new_blocks[key].get(field, {})
                for field in ("properties", "default")
            )
        },
    }
    path = Path("dist", f"blockdata-diff-{old_version}-{new_version}.json")
    path.write_text(json.dumps(changes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
