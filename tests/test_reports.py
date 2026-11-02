import json

from mcblockdata.reports import convert_blocks


def test_convert_blocks_sorts_and_converts_default(tmp_path):
    path = tmp_path / "blocks.json"
    path.write_text(
        json.dumps(
            {
                "minecraft:z_block": {"states": [{"id": 0, "default": True}]},
                "minecraft:a_block": {
                    "properties": {"powered": ["false", "true"]},
                    "states": [
                        {"id": 0, "properties": {"powered": "false"}, "default": True},
                        {"id": 1, "properties": {"powered": "true"}},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    assert convert_blocks(path) == {
        "minecraft:a_block": {
            "properties": {"powered": ["false", "true"]},
            "default": {"powered": "false"},
        },
        "minecraft:z_block": {"properties": {}, "default": {}},
    }
