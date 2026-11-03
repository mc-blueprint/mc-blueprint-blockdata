import json
from zipfile import ZipFile

from mcblockdata.classification import classify_blocks


def test_classifies_material_shape_family_and_weathering(tmp_path):
    jar = tmp_path / "server.jar"
    blocks = {
        f"minecraft:{name}": {"properties": {}, "default": {}}
        for name in (
            "stone_bricks",
            "stone_brick_stairs",
            "stone_brick_slab",
            "stone_brick_wall",
            "mossy_stone_bricks",
            "mossy_stone_brick_stairs",
            "mossy_stone_brick_slab",
            "mossy_stone_brick_wall",
            "cracked_stone_bricks",
            "oak_planks",
            "oak_stairs",
            "oak_fence_gate",
            "oak_sign",
            "blue_concrete",
            "glass",
            "unknown_block",
            "glowstone",
            "redstone_wire",
            "redstone_lamp",
            "amethyst_block",
            "barrel",
            "bubble_column",
            "black_banner",
            "potted_poppy",
            "calcite",
            "petrified_oak_slab",
            "hay_block",
            "dripstone_block",
            "crimson_nylium",
            "warped_nylium",
            "bone_block",
            "furnace",
            "blast_furnace",
            "smoker",
            "dispenser",
            "dropper",
            "observer",
            "honeycomb_block",
            "honey_block",
            "resin_block",
            "resin_clump",
            "sponge",
            "wet_sponge",
            "slime_block",
            "sculk",
            "sculk_sensor",
            "shulker_box",
            "black_shulker_box",
            "target",
            "tnt",
            "chorus_plant",
            "composter",
            "conduit",
            "creaking_heart",
            "decorated_pot",
            "dried_ghast",
            "ender_chest",
            "fletching_table",
            "grindstone",
            "hopper",
            "lectern",
            "lily_pad",
            "loom",
            "repeater",
            "respawn_anchor",
            "tripwire",
            "vault",
            "calibrated_sculk_sensor",
        )
    }
    concrete_colors = (
        "white",
        "orange",
        "magenta",
        "light_blue",
        "yellow",
        "lime",
        "pink",
        "gray",
        "light_gray",
        "cyan",
        "purple",
        "blue",
        "brown",
        "green",
        "red",
        "black",
    )
    blocks.update(
        {
            f"minecraft:{color}_concrete": {"properties": {}, "default": {}}
            for color in concrete_colors
        }
    )
    with ZipFile(jar, "w") as archive:
        archive.writestr(
            "data/minecraft/tags/block/stone_bricks.json",
            json.dumps({"values": ["minecraft:stone_bricks", "minecraft:stone_brick_stairs"]}),
        )
        archive.writestr(
            "data/minecraft/tags/block/wooden_stairs.json",
            json.dumps({"values": ["#minecraft:wooden_stairs_base"]}),
        )
        archive.writestr(
            "data/minecraft/tags/block/wooden_stairs_base.json",
            json.dumps({"values": ["minecraft:oak_stairs"]}),
        )

    families = classify_blocks(blocks, jar)

    assert blocks["minecraft:stone_bricks"]["material"] == "stone"
    assert blocks["minecraft:stone_bricks"]["subMaterial"] == "brick_pattern"
    assert blocks["minecraft:stone_brick_stairs"]["shape"] == "stairs"
    assert blocks["minecraft:oak_stairs"]["family"] == "oak_planks"
    assert blocks["minecraft:oak_stairs"]["material"] == "wood"
    assert blocks["minecraft:oak_fence_gate"]["material"] == "wood"
    assert blocks["minecraft:oak_sign"]["material"] == "wood"
    assert families["oak_planks"] == {
        "full": "minecraft:oak_planks",
        "stairs": "minecraft:oak_stairs",
        "fence_gate": "minecraft:oak_fence_gate",
        "sign": "minecraft:oak_sign",
    }
    assert blocks["minecraft:stone_bricks"]["weathering"] == {
        "moss": "minecraft:mossy_stone_bricks",
        "crack": "minecraft:cracked_stone_bricks",
    }
    assert blocks["minecraft:stone_brick_stairs"]["weathering"] == {
        "moss": "minecraft:mossy_stone_brick_stairs"
    }
    assert blocks["minecraft:blue_concrete"]["material"] == "concrete"
    assert all(
        blocks[f"minecraft:{color}_concrete"]["material"] == "concrete" for color in concrete_colors
    )
    assert blocks["minecraft:glass"]["material"] == "glass"
    assert blocks["minecraft:unknown_block"]["material"] == "other"
    assert blocks["minecraft:glowstone"]["material"] == "light"
    assert blocks["minecraft:redstone_wire"]["material"] == "mineral"
    assert blocks["minecraft:redstone_lamp"]["material"] == "light"
    assert blocks["minecraft:amethyst_block"]["material"] == "mineral"
    assert blocks["minecraft:barrel"]["material"] == "wood"
    assert blocks["minecraft:bubble_column"]["material"] == "liquid"
    assert blocks["minecraft:black_banner"]["material"] == "wool"
    assert blocks["minecraft:potted_poppy"]["material"] == "plant"
    assert blocks["minecraft:calcite"]["material"] == "stone"
    assert blocks["minecraft:petrified_oak_slab"]["material"] == "wood"
    assert blocks["minecraft:hay_block"]["material"] == "plant"
    assert blocks["minecraft:dripstone_block"]["material"] == "stone"
    assert blocks["minecraft:crimson_nylium"]["material"] == "soil"
    assert blocks["minecraft:warped_nylium"]["material"] == "soil"
    assert blocks["minecraft:bone_block"]["material"] == "mineral"
    for name in ("furnace", "blast_furnace", "smoker", "dispenser", "dropper", "observer"):
        assert blocks[f"minecraft:{name}"]["material"] == "stone"
    for name in (
        "honeycomb_block",
        "honey_block",
        "resin_block",
        "resin_clump",
        "sponge",
        "wet_sponge",
        "slime_block",
        "target",
    ):
        assert blocks[f"minecraft:{name}"]["material"] == "plant"
    assert blocks["minecraft:sculk"]["material"] == "mineral"
    assert blocks["minecraft:sculk_sensor"]["material"] == "mineral"
    assert blocks["minecraft:shulker_box"]["material"] == "mineral"
    assert blocks["minecraft:black_shulker_box"]["material"] == "mineral"
    assert blocks["minecraft:tnt"]["material"] == "mineral"
    assert blocks["minecraft:chorus_plant"]["material"] == "plant"
    assert blocks["minecraft:composter"]["material"] == "wood"
    assert blocks["minecraft:conduit"]["material"] == "mineral"
    assert blocks["minecraft:creaking_heart"]["material"] == "wood"
    assert blocks["minecraft:decorated_pot"]["material"] == "terracotta"
    assert blocks["minecraft:dried_ghast"]["material"] == "plant"
    assert blocks["minecraft:ender_chest"]["material"] == "stone"
    assert blocks["minecraft:fletching_table"]["material"] == "wood"
    assert blocks["minecraft:grindstone"]["material"] == "stone"
    assert blocks["minecraft:hopper"]["material"] == "metal"
    assert blocks["minecraft:lectern"]["material"] == "wood"
    assert blocks["minecraft:lily_pad"]["material"] == "plant"
    assert blocks["minecraft:loom"]["material"] == "wood"
    assert blocks["minecraft:repeater"]["material"] == "stone"
    assert blocks["minecraft:respawn_anchor"]["material"] == "stone"
    assert blocks["minecraft:tripwire"]["material"] == "plant"
    assert blocks["minecraft:vault"]["material"] == "stone"
    assert blocks["minecraft:calibrated_sculk_sensor"]["material"] == "mineral"
    assert all(block["material"] and block["shape"] for block in blocks.values())


