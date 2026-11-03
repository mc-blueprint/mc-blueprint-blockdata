import json
import zipfile
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from mcblockdata.colors import _cube_faces, _rgb_color, extract_faces, extract_models
from mcblockdata.visuals import enrich_blocks


def test_extract_faces_reads_inherited_model_and_ignores_transparent_pixels(tmp_path):
    jar = tmp_path / "client.zip"
    with zipfile.ZipFile(jar, "w") as archive:
        archive.writestr(
            "assets/minecraft/blockstates/test.json",
            json.dumps({"variants": {"": {"model": "minecraft:block/test"}}}),
        )
        archive.writestr(
            "assets/minecraft/models/block/test.json",
            json.dumps({"parent": "minecraft:block/parent"}),
        )
        archive.writestr(
            "assets/minecraft/models/block/parent.json",
            json.dumps({
                "textures": {"all": "minecraft:block/test"},
                "elements": [{"faces": {
                    "up": {"texture": "#all"},
                    "north": {"texture": "#all", "cullface": "down"},
                }}],
            }),
        )
        image = Image.new("RGBA", (2, 1))
        image.putpixel((0, 0), (255, 0, 0, 255))
        image.putpixel((1, 0), (0, 0, 255, 0))
        stream = BytesIO()
        image.save(stream, format="PNG")
        archive.writestr("assets/minecraft/textures/block/test.png", stream.getvalue())

    result = extract_faces(jar, {"minecraft:test": {"default": {}}})

    assert set(result["minecraft:test"]) == {"top", "bottom"}
    assert result["minecraft:test"]["top"]["oklab"] == result["minecraft:test"]["bottom"]["oklab"]
    assert len(result["minecraft:test"]["top"]["oklab"]["L"]) == 5


def test_extract_faces_omits_blocks_without_opaque_textures(tmp_path):
    jar = tmp_path / "client.zip"
    with zipfile.ZipFile(jar, "w") as archive:
        archive.writestr(
            "assets/minecraft/blockstates/empty.json",
            json.dumps({"variants": {"": {"model": "minecraft:block/empty"}}}),
        )
        archive.writestr(
            "assets/minecraft/models/block/empty.json",
            json.dumps({"textures": {"all": "minecraft:block/empty"}, "elements": [{
                "faces": {"up": {"texture": "#all"}}
            }]}),
        )
        image = Image.new("RGBA", (1, 1), (255, 0, 0, 0))
        stream = BytesIO()
        image.save(stream, format="PNG")
        archive.writestr("assets/minecraft/textures/block/empty.png", stream.getvalue())

    assert extract_faces(jar, {"minecraft:empty": {"default": {}}}) == {}


def test_extract_faces_separates_tinted_and_plain_layers(tmp_path):
    jar = tmp_path / "client.zip"
    with zipfile.ZipFile(jar, "w") as archive:
        archive.writestr("assets/minecraft/blockstates/test.json", json.dumps({
            "variants": {"": {"model": "minecraft:block/test"}}
        }))
        archive.writestr("assets/minecraft/models/block/test.json", json.dumps({
            "textures": {"plain": "minecraft:block/plain", "overlay": "minecraft:block/overlay"},
            "elements": [{"faces": {
                "north": {"texture": "#plain", "tintindex": -1},
                "down": {"texture": "#plain"},
            }}, {"faces": {
                "north": {"texture": "#overlay", "tintindex": 0},
                "up": {"texture": "#overlay", "tintindex": 1},
            }}],
        }))
        for name, rgb in (("plain", (100, 40, 20)), ("overlay", (220, 220, 220))):
            image = Image.new("RGBA", (2, 1), (*rgb, 255))
            image.putpixel((1, 0), (0, 255, 0, 0))
            stream = BytesIO()
            image.save(stream, format="PNG")
            archive.writestr(f"assets/minecraft/textures/block/{name}.png", stream.getvalue())
    faces = extract_faces(jar, {"minecraft:test": {"default": {}}})["minecraft:test"]
    assert set(faces["side"]) == {"oklab", "tintedOklab", "untintedOklab"}
    assert set(faces["top"]) == {"oklab", "tintedOklab"}
    assert set(faces["bottom"]) == {"oklab"}
    for index, channel in enumerate(("L", "a", "b")):
        np.testing.assert_allclose(
            faces["side"]["tintedOklab"][channel], [_rgb_color((220, 220, 220))[index]] * 5
        )
        np.testing.assert_allclose(
            faces["side"]["untintedOklab"][channel], [_rgb_color((100, 40, 20))[index]] * 5
        )
    assert faces["side"]["oklab"] != faces["side"]["tintedOklab"]
    assert faces["side"]["untintedOklab"] == faces["bottom"]["oklab"]


