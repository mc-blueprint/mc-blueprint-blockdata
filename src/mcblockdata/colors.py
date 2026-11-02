"""Client jarのブロックモデルから面ごとのOKLab分位点を抽出する。"""

from __future__ import annotations

import json
import zipfile
from collections import defaultdict
from pathlib import Path

import colour
import numpy as np
from PIL import Image

QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)
FACES = ("top", "side", "bottom")


def _resource(value: str, directory: str) -> str:
    namespace, separator, path = value.partition(":")
    if not separator:
        namespace, path = "minecraft", namespace
    return f"assets/{namespace}/{directory}/{path}"


def _model(archive: zipfile.ZipFile, model_id: str, cache: dict[str, dict]) -> dict:
    if model_id in cache:
        return cache[model_id]
    model = json.loads(archive.read(_resource(model_id, "models") + ".json"))
    parent = model.pop("parent", None)
    if parent:
        inherited = _model(archive, parent, cache)
        model = {
            **inherited,
            **model,
            "textures": inherited.get("textures", {}) | model.get("textures", {}),
            "elements": model.get("elements", inherited.get("elements", [])),
        }
    cache[model_id] = model
    return model


def _state_models(state: dict, defaults: dict[str, str]) -> list[str]:
    selected = []
    for key, value in state.get("variants", {}).items():
        requirements = dict(part.split("=", 1) for part in key.split(",") if part)
        if all(defaults.get(name) == expected for name, expected in requirements.items()):
            choices = value if isinstance(value, list) else [value]
            selected.extend(choice["model"] for choice in choices)
    if selected:
        return selected
    for part in state.get("multipart", []):
        choices = part["apply"] if isinstance(part["apply"], list) else [part["apply"]]
        selected.extend(choice["model"] for choice in choices)
    return selected


def _face(direction: str, data: dict) -> str:
    cullface = data.get("cullface", direction)
    return "top" if cullface == "up" else "bottom" if cullface == "down" else "side"


def _pixels(image: Image.Image) -> np.ndarray:
    rgba = np.asarray(image.convert("RGBA"), dtype=np.float64) / 255
    rgb = rgba[rgba[:, :, 3] == 1.0, :3]
    if not len(rgb):
        return np.empty((0, 3), dtype=np.float64)
    xyz = colour.RGB_to_XYZ(
        rgb,
        colourspace=colour.RGB_COLOURSPACES["sRGB"],
        apply_cctf_decoding=True,
    )
    return np.asarray(colour.XYZ_to_Oklab(xyz))


def _distribution(pixels: np.ndarray) -> dict[str, list[float]]:
    return {
        channel: np.quantile(pixels[:, index], QUANTILES).tolist()
        for index, channel in enumerate(("L", "a", "b"))
    }


def extract_faces(client_jar: Path, blocks: dict[str, dict]) -> dict[str, dict]:
    """blockstate/model/textureをたどり、各block IDの面別OKLab分位点を返す。"""
    faces_by_block = {}
    with zipfile.ZipFile(client_jar) as archive:
        names = set(archive.namelist())
        model_cache = {}
        state_names = sorted(
            name
            for name in names
            if name.startswith("assets/minecraft/blockstates/") and name.endswith(".json")
        )
        for state_name in state_names:
            block_id = "minecraft:" + Path(state_name).stem
            info = blocks.get(block_id)
            if info is None:
                continue
            state = json.loads(archive.read(state_name))
            by_face = defaultdict(list)
            for model_id in _state_models(state, info["default"]):
                model = _model(archive, model_id, model_cache)
                textures = {
                    key: value["sprite"] if isinstance(value, dict) else value
                    for key, value in model.get("textures", {}).items()
                }
                for element in model.get("elements", []):
                    for direction, face_data in element.get("faces", {}).items():
                        texture = face_data["texture"]
                        seen = set()
                        while texture.startswith("#"):
                            key = texture[1:]
                            if key in seen or key not in textures:
                                break
                            seen.add(key)
                            texture = textures[key]
                        if texture.startswith("#"):
                            continue
                        texture_name = _resource(texture, "textures") + ".png"
                        if texture_name not in names:
                            continue
                        with archive.open(texture_name) as stream, Image.open(stream) as image:
                            pixels = _pixels(image)
                        if len(pixels):
                            by_face[_face(direction, face_data)].append(pixels)
            if by_face:
                faces_by_block[block_id] = {
                    face: {"oklab": _distribution(np.concatenate(by_face[face]))}
                    for face in FACES
                    if by_face[face]
                }
    return faces_by_block


