import json

from mcblockdata.generator import write_checksums, write_diff


def test_write_diff_records_added_removed_and_state_changes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "dist").mkdir()
    old = {
        "minecraft:stone": {"properties": {"axis": ["x"]}, "default": {"axis": "x"}},
        "minecraft:gone": {"properties": {}, "default": {}},
    }
    new = {
        "minecraft:stone": {
            "properties": {"axis": ["x", "y"]},
            "default": {"axis": "x"},
        },
        "minecraft:new": {"properties": {}, "default": {}},
    }
    for version, blocks in (("1", old), ("2", new)):
        (tmp_path / "dist" / f"blockdata-{version}.json").write_text(
            json.dumps({"blocks": blocks}), encoding="utf-8"
        )

    path = write_diff("1", "2")
    diff = json.loads(path.read_text(encoding="utf-8"))

    assert diff["added"] == ["minecraft:new"]
    assert diff["removed"] == ["minecraft:gone"]
    assert diff["changed"] == {
        "minecraft:stone": {
            "properties": {
                "from": {"axis": ["x"]},
                "to": {"axis": ["x", "y"]},
            }
        }
    }


def test_write_checksums_includes_sorted_asset_names(tmp_path):
    first = tmp_path / "b.json"
    second = tmp_path / "a.json"
    first.write_text("{}\n", encoding="utf-8")
    second.write_text("[]\n", encoding="utf-8")
    output = tmp_path / "dist" / "SHA256SUMS"

    write_checksums([first, second], output)

    assert [line.split("  ", 1)[1] for line in output.read_text().splitlines()] == [
        "a.json",
        "b.json",
    ]