@pytest.mark.parametrize("name", ["red_mushroom_block", "brown_mushroom_block", "mushroom_stem"])
def test_multipart_rotated_boundary_planes_form_a_full_cube(tmp_path, name):
    # 自作の単面をblockstateで回転し、閉じた立方体と植物の交差面を区別する。
    jar = tmp_path / "client.zip"
    blocks = {
        f"minecraft:{key}": {"default": {"closed": closed}, "properties": {},
                             "shape": "full", "material": "plant"}
        for key, closed in ((name, "true"), ("open_planes", "false"), ("cross", "false"))
    }
    with zipfile.ZipFile(jar, "w") as archive:
        plane = {"from": [0, 0, 0], "to": [16, 16, 0],
                 "faces": {"north": {"texture": "#test"}}}
        archive.writestr("assets/minecraft/models/block/plane.json",
                         json.dumps({"textures": {"test": "minecraft:block/plane"},
                                     "elements": [plane]}))
        image = Image.new("RGBA", (1, 1), (100, 40, 20, 255))
        stream = BytesIO()
        image.save(stream, format="PNG")
        archive.writestr("assets/minecraft/textures/block/plane.png", stream.getvalue())
        cross = {"from": [0, 0, 8], "to": [16, 16, 8],
                 "rotation": {"angle": 45, "axis": "y", "origin": [8, 8, 8]},
                 "faces": {"north": {"texture": "#test"}}}
        archive.writestr("assets/minecraft/models/block/cross.json",
                         json.dumps({"elements": [cross]}))
        parts = [{"apply": {"model": "minecraft:block/plane", "y": angle}}
                 for angle in (0, 90, 180, 270)]
        parts.extend({"apply": {"model": "minecraft:block/plane", "x": angle},
                      "when": {"closed": "true"}} for angle in (90, 270))
        for key in (name, "open_planes"):
            archive.writestr(f"assets/minecraft/blockstates/{key}.json",
                             json.dumps({"multipart": parts}))
        archive.writestr("assets/minecraft/blockstates/cross.json", json.dumps({
            "variants": {"": {"model": "minecraft:block/cross"}}
        }))
    models = extract_models(jar, blocks)
    assert models[f"minecraft:{name}"]["fullCube"]
    assert not models[f"minecraft:{name}"]["cross"]
    assert not models["minecraft:open_planes"]["fullCube"]
    assert not models["minecraft:cross"]["fullCube"]
    enrich_blocks(blocks, models)
    assert blocks[f"minecraft:{name}"]["shape"] == "full"
    assert blocks[f"minecraft:{name}"]["light"][-1]["opacity"] == 15
    assert blocks["minecraft:cross"]["shape"] == "plant"
    assert blocks["minecraft:cross"]["light"][-1]["opacity"] == 0
    faces = extract_faces(jar, blocks)
    assert set(faces[f"minecraft:{name}"]) == {"top", "side", "bottom"}
    assert set(faces["minecraft:open_planes"]) == {"side"}


@pytest.mark.parametrize(("part", "top", "bottom"), [
    pytest.param({"x": 90}, "south", "north", id="barrel-north"),
    pytest.param({"x": 90, "y": 90}, "south", "north", id="log-axis-x"),
    pytest.param({"x": 180}, "down", "up", id="upside-down"),
    pytest.param({"x": 270}, "north", "south", id="x-270"),
    pytest.param({"y": 90}, "up", "down", id="y-90"),
    pytest.param({}, "up", "down", id="unrotated"),
])
def test_default_variant_rotation_moves_face_colors_and_tint_layers(tmp_path, part, top, bottom):
    jar = tmp_path / "client.zip"
    colors = {"up": (255, 0, 0), "down": (0, 255, 0), "north": (0, 0, 255),
              "south": (255, 255, 0), "west": (255, 0, 255), "east": (0, 255, 255)}
    tinted = {"up", "south"}
    blocks = {"minecraft:test": {"default": {"axis": "x"}}}
    with zipfile.ZipFile(jar, "w") as archive:
        archive.writestr("assets/minecraft/blockstates/test.json", json.dumps({
            "variants": {"axis=x": {"model": "minecraft:block/test", "uvlock": True, **part},
                         "axis=y": {"model": "minecraft:block/test"}}
        }))
        archive.writestr("assets/minecraft/models/block/test.json", json.dumps({
            "textures": {direction: f"minecraft:block/{direction}" for direction in colors},
            "elements": [{"from": [0, 0, 0], "to": [16, 16, 16], "faces": {
                direction: {"texture": f"#{direction}", "cullface": direction,
                            "tintindex": 0 if direction in tinted else -1}
                for direction in colors
            }}],
        }))
        for direction, rgb in colors.items():
            image = Image.new("RGBA", (1, 1), (*rgb, 255))
            stream = BytesIO()
            image.save(stream, format="PNG")
            archive.writestr(f"assets/minecraft/textures/block/{direction}.png", stream.getvalue())
    faces = extract_faces(jar, blocks)["minecraft:test"]
    assert extract_models(jar, blocks)["minecraft:test"]["fullCube"]
    for face, directions in (("top", {top}), ("bottom", {bottom}),
                             ("side", colors.keys() - {top, bottom})):
        groups = {"oklab": directions}
        if directions & tinted:
            groups["tintedOklab"] = directions & tinted
            if directions - tinted:
                groups["untintedOklab"] = directions - tinted
        assert faces[face].keys() == groups.keys()
        for field, selected in groups.items():
            expected = np.quantile([_rgb_color(colors[d]) for d in sorted(selected)],
                                   [0.05, 0.25, 0.5, 0.75, 0.95], axis=0)
            for i, channel in enumerate(("L", "a", "b")):
                np.testing.assert_allclose(faces[face][field][channel], expected[:, i])


def test_boundary_face_uses_clockwise_x_then_y_rotation():
    north = {"from": [0, 0, 0], "to": [16, 16, 0], "faces": {"north": {}}}
    up = {"from": [0, 16, 0], "to": [16, 16, 16], "faces": {"up": {}}}
    assert _cube_faces(north, {"y": 90}) == {(1, 0, 0)}
    assert _cube_faces(north, {"x": 90}) == {(0, -1, 0)}
    assert _cube_faces(up, {"x": 90, "y": 90}) == {(1, 0, 0)}