def extract_tints(client_jar: Path, biomes: dict[str, dict]) -> dict[str, dict]:
    """colormapとbiome定義からgrass/foliage/waterのOKLab色表を作る。

    根拠: minecraft.wiki/w/Temperature と /Biome_definition_(Java_Edition)。
    気候座標はJava版Biome#getGrassColorAtTemperatureの256x256参照式。
    swamp/dark_forest/badlandsの固定色はBiomeColorsの特殊処理を適用する。
    """
    with zipfile.ZipFile(client_jar) as archive:
        maps = {}
        for kind in ("grass", "foliage"):
            with archive.open(f"assets/minecraft/textures/colormap/{kind}.png") as stream:
                maps[kind] = np.asarray(Image.open(stream).convert("RGB"))

    result = {kind: {} for kind in ("grass", "foliage", "water")}
    for biome_id, biome in sorted(biomes.items()):
        effects = biome.get("effects", {})
        temp = min(1.0, max(0.0, float(biome.get("temperature", 0.5))))
        downfall = min(1.0, max(0.0, float(biome.get("downfall", 0.0))))
        x = min(255, max(0, int((1 - temp) * 255)))
        y = min(255, max(0, int((1 - temp * downfall) * 255)))
        grass = _colormap_color(maps["grass"][y, x])
        foliage = _colormap_color(maps["foliage"][y, x])

        if biome_id.endswith(("badlands", "wooded_badlands", "eroded_badlands")):
            grass = _rgb_color(0x90814D)
            foliage = _rgb_color(0x9E814D)
        if biome_id.endswith(("swamp", "mangrove_swamp")):
            grass = _rgb_color(0x6A7039)
            foliage = _rgb_color(0x8DB127 if biome_id.endswith("mangrove_swamp") else 0x6A7039)
        if biome.get("effects", {}).get("grass_color_modifier") == "dark_forest":
            rgb = tuple(int(value) for value in maps["grass"][y, x])
            grass = _rgb_color(
                tuple(
                    (((channel & 0xFE) + mask) // 2)
                    for channel, mask in zip(rgb, (0x28, 0x34, 0x0A), strict=True)
                )
            )

        for kind, override in (("grass", "grass_color"), ("foliage", "foliage_color")):
            value = effects.get(override)
            if value is not None:
                color = _rgb_color(_color_value(value))
            else:
                color = grass if kind == "grass" else foliage
            result[kind][biome_id.removeprefix("minecraft:")] = color
        water = _color_value(effects.get("water_color", 0x3F76E4))
        result["water"][biome_id.removeprefix("minecraft:")] = _rgb_color(water)
    return result


def _colormap_color(rgb: np.ndarray) -> list[float]:
    return _rgb_color(tuple(int(channel) for channel in rgb))


def _rgb_color(rgb: int | tuple[int, int, int]) -> list[float]:
    if isinstance(rgb, int):
        rgb = ((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255)
    values = np.asarray([rgb], dtype=np.float64) / 255
    xyz = colour.RGB_to_XYZ(
        values,
        colourspace=colour.RGB_COLOURSPACES["sRGB"],
        apply_cctf_decoding=True,
    )
    return np.asarray(colour.XYZ_to_Oklab(xyz)[0]).tolist()


def _color_value(value: int | str) -> int:
    return int(value.removeprefix("#"), 16) if isinstance(value, str) else value
