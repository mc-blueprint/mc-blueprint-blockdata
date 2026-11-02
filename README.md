# mc-blueprint-blockdata

Minecraft Java Edition の版ごとのブロックデータを生成し、[mc-blueprint](https://github.com/mc-blueprint/mc-blueprint) などへリリース資産として提供する。

## 生成

Python 3.11 以上と、対象バージョンに対応した Java が必要です（1.21 系は Java 21、26 系は Java 25）。

```powershell
python -m pip install -e ".[dev]"
python -m mcblockdata build --version 1.21.11 --download --java "C:\path\to\java.exe"
```

`--download` は Mojang 公式 version manifest から server jar を取得して SHA-1 を検証し、Windows では `%LOCALAPPDATA%\mc-blueprint\cache\jars\`、他の OS では `~/.cache/mc-blueprint/jars/` に保存します。既存 jar は `--server-jar <path>` で指定できます。生成結果は `dist/blockdata-<版>.json` に書き出し、`schema/blockdata.schema.json` で検証します。

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

初期実装ではブロック一覧・状態・既定値を生成します。面ごとの色など後続 Issue の属性と対応版のリリース資産は順次追加します。配布するのは数値のデータだけで、Minecraft の jar・テクスチャ・モデルは含めません。抽出には利用者が取得した jar を使います。

本プロジェクトは非公式で、Mojang Studios・Microsoft とは関係ありません。
