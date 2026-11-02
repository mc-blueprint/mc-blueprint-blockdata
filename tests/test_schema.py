import json

from jsonschema import Draft202012Validator

from mcblockdata.generator import SCHEMA_PATH


def test_schema_accepts_classified_data():
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
            "minecraft:stone": {
                "properties": {},
                "default": {},
                "material": "stone",
                "shape": "full",
                "tint": "none",
                "light": [{"when": {}, "emission": 0, "opacity": 15}],
                "render": "model",
            },
            "minecraft:grass_block": {
                "properties": {"snowy": ["true", "false"]},
                "default": {"snowy": "false"},
                "material": "soil",
                "shape": "full",
                "tint": "grass",
                "light": [{"when": {}, "emission": 0, "opacity": 15}],
                "render": "model",
                "faces": {
                    "top": {
                        "oklab": {
                            "L": [0.5, 0.5, 0.5, 0.5, 1.000001735347926],
                            "a": [0.0, 0.0, 0.0, 0.0, 0.0],
                            "b": [0.0, 0.0, 0.0, 0.0, 0.0],
                        }
                    }
                },
            },
        },
        "families": {},
        "tints": {"grass": {}, "foliage": {}, "water": {}},
    }

    Draft202012Validator(schema).validate(data)
