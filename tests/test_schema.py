import json

import pytest
from jsonschema import Draft202012Validator

from mcblockdata.generator import SCHEMA_PATH, validate


@pytest.fixture
def data():
    return {
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

def test_schema_accepts_classified_data(data):
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(data)
    validate(data)


@pytest.mark.parametrize("problem", ["family", "weathering", "light", "empty", "fallback", "fixed"])
def test_rejects_invalid_references_and_light_conditions(data, problem):
    block = data["blocks"]["minecraft:stone"]
    if problem == "family":
        block["family"] = "absent"
    elif problem == "weathering":
        block["weathering"] = {"crack": "minecraft:absent"}
    elif problem == "light":
        block["light"].insert(0, {"when": {"lit": "true"}, "emission": 1, "opacity": 0})
    elif problem == "empty":
        block["light"] = []
    elif problem == "fallback":
        block["properties"] = {"lit": ["true", "false"]}
        block["light"][0]["when"] = {"lit": "true"}
    else:
        block["tint"] = "fixed"
    with pytest.raises(ValueError):
        validate(data)


def test_fixed_colors_are_optional_but_required_for_fixed_blocks(data):
    data["blocks"]["minecraft:stone"]["tint"] = "fixed"
    data["tints"]["fixed"] = {"minecraft:stone": [0.6, -0.1, 0.1]}
    validate(data)
    data["tints"]["fixed"]["minecraft:stone"] = [0.6, 0.1]
    with pytest.raises(ValueError):
        validate(data)
