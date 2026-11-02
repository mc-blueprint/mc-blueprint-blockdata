import json
import zipfile
from io import BytesIO

import numpy as np
from PIL import Image

from mcblockdata.colors import _rgb_color, extract_models, extract_tints
from mcblockdata.visuals import FIXED_TINTS, enrich_blocks, read_biomes


def test_visual_attributes_cover_dynamic_lights_tints_and_render():
    blocks = {
        "minecraft:torch": {"shape": "plant", "properties": {}, "default": {}},
        "minecraft:lantern": {"shape": "full", "properties": {}, "default": {}},
        "minecraft:candle": {
            "shape": "plant",
            "properties": {"lit": ["true", "false"], "candles": ["1", "2", "3", "4"]},
            "default": {"lit": "false", "candles": "1"},
        },
        "minecraft:furnace": {
            "shape": "full",
            "properties": {"lit": ["true", "false"]},
            "default": {"lit": "false"},
        },
        "minecraft:glowstone": {"shape": "full", "properties": {}, "default": {}},
        "minecraft:sea_lantern": {"shape": "full", "properties": {}, "default": {}},
        "minecraft:beacon": {"shape": "full", "properties": {}, "default": {}},
        "minecraft:water": {"shape": "fluid", "properties": {}, "default": {}},
        "minecraft:lava": {"shape": "fluid", "properties": {}, "default": {}},
        "minecraft:chest": {"shape": "full", "properties": {}, "default": {}},
        "minecraft:red_bed": {"shape": "full", "properties": {}, "default": {}},
        "minecraft:grass_block": {"shape": "full", "properties": {}, "default": {}},
        "minecraft:oak_leaves": {"shape": "full", "properties": {}, "default": {}},
        "minecraft:glass": {"shape": "full", "properties": {}, "default": {}},
        "minecraft:oak_slab": {
            "shape": "slab",
            "properties": {"type": ["top", "bottom", "double"]},
            "default": {"type": "bottom"},
        },
        "minecraft:trial_spawner": {
            "shape": "full",
            "properties": {"trial_spawner_state": ["inactive", "waiting_for_players", "active"]},
            "default": {"trial_spawner_state": "inactive"},
        },
        "minecraft:vault": {
            "shape": "full",
            "properties": {"vault_state": ["inactive", "active", "unlocking", "ejecting"]},
            "default": {"vault_state": "inactive"},
        },
        "minecraft:oxidized_copper_bulb": {
            "shape": "full",
            "properties": {"lit": ["true", "false"]},
            "default": {"lit": "false"},
        },
    }

    enrich_blocks(blocks)

    assert blocks["minecraft:torch"]["light"][0]["emission"] == 14
    assert blocks["minecraft:lantern"]["light"][0]["emission"] == 15
    candle_rules = blocks["minecraft:candle"]["light"]
    assert {rule["emission"] for rule in candle_rules if rule["when"].get("lit") == "true"} == {
        3,
        6,
        9,
        12,
    }
    furnace = blocks["minecraft:furnace"]["light"]
    assert next(rule["emission"] for rule in furnace if rule["when"] == {"lit": "true"}) == 13
    assert blocks["minecraft:glowstone"]["light"][0]["emission"] == 15
    assert blocks["minecraft:glowstone"]["light"][0]["opacity"] == 15
    assert blocks["minecraft:sea_lantern"]["light"][0]["opacity"] == 15
    assert blocks["minecraft:beacon"]["light"][0]["opacity"] == 0
    assert blocks["minecraft:water"]["light"][0]["opacity"] == 1
    assert blocks["minecraft:oak_leaves"]["light"][0]["opacity"] == 1
    assert blocks["minecraft:glass"]["light"][0]["opacity"] == 0
    assert (
        next(rule["opacity"] for rule in blocks["minecraft:oak_slab"]["light"] if not rule["when"])
        == 0
    )
    assert (
        next(
            rule["opacity"]
            for rule in blocks["minecraft:oak_slab"]["light"]
            if rule["when"].get("type") == "double"
        )
        == 15
    )
    assert blocks["minecraft:chest"]["light"][0]["opacity"] == 0
    trial = blocks["minecraft:trial_spawner"]["light"]
    assert (
        next(
            rule["emission"]
            for rule in trial
            if rule["when"].get("trial_spawner_state") == "active"
        )
        == 8
    )
    vault = blocks["minecraft:vault"]["light"]
    assert (
        next(rule["emission"] for rule in vault if rule["when"].get("vault_state") == "inactive")
        == 6
    )
    bulb = blocks["minecraft:oxidized_copper_bulb"]["light"]
    assert next(rule["emission"] for rule in bulb if rule["when"].get("lit") == "true") == 4
    assert blocks["minecraft:water"]["render"] == "fluid"
    assert blocks["minecraft:lava"]["render"] == "fluid"
    assert blocks["minecraft:chest"]["render"] == blocks["minecraft:red_bed"]["render"] == "entity"
    assert blocks["minecraft:grass_block"]["tint"] == "grass"
    assert blocks["minecraft:oak_leaves"]["tint"] == "foliage"


