"""mcblockdata CLI。"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from mcblockdata.generator import build_version, write_checksums, write_diff
from mcblockdata.jars import download_client_jar, download_server_jar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mcblockdata")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Minecraft版のblockdataを生成する")
    versions = build.add_mutually_exclusive_group(required=True)
    versions.add_argument("--version", help="Minecraft版、例: 1.21.11")
    versions.add_argument("--all", action="store_true", help="対応する全4版を生成")
    source = build.add_mutually_exclusive_group()
    source.add_argument("--server-jar", type=Path, help="既存のserver jar")
    source.add_argument("--download", action="store_true", help="公式server jarを取得")
    client = build.add_mutually_exclusive_group()
    client.add_argument("--client-jar", type=Path, help="既存のclient jar（面色抽出用）")
    client.add_argument("--download-client", action="store_true", help="公式client jarを取得")
    build.add_argument("--java", default="java", help="data generatorを実行するJava")
    build.add_argument(
        "--java-for",
        action="append",
        default=[],
        metavar="版=PATH",
        help="--allで版ごとのJavaを指定（複数指定可）",
    )
    args = parser.parse_args(argv)

    try:
        if args.all:
            if args.server_jar or args.client_jar:
                raise ValueError("--allでは版ごとのjar指定は使えません。公式jarを取得します")
            supported = ["1.21.11", "26.1.2", "26.2", "26.3"]
            java_by_version = {}
            for spec in args.java_for:
                version, separator, executable = spec.partition("=")
                if not separator or version not in supported or not executable:
                    raise ValueError(f"不正な--java-for指定です: {spec!r}（版=PATH）")
                java_by_version[version] = executable
            generated = {}
            for version in supported:
                jar = download_server_jar(version)
                client_jar = download_client_jar(version)
                generated[version] = build_version(
                    version, jar, java_by_version.get(version, args.java), client_jar
                )
            for old, new in zip(supported, supported[1:], strict=False):
                write_diff(old, new)
            assets = [Path("dist") / f"blockdata-{version}.json" for version in supported]
            assets.extend(Path("dist").glob("blockdata-diff-*.json"))
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            ).stdout.strip()
            commit_file = Path("dist/generator.commit")
            commit_file.write_text(f"{commit}\n", encoding="utf-8")
            assets.append(commit_file)
            write_checksums(assets)
            for version, data in generated.items():
                print(
                    f"dist/blockdata-{version}.json を生成しました"
                    f"（{len(data['blocks'])} blocks）"
                )
        else:
            if args.java_for:
                raise ValueError("--java-forは--allと併用してください")
            if not args.server_jar and not args.download:
                raise ValueError("--versionでは--server-jarまたは--downloadを指定してください")
            jar = args.server_jar or download_server_jar(args.version)
            client_jar = args.client_jar or (
                download_client_jar(args.version) if args.download_client else None
            )
            data = build_version(args.version, jar, args.java, client_jar)
            print(
                f"dist/blockdata-{args.version}.json を生成しました"
                f"（{len(data['blocks'])} blocks）"
            )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
