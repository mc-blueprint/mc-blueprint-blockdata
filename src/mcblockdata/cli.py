"""mcblockdata CLI。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mcblockdata.generator import build_version
from mcblockdata.jars import download_server_jar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mcblockdata")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Minecraft版のblockdataを生成する")
    build.add_argument("--version", required=True, help="Minecraft版、例: 1.21.11")
    source = build.add_mutually_exclusive_group(required=True)
    source.add_argument("--server-jar", type=Path, help="既存のserver jar")
    source.add_argument("--download", action="store_true", help="公式server jarを取得")
    build.add_argument("--java", default="java", help="data generatorを実行するJava")
    args = parser.parse_args(argv)

    try:
        jar = args.server_jar or download_server_jar(args.version)
        data = build_version(args.version, jar, args.java)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    print(f"dist/blockdata-{args.version}.json を生成しました（{len(data['blocks'])} blocks）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
