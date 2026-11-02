"""モデルから得た特徴と、光・着色・描画方式の補完規則。"""

from __future__ import annotations

import json
from pathlib import Path

from mcblockdata.jars import read_server_entries

# 根拠: minecraft.wiki/w/Light, /Opacity, /Sea_Pickle, /Candle, /Copper_Bulb,
# /Trial_Spawner, /Vault。
EMISSION = {
    "torch": 14,
    "wall_torch": 14,
    "redstone_torch": 7,
    "redstone_wall_torch": 7,
    "soul_torch": 10,
    "soul_wall_torch": 10,
    "lantern": 15,
    "soul_lantern": 10,
    "end_rod": 14,
    "glowstone": 15,
    "sea_lantern": 15,
    "shroomlight": 15,
    "jack_o_lantern": 15,
    "ochre_froglight": 15,
    "verdant_froglight": 15,
    "pearlescent_froglight": 15,
    "lava": 15,
    "lava_cauldron": 15,  # 根拠: https://minecraft.wiki/w/Cauldron#Lava
    "fire": 15,
    "soul_fire": 10,
    "campfire": 15,
    "soul_campfire": 10,
    "beacon": 15,
    "conduit": 15,
    "end_portal": 15,
    "end_gateway": 15,
    "nether_portal": 11,
    "magma_block": 3,
    "crying_obsidian": 10,
    "glow_lichen": 7,
    "redstone_ore": 9,
    "deepslate_redstone_ore": 9,
    "enchanting_table": 7,
    "brown_mushroom": 1,
    "brewing_stand": 1,
    "dragon_egg": 1,
    "end_portal_frame": 1,
    "sculk_sensor": 1,
    "calibrated_sculk_sensor": 1,
    "firefly_bush": 2,
    "candle_cake": 3,
    "white_candle_cake": 3,
    "orange_candle_cake": 3,
    "magenta_candle_cake": 3,
    "light_blue_candle_cake": 3,
    "yellow_candle_cake": 3,
    "lime_candle_cake": 3,
    "pink_candle_cake": 3,
    "gray_candle_cake": 3,
    "light_gray_candle_cake": 3,
    "cyan_candle_cake": 3,
    "purple_candle_cake": 3,
    "blue_candle_cake": 3,
    "brown_candle_cake": 3,
    "green_candle_cake": 3,
    "red_candle_cake": 3,
    "black_candle_cake": 3,
    "vault": 6,
    "trial_spawner": 0,
    "copper_bulb": 15,
    "exposed_copper_bulb": 12,
    "weathered_copper_bulb": 8,
    "oxidized_copper_bulb": 4,
    "waxed_copper_bulb": 15,
    "waxed_exposed_copper_bulb": 12,
    "waxed_weathered_copper_bulb": 8,
    "waxed_oxidized_copper_bulb": 4,
    "lightning_rod": 0,
    "frogspawn": 0,
    "small_amethyst_bud": 1,
    "medium_amethyst_bud": 2,
    "large_amethyst_bud": 4,
    "amethyst_cluster": 5,
    "sculk_catalyst": 6,
}

# Wiki「Light」: 不透過の立方体は15、ガラス/カーペットは0、葉/水/通常の氷は1。
# packed_ice・blue_iceは不透過: minecraft.wiki/w/Packed_Ice, /Blue_Ice。
# 半ブロック・階段などはfull cubeでなく追加遮光しないため0とする。
ZERO_OPACITY = {
    "air",
    "cave_air",
    "void_air",
    "glass",
    "glass_pane",
    "iron_bars",
    "chain",
    "carpet",
    "snow",
    "powder_snow",  # 根拠: minecraft.wiki/w/Powder_Snow （モデルは立方体だが透光）。
    "torch",
    "wall_torch",
    "redstone_torch",
    "redstone_wall_torch",
    "soul_torch",
    "soul_wall_torch",
    "lantern",
    "soul_lantern",
    "end_rod",
    "beacon",
    "campfire",
    "soul_campfire",
    "glow_lichen",
    "vine",
    "ladder",
    "scaffolding",
    "cobweb",
    "slime_block",
    "honey_block",
    "chest",
    "trapped_chest",
    "ender_chest",
    "candle",
    "sea_pickle",
    "vault",
    "trial_spawner",
    "oak_bed",
    "red_bed",
    "ice",
    "frosted_ice",
    "water",
    "bubble_column",
    "fire",
    "soul_fire",
    "nether_portal",
    "end_portal",
    "end_gateway",
    "barrier",
    "structure_void",
    "light",
}

FLUIDS = {"water", "bubble_column", "lava"}
TINT_GRASS = {
    "grass_block",
    "short_grass",
    "tall_grass",
    "fern",
    "large_fern",
    "sugar_cane",
    "pink_petals",
    "wildflowers",
    "bush",
    "potted_fern",
}
# 根拠: https://minecraft.wiki/w/Biome#Tint （tintindexだけでは色の登録は分からない）。
TINT_FOLIAGE = {
    "vine", "oak_leaves", "jungle_leaves", "acacia_leaves", "dark_oak_leaves", "mangrove_leaves"
}
# 根拠: https://minecraft.wiki/w/Biome#Other_foliage と /Lily_Pad#Appearance。
FIXED_TINTS = {"spruce_leaves": 0x619961, "birch_leaves": 0x80A755, "lily_pad": 0x208030}