def test_families_materials_and_existing_weathering_targets(tmp_path):
    jar = tmp_path / "server.jar"
    with ZipFile(jar, "w"):
        pass

    names = ["white_carpet", "stone_bricks"]
    for base in ("quartz", "purpur", "sandstone", "red_sandstone"):
        names.extend([base if "sandstone" in base else base + "_block",
                      base + "_stairs", base + "_slab"])
    cracked = ("nether_bricks", "deepslate_bricks", "deepslate_tiles",
               "polished_blackstone_bricks")
    for name in cracked:
        names.extend([name, "cracked_" + name])
    blocks = {f"minecraft:{name}": {"properties": {}, "default": {}} for name in names}
    families = classify_blocks(blocks, jar)
    assert "family" not in blocks["minecraft:white_carpet"]
    assert "weathering" not in blocks["minecraft:stone_bricks"]
    for base in ("quartz", "purpur", "sandstone", "red_sandstone"):
        key = base if "sandstone" in base else base + "_block"
        assert set(families[key]) == {"full", "stairs", "slab"}
        materials = {blocks[block_id]["material"] for block_id in families[key].values()}
        assert materials == ({"mineral"} if base == "quartz" else {"stone"})
    for name in cracked:
        assert blocks[f"minecraft:{name}"]["weathering"] == {
            "crack": f"minecraft:cracked_{name}"
        }
