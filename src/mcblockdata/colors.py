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
            name for name in names
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
                    for face in FACES if by_face[face]
                }
    return faces_by_block