def enrich_blocks(blocks: dict[str, dict], models: dict[str, dict] | None = None) -> None:
    """光・着色・描画を追加し、モデルがある場合は形状と遮光も補正する。"""
    for block_id, block in blocks.items():
        name = block_id.partition(":")[2]
        model = models.get(block_id) if models is not None else None
        if model and model["cross"] and block["material"] == "plant":
            block["shape"] = "plant"
        default_emission = 0 if "lit" in block.get("properties", {}) else EMISSION.get(name, 0)
        opacity = _opacity(name, block["shape"], model)
        rules = [{"when": {}, "emission": default_emission, "opacity": opacity}]
        rules.extend(_state_light(name, block.get("properties", {}), opacity, block["shape"]))
        block["light"] = list(reversed(rules[1:])) + rules[:1]
        block["tint"] = (
            _tint(name) if model is None or model["tinted"] or name in FLUIDS else "none"
        )
        block["render"] = (
            "fluid"
            if name in FLUIDS
            else "entity"
            if _is_entity(name)
            else "invisible"
            if name in {"air", "cave_air", "void_air", "barrier", "structure_void", "light"}
            else "model"
        )


def _opacity(name: str, shape: str, model: dict | None = None) -> int:
    if name == "tinted_glass":
        return 15
    if name.endswith("_chest"):
        return 0
    if name.endswith(("_candle", "_candle_cake", "_bed")):
        return 0
    if "glass" in name:
        return 0
    if name in {
        "water",
        "bubble_column",
        "lava",
        "ice",
        "frosted_ice",
        "slime_block",
        "honey_block",
        "cobweb",
        "mangrove_roots",  # 根拠: minecraft.wiki/w/Mangrove_Roots （Java版は遮光1）。
    }:
        return 1
    if name.endswith("_leaves"):
        return 1
    if name in ZERO_OPACITY or shape != "full":
        return 0
    if model is not None and not model["fullCube"]:
        return 0
    return 15


def _state_light(name: str, properties: dict, opacity: int, shape: str) -> list[dict]:
    result = []
    if "lit" in properties and not {"candles", "pickles"} & properties.keys():
        level = EMISSION.get(name, 13 if name in {"furnace", "blast_furnace", "smoker"} else 15)
        result.append({"when": {"lit": "true"}, "emission": level, "opacity": opacity})
    if "candles" in properties:
        result.extend(
            {
                "when": {"candles": str(count), "lit": "true"},
                "emission": min(15, count * 3),
                "opacity": opacity,
            }
            for count in range(4, 0, -1)
        )
        result.append({"when": {"lit": "false"}, "emission": 0, "opacity": opacity})
    if "pickles" in properties:
        result.extend(
            {
                "when": {"pickles": str(count), "waterlogged": "true"},
                "emission": 3 + count * 3,
                "opacity": opacity,
            }
            for count in range(4, 0, -1)
        )
        result.append({"when": {"waterlogged": "false"}, "emission": 0, "opacity": opacity})
    if "charges" in properties:
        result.extend(
            {"when": {"charges": str(count)}, "emission": count * 4 - 1, "opacity": opacity}
            for count in range(4, 0, -1)
        )
        result.append({"when": {"charges": "0"}, "emission": 0, "opacity": opacity})
    if "berries" in properties:
        result.append({"when": {"berries": "true"}, "emission": 14, "opacity": opacity})
    if "level" in properties and name == "light":
        result.extend(
            {"when": {"level": str(level)}, "emission": level, "opacity": 0}
            for level in range(15, -1, -1)
        )
    if "vault_state" in properties:
        result.extend(
            {
                "when": {"vault_state": state},
                "emission": 6 if state == "inactive" else 12,
                "opacity": opacity,
            }
            for state in ("inactive", "active", "unlocking", "ejecting")
        )
    if "trial_spawner_state" in properties:
        result.extend(
            {"when": {"trial_spawner_state": state}, "emission": level, "opacity": opacity}
            for state, level in (
                ("inactive", 0),
                ("waiting_for_players", 4),
                ("active", 8),
                ("waiting_for_reward_ejection", 0),
                ("ejecting_reward", 0),
                ("cooldown", 0),
            )
        )
    if shape == "slab":
        result.insert(0, {"when": {"type": "double"}, "emission": 0, "opacity": 15})
    return [
        rule for rule in result
        if all(value in properties.get(key, []) for key, value in rule["when"].items())
    ]


def _tint(name: str) -> str:
    if name == "water" or name == "bubble_column" or name == "water_cauldron":
        return "water"
    if name in TINT_GRASS:
        return "grass"
    if name in FIXED_TINTS:
        return "fixed"
    if name in TINT_FOLIAGE:
        return "foliage"
    return "none"


def _is_entity(name: str) -> bool:
    # 根拠: https://minecraft.wiki/w/Block_entity （専用レンダラーを使うもの）。
    return name.endswith((
        "_chest", "_bed", "_sign", "_banner", "_head", "_skull", "_shulker_box"
    )) or name in {
        "chest", "shulker_box", "bell", "conduit", "decorated_pot", "enchanting_table"
    }


def read_biomes(server_jar: Path) -> dict[str, dict]:
    """server jar内のworldgen biome定義を読む。"""
    prefix = "data/minecraft/worldgen/biome/"
    result = {}
    for path, content in read_server_entries(server_jar, prefix).items():
        if path.endswith(".json"):
            result[f"minecraft:{Path(path).stem}"] = json.loads(content)
    return result
