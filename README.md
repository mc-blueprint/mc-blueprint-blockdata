# mc-blueprint-blockdata

Minecraft Java Edition の版ごとのブロックデータを生成し、[mc-blueprint](https://github.com/mc-blueprint/mc-blueprint) などへリリース資産として提供する。

## 生成

Python 3.11 以上と、対象バージョンに対応した Java が必要です（1.21 系は Java 21、26 系は Java 25）。全4版を生成するには、開発用依存関係を入れて次を実行します。

```powershell
python -m pip install -e ".[dev]"
python -m mcblockdata build --all `
  --java-for "1.21.11=C:\Program Files\Eclipse Adoptium\jdk-21\bin\java.exe" `
  --java-for "26.1.2=C:\Program Files\Eclipse Adoptium\jdk-25\bin\java.exe" `
  --java-for "26.2=C:\Program Files\Eclipse Adoptium\jdk-25\bin\java.exe" `
  --java-for "26.3=C:\Program Files\Eclipse Adoptium\jdk-25\bin\java.exe"
```

`--all` は Mojang 公式 version manifest から server/client jar を取得して SHA-1 を検証し、Windows では `%LOCALAPPDATA%\mc-blueprint\cache\jars\`、他の OS では `~/.cache/mc-blueprint/jars/` に保存します。全版に面ごとの色を含めます。単版は `python -m mcblockdata build --version 1.21.11 --download --download-client` で生成できます。既存 jar は単版の `--server-jar <path>` と `--client-jar <path>` で指定できます。各 blockdata は生成時に `schema/blockdata.schema.json` で検証します。

## リリース資産

GitHub Release には次のファイルを添付します（`dist/` の内容はGitにコミットしません）。

- `blockdata-1.21.11.json`、`blockdata-26.1.2.json`、`blockdata-26.2.json`、`blockdata-26.3.json`
- `blockdata-diff-1.21.11-26.1.2.json`、`blockdata-diff-26.1.2-26.2.json`、`blockdata-diff-26.2-26.3.json`
- `SHA256SUMS`：上記 JSON と `generator.commit` の SHA-256
- `generator.commit`：生成器の Git commit ID

mc-blueprint は blockdata JSON をリリースから取得し、`SHA256SUMS` で検証したうえで、`generator.commit` を出所記録に使います。版間差分は追加・削除のブロックIDと、共通ブロックの状態定義変更を記録するJSONです。例：

```json
{
  "formatVersion": 1,
  "from": "26.1.2",
  "to": "26.2",
  "added": ["minecraft:new_block"],
  "removed": ["minecraft:old_block"],
  "changed": {
    "minecraft:example": {
      "properties": {"from": {"powered": ["false"]}, "to": {"powered": ["false", "true"]}},
      "default": {"from": {"powered": "false"}, "to": {"powered": "false"}}
    }
  }
}
```

開発時の確認は `ruff check .` と `pytest` で行います。

## 提供するデータ

- ブロックの一覧・状態・既定値（Mojang 公式データジェネレーターの reports から生成）
- 面ごとの色（OKLab の分位点。テクスチャの素材色）
- 材質（石材・木材・レンガ・漆喰・金属・ガラスなど）、ブロックファミリー（階段・ハーフ・壁の対応）
- 劣化の連鎖（苔・ひび）、状態ごとの発光・遮光、着色の種類とバイオームの着色表、描画の種類

対応予定版：`1.21.11`、`26.1.2`、`26.2`、`26.3`。

## 範囲

| 担当する | 担当しない |
|---|---|
| Minecraft のブロックに関する事実のデータ | 実在建築の配色統計（mc-blueprint-color-stats） |
| 版間の差分の記録 | 生成時の配色選択（mc-blueprint） |
| | テクスチャ画像・jar の保存・配布 |

## 状態

ブロック一覧・状態・既定値、面ごとの色、状態ごとの光、着色、描画方式を生成します。配布するのは数値データだけで、Minecraftのjar・テクスチャ・モデルは含めません。抽出には利用者が取得したjarを使います。

本プロジェクトは非公式で、Mojang Studios・Microsoft とは関係ありません。
