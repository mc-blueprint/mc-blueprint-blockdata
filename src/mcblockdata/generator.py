"""Minecraft版ごとのblockdataを組み立てる。"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from mcblockdata import __version__
from mcblockdata.colors import extract_faces
from mcblockdata.reports import convert_blocks, read_data_version

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
    if client_jar is not None:
        for block_id, faces in extract_faces(client_jar, blocks).items():
            blocks[block_id]["faces"] = faces
    data = {
        "formatVersion": 1,
        "minecraftVersion": version,
        "dataVersion": read_data_version(server_jar),
        "generator": {"repository": REPOSITORY, "version": __version__, "commit": _commit()},
        "blocks": blocks,
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


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
