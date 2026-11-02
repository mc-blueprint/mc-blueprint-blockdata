import json
import zipfile
from io import BytesIO

from PIL import Image

from mcblockdata.colors import extract_faces


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