def test_extract_tints_uses_climate_overrides_and_water_color(tmp_path):
    jar = tmp_path / "client.jar"
    image = Image.fromarray(np.full((256, 256, 3), (40, 120, 60), dtype=np.uint8))
    stream = BytesIO()
    image.save(stream, format="PNG")
    with zipfile.ZipFile(jar, "w") as archive:
        for name in ("grass", "foliage"):
            archive.writestr(f"assets/minecraft/textures/colormap/{name}.png", stream.getvalue())
    biomes = {
        "minecraft:plains": {
            "temperature": 0.8,
            "downfall": 0.4,
            "effects": {"water_color": 0x123456},
        },
        "minecraft:swamp": {
            "temperature": 0.8,
            "downfall": 0.9,
            "effects": {"grass_color_modifier": "swamp", "water_color": 0x654321},
        },
        "minecraft:badlands": {
            "temperature": 2,
            "downfall": 0,
            "effects": {"water_color": 0x123456},
        },
        "minecraft:custom": {
            "temperature": 0.5,
            "downfall": 0.5,
            "effects": {
                "grass_color": "#abcdef",
                "foliage_color": "#112233",
                "water_color": "#abcdef",
            },
        },
        "minecraft:dark_forest": {
            "temperature": 0.7,
            "downfall": 0.8,
            "effects": {"grass_color_modifier": "dark_forest", "water_color": 0x123456},
        },
    }

    colors = extract_tints(jar, biomes)

    assert colors["grass"]["plains"] == colors["foliage"]["plains"]
    assert colors["grass"]["badlands"] != colors["grass"]["plains"]
    assert colors["grass"]["custom"] != colors["grass"]["plains"]
    assert colors["water"]["custom"] != colors["water"]["plains"]


def test_read_biomes_from_bundled_server_jar(tmp_path):
    jar = tmp_path / "server.jar"
    nested = BytesIO()
    with zipfile.ZipFile(nested, "w") as archive:
        archive.writestr(
            "data/minecraft/worldgen/biome/plains.json", json.dumps({"temperature": 0.8})
        )
    with zipfile.ZipFile(jar, "w") as archive:
        archive.writestr("META-INF/versions/1.21.11/server-1.21.11.jar", nested.getvalue())

    assert read_biomes(jar) == {"minecraft:plains": {"temperature": 0.8}}


def test_model_geometry_and_tint_registration_correct_visual_attributes(tmp_path):
    # 自作の最小モデルで継承・面・着色を検証し、Mojangの資産は含めない。
    jar = tmp_path / "client.jar"
    untinted = ("oak_sapling", "azalea_leaves", "red_poplar_leaves", "cherry_leaves")
    plants = ("short_grass", "fern", "golden_dandelion", "bush")
    cubes = ("stone", "tinted_glass", "spruce_leaves", "birch_leaves", *untinted)
    blocks = {
        f"minecraft:{name}": {"properties": {}, "default": {}, "shape": "full",
                             "material": "plant" if name in plants else "stone"}
        for name in (*plants, *cubes, "redstone_wire", "lava_cauldron")
    }
    with zipfile.ZipFile(jar, "w") as archive:
        for name, start, end in (("cube", [0, 0, 0], [16, 16, 16]),
                                 ("cross", [0, 0, 8], [16, 16, 8])):
            archive.writestr(f"assets/minecraft/models/block/test_{name}.json", json.dumps({
                "elements": [{"from": start, "to": end, "faces": {
                    direction: {"texture": "#test", "tintindex": 0}
                    for direction in ("up", "down", "north", "south", "east", "west")
                }}]
            }))
        for block_id in blocks:
            name = block_id.partition(":")[2]
            model = "cube" if name in cubes else "cross"
            archive.writestr(f"assets/minecraft/models/block/{name}.json", json.dumps({
                "parent": f"minecraft:block/test_{model}"
            }))
            archive.writestr(f"assets/minecraft/blockstates/{name}.json", json.dumps({
                "variants": {"": {"model": f"minecraft:block/{name}"}}
            }))
    models = extract_models(jar, blocks)
    # tintindexのある未登録モデルもnone、登録があっても着色面がなければnone。
    models["minecraft:oak_sapling"]["tinted"] = False
    enrich_blocks(blocks, models)
    for name in plants:
        assert blocks[f"minecraft:{name}"]["shape"] == "plant"
        assert blocks[f"minecraft:{name}"]["light"][0]["opacity"] == 0
    for name in untinted:
        assert blocks[f"minecraft:{name}"]["tint"] == "none"
    assert blocks["minecraft:bush"]["tint"] == "grass"
    assert blocks["minecraft:redstone_wire"]["light"][0]["opacity"] == 0
    assert blocks["minecraft:tinted_glass"]["light"][0]["opacity"] == 15
    assert blocks["minecraft:stone"]["light"][0]["opacity"] == 15
    assert blocks["minecraft:lava_cauldron"]["light"][0]["emission"] == 15
    for name in ("spruce_leaves", "birch_leaves"):
        assert blocks[f"minecraft:{name}"]["tint"] == "fixed"
    assert FIXED_TINTS["spruce_leaves"] == 0x619961
    assert FIXED_TINTS["birch_leaves"] == 0x80A755
    assert _rgb_color(FIXED_TINTS["spruce_leaves"]) != _rgb_color(FIXED_TINTS["birch_leaves"])


def test_special_renderers_include_signs_banners_heads_and_shulkers():
    names = ("oak_sign", "oak_wall_hanging_sign", "white_banner", "black_wall_banner",
             "player_head", "zombie_wall_head", "skeleton_skull", "wither_skeleton_wall_skull",
             "shulker_box", "red_shulker_box", "chest", "red_bed")
    blocks = {f"minecraft:{name}": {"shape": "full", "properties": {}} for name in names}
    enrich_blocks(blocks)
    assert all(block["render"] == "entity" for block in blocks.values())
