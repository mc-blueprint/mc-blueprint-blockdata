import json

from jsonschema import Draft202012Validator

from mcblockdata.generator import SCHEMA_PATH


def test_schema_accepts_base_data_and_optional_followup_attributes():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    data = {
        "formatVersion": 1,
        "minecraftVersion": "1.21.11",
        "dataVersion": 4671,
        "generator": {
            "repository": "mc-blueprint/mc-blueprint-blockdata",
            "version": "0.1.0",
            "commit": "abc123",
        },
        "blocks": {
            "minecraft:stone": {"properties": {}, "default": {}},
            "minecraft:grass_block": {
                "properties": {"snowy": ["true", "false"]},
                "default": {"snowy": "false"},
                "tint": "grass",
                "faces": {
                    "top": {
                        "oklab": {
                            "L": [0.5, 0.5, 0.5, 0.5, 0.5],
                            "a": [0.0, 0.0, 0.0, 0.0, 0.0],
                            "b": [0.0, 0.0, 0.0, 0.0, 0.0],
                        }
                    }
                },
            },
        },
    }

    Draft202012Validator(schema).validate(data)
