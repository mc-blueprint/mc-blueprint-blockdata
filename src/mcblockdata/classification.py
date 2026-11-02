"""ブロックIDとserver jarのタグから材質・形状・ファミリーを分類する。"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from zipfile import ZipFile

MATERIALS = (
    "stone",
    "brick",
    "wood",
    "plaster",
    "terracotta",
    "concrete",
    "metal",
    "glass",
    "soil",
    "sand",
    "plant",
    "wool",
    "ice_snow",
    "ore",
    "mineral",
    "light",
    "liquid",
    "other",
)
SHAPES = (
    "full",
    "stairs",
    "slab",
    "wall",
    "fence",
    "fence_gate",
    "pane",
    "door",
    "trapdoor",
    "button",
    "pressure_plate",
    "sign",
    "hanging_sign",
    "carpet",
    "rail",
    "plant",
    "fluid",
)
VARIANTS = (
    ("_hanging_sign", "hanging_sign"),
    ("_pressure_plate", "pressure_plate"),
    ("_fence_gate", "fence_gate"),
    ("_trapdoor", "trapdoor"),
    ("_stairs", "stairs"),
    ("_slab", "slab"),
    ("_wall", "wall"),
    ("_fence", "fence"),
    ("_pane", "pane"),
    ("_door", "door"),
    ("_button", "button"),
    ("_sign", "sign"),
    ("_carpet", "carpet"),
)
WEATHERING = {
    "stone_bricks": {"moss": "mossy_stone_bricks", "crack": "cracked_stone_bricks"},
    "stone_brick_stairs": {"moss": "mossy_stone_brick_stairs"},
    "stone_brick_slab": {"moss": "mossy_stone_brick_slab"},
    "stone_brick_wall": {"moss": "mossy_stone_brick_wall"},
    "cobblestone": {"moss": "mossy_cobblestone"},
    "cobblestone_stairs": {"moss": "mossy_cobblestone_stairs"},
    "cobblestone_slab": {"moss": "mossy_cobblestone_slab"},
    "cobblestone_wall": {"moss": "mossy_cobblestone_wall"},
}


def classify_blocks(blocks: dict, server_jar) -> dict:
    """分類属性を付加し、形状別ファミリーを返す。"""
    tags = _read_block_tags(server_jar)
    tagged = defaultdict(set)
    for tag, block_ids in tags.items():
        for block_id in block_ids:
            tagged[block_id].add(tag)

    families = defaultdict(dict)
    family_bases = {}
    for block_id, block in blocks.items():
        path = block_id.partition(":")[2]
        shape, base = _shape_and_base(path)
        material = _material(path, tagged[block_id])
        block.update(material=material, shape=shape)
        sub_material = _sub_material(path)
        if sub_material:
            block["subMaterial"] = sub_material
        for suffix, _ in VARIANTS:
            if path.endswith(suffix):
                namespace = block_id.partition(":")[0]
                full_id = next(
                    (
                        f"{namespace}:{candidate}"
                        for candidate in _full_candidates(base)
                        if f"{namespace}:{candidate}" in blocks
                    ),
                    None,
                )
                family_name = full_id.partition(":")[2] if full_id else base
                family_id = family_name
                block["family"] = family_name
                families[family_id][shape] = block_id
                family_bases[family_id] = full_id
                break
        weathering = _weathering(path, blocks)
        if weathering:
            block["weathering"] = weathering

    # family keyにした基本ブロックをfull形状として登録する。
    for family_id, family in families.items():
        full_id = family_bases[family_id]
        if full_id and full_id in blocks:
            family.setdefault("full", full_id)
        for _, block_id in family.items():
            blocks[block_id]["family"] = family_id
    return {key: value for key, value in sorted(families.items()) if len(value) > 1}


def _shape_and_base(path: str) -> tuple[str, str]:
    if path in {"water", "lava"}:
        return "fluid", path
    if path.endswith(("_leaves", "_sapling", "_flower", "_tulip", "_orchid", "_mushroom")):
        return "plant", path
    for suffix, shape in VARIANTS:
        if path.endswith(suffix):
            return shape, path[: -len(suffix)]
    if path.endswith("_rail") or path == "rail":
        return "rail", path.removesuffix("_rail")
    return "full", path


def _full_candidates(base: str) -> tuple[str, ...]:
    return (base, f"{base}s", f"{base}_planks")


def _material(path: str, tags: set[str]) -> str:
    tag_names = {tag.removeprefix("minecraft:") for tag in tags}
    tag_text = " ".join(tag_names)
    if path in {"crimson_nylium", "warped_nylium", "soul_soil"}:
        return "soil"
    if path in {
        "furnace",
        "blast_furnace",
        "smoker",
        "dispenser",
        "dropper",
        "observer",
        "bone_block",
        "tnt",
    }:
        return "mineral" if path in {"bone_block", "tnt"} else "stone"
    if path == "petrified_oak_slab":
        return "wood"
    if path in {
        "hay_block",
        "honey_block",
        "honeycomb_block",
        "resin_block",
        "resin_clump",
        "sponge",
        "wet_sponge",
        "slime_block",
        "target",
    }:
        return "plant"
    if path in {
        "chorus_plant",
        "dried_ghast",
        "lily_pad",
        "sniffer_egg",
        "tripwire",
        "cobweb",
    }:
        return "plant"
    if path in {"composter", "creaking_heart", "fletching_table", "lectern", "loom"}:
        return "wood"
    if path in {
        "comparator",
        "ender_chest",
        "enchanting_table",
        "grindstone",
        "repeater",
        "respawn_anchor",
        "vault",
    }:
        return "stone"
    if path in {"conduit", "calibrated_sculk_sensor"}:
        return "mineral"
    if path in {"decorated_pot"}:
        return "terracotta"
    if path == "hopper":
        return "metal"
    if path.startswith("sculk") or path.endswith("_shulker_box") or path == "shulker_box":
        return "mineral"
    if path in {"water", "lava", "bubble_column", "water_cauldron"} or "fluids" in tag_text:
        return "liquid"
    if path.endswith(("_banner", "_wall_banner", "_bed")):
        return "wool"
    if path.startswith("potted_"):
        return "plant"
    wood_species = (
        "oak",
        "spruce",
        "birch",
        "jungle",
        "acacia",
        "dark_oak",
        "mangrove",
        "cherry",
        "pale_oak",
        "crimson",
        "warped",
        "bamboo",
    )
    wood_parts = (
        "_planks",
        "_log",
        "_wood",
        "_stem",
        "_hyphae",
        "_stairs",
        "_slab",
        "_fence",
        "_button",
        "_door",
        "_trapdoor",
        "_pressure_plate",
        "_sign",
        "_shelf",
    )
    if path.startswith(tuple(f"{species}_" for species in wood_species)) and any(
        part in path for part in wood_parts
    ):
        return "wood"
    if any(tag.startswith("wooden_") for tag in tag_names) or tag_names & {
        "logs",
        "planks",
        "wooden_blocks",
        "bamboo_blocks",
    }:
        return "wood"
    if path in {
        "barrel",
        "bee_nest",
        "beehive",
        "bookshelf",
        "chest",
        "chiseled_bookshelf",
        "cartography_table",
        "crafting_table",
        "jukebox",
        "ladder",
        "note_block",
        "scaffolding",
        "trapped_chest",
    }:
        return "wood"
    if tag_names & {
        "flowers",
        "small_flowers",
        "tall_flowers",
        "saplings",
        "leaves",
        "crops",
        "underwater_bonemeals",
        "wart_blocks",
        "corals",
    }:
        return "plant"
    if "wool" in path or "wool" in tag_text or "carpets" in tag_text:
        return "wool"
    if any(word in path for word in ("glass", "pane")) or "glass" in tag_text:
        return "glass"
    if any(word in path for word in ("ice", "snow", "powder_snow")):
        return "ice_snow"
    if (
        path.endswith("_ore")
        or path.startswith("ore_")
        or "raw_" in path
        or "ancient_debris" in path
    ):
        return "ore"
    if any(word in path for word in ("copper", "iron", "gold", "netherite", "anvil", "chain")):
        return "metal"
    if path in {
        "bell",
        "cauldron",
        "heavy_weighted_pressure_plate",
        "rail",
        "activator_rail",
        "detector_rail",
        "powered_rail",
    }:
        return "metal"
    if any(word in path for word in ("concrete",)):
        return "concrete"
    if any(word in path for word in ("terracotta",)):
        return "terracotta"
    if any(
        word in path
        for word in (
            "torch",
            "lantern",
            "light",
            "candle",
            "glowstone",
            "sea_lantern",
            "shroomlight",
            "redstone_lamp",
        )
    ):
        return "light"
    if path in {"beacon", "campfire", "end_rod", "fire", "soul_campfire", "soul_fire"}:
        return "light"
    if any(
        word in path
        for word in (
            "amethyst",
            "diamond_block",
            "emerald_block",
            "lapis_block",
            "coal_block",
            "quartz_block",
            "redstone_block",
            "redstone_wire",
        )
    ):
        return "mineral"
    if any(
        path == word
        or path.startswith(f"{word}_")
        or path.endswith(f"_{word}")
        or f"_{word}_" in path
        for word in (
            "stone",
            "cobblestone",
            "cobble",
            "deepslate",
            "tuff",
            "basalt",
            "granite",
            "diorite",
            "andesite",
            "blackstone",
            "netherrack",
            "end_stone",
            "prismarine",
            "obsidian",
            "purpur",
            "quartz",
            "calcite",
            "dripstone",
            "lodestone",
            "heavy_core",
            "magma_block",
            "stonecutter",
        )
    ):
        return "stone"
    if any(word in path for word in ("bricks", "brick", "tiles")):
        return "brick"
    if any(word in path for word in ("log", "wood", "planks", "stem", "hyphae", "bamboo")):
        return "wood"
    if (
        any(
            word in path
            for word in ("dirt", "grass_block", "mud", "podzol", "mycelium", "farmland")
        )
        or path == "soul_soil"
    ):
        return "soil"
    if any(word in path for word in ("sand", "gravel", "clay")):
        return "sand"
    if any(
        word in path
        for word in (
            "flower",
            "leaves",
            "sapling",
            "grass",
            "fern",
            "vine",
            "moss",
            "azalea",
            "seagrass",
            "coral",
            "fungus",
            "mushroom",
            "roots",
            "cactus",
            "bush",
            "kelp",
            "dripleaf",
            "sprouts",
            "pickle",
            "lichen",
            "pumpkin",
            "melon",
            "wart",
            "berry",
            "cocoa",
            "carrots",
            "potatoes",
            "wheat",
            "sugar_cane",
        )
    ):
        return "plant"
    return "other"


def _sub_material(path: str) -> str | None:
    if "stone_brick" in path:
        return "brick_pattern"
    if path.endswith(("_planks", "_log", "_wood", "_stem", "_hyphae")):
        return path.rsplit("_", 1)[-1]
    return None


def _weathering(path: str, blocks: dict) -> dict[str, str]:
    rules = WEATHERING.get(path, {})
    result = {}
    for kind, target in rules.items():
        block_id = f"minecraft:{target}"
        if block_id not in blocks:
            raise ValueError(f"weathering規則 {path!r} の参照先が存在しません: {block_id}")
        result[kind] = block_id
    if "moss" not in result and path.startswith("stone_brick"):
        target = f"minecraft:mossy_{path}"
        if target in blocks:
            result["moss"] = target
    if "crack" not in result and path.startswith("stone_brick"):
        target = f"minecraft:cracked_{path}"
        if target in blocks:
            result["crack"] = target
    return result


def _read_block_tags(server_jar) -> dict[str, set[str]]:
    """server jar（bundlerを含む）からminecraftのblock tagを読み取る。"""
    from pathlib import Path

    raw_tags = {}
    with ZipFile(Path(server_jar)) as outer:
        nested_name = next(
            (
                name
                for name in outer.namelist()
                if name.startswith("META-INF/versions/") and name.endswith(".jar")
            ),
            None,
        )
        if nested_name:
            import io

            jar = ZipFile(io.BytesIO(outer.read(nested_name)))
        else:
            jar = outer
        with jar:
            for name in jar.namelist():
                match = re.fullmatch(r"data/minecraft/tags/block/(.+)\.json", name)
                if not match:
                    continue
                contents = json.loads(jar.read(name))
                raw_tags[f"minecraft:{match.group(1)}"] = contents.get("values", [])

    resolved = {}

    def resolve(tag: str, active: frozenset[str] = frozenset()) -> set[str]:
        if tag in resolved:
            return resolved[tag]
        if tag in active:
            return set()
        blocks = set()
        for entry in raw_tags.get(tag, []):
            value = entry.get("id") if isinstance(entry, dict) else entry
            if not isinstance(value, str):
                continue
            if value.startswith("#"):
                nested_tag = value[1:]
                if ":" not in nested_tag:
                    nested_tag = f"minecraft:{nested_tag}"
                blocks.update(resolve(nested_tag, active | {tag}))
            else:
                blocks.add(value if ":" in value else f"minecraft:{value}")
        resolved[tag] = blocks
        return blocks

    return {tag: resolve(tag) for tag in raw_tags}
