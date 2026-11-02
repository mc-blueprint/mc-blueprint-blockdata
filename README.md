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

`--all` は Mojang 公式 version manifest から server/client jar を取得して SHA-1 を検証し、Windows では `%LOCALAPPDATA%\mc-blueprint\cache\jars\`、他の OS では `~/.cache/mc-blueprint/jars/` に保存します。全版に面ごとの色を含めます。単版は `python -m mcblockdata build --version 1.21.11 --download --download-client` で生成できます。既存 jar は単版の `--server-jar <path>` と `--client-jar <path>` で指定できます。各 blockdata は生成時にパッケージ内の `src/mcblockdata/blockdata.schema.json` で検証します。wheel からも `mcblockdata.generator.validate(data)` を利用できます。

生成は本リポジトリの Git checkout から行います。`generator.commit` は実行ディレクトリによらず生成器自身の HEAD です。取得できない場合は生成を失敗させます。出力 JSON・チェックサム・commit ファイルの改行は LF です。

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

### 着色の形式と適用

`faces` は着色を掛けていない素材色です。`tint: grass / foliage / water` では `tints[種類][バイオームID]`、`tint: fixed` では追加の `tints.fixed[名前空間付きブロックID]` を参照します。どちらの値も OKLab の `[L, a, b]` です。`tints.fixed` は formatVersion 1 に対する互換追加で、例は `{"minecraft:spruce_leaves": [L, a, b], "minecraft:birch_leaves": [L, a, b]}` です。

素材色と乗算色をそれぞれ OKLab から**線形 sRGB** へ変換し、RGB の各成分を掛けます。OKLab の成分同士やガンマ符号化された sRGB 同士を掛けません。viewer はモデルの `tintindex >= 0` の面にだけ着色し、配色選択でも未着色部分と区別してください。固定色を `faces` に焼き込みません。

`faces.<面>` に、formatVersion 1 の互換追加として `tintedOklab` と `untintedOklab` を提供します。いずれも `oklab` と同じ `{L: [5点], a: [5点], b: [5点]}`（5/25/50/75/95パーセンタイル）で、着色前の素材色です。

- `oklab`：従来どおり、全層の不透明画素を合わせた分位点を保持します。
- `tintedOklab`：`tintindex >= 0` の層に不透明画素がある場合だけ出力します。
- `untintedOklab`：着色層と未着色層の両方がある面で、未着色層の分位点を出力します。

Materialize は `tintedOklab` にだけブロックの乗算色を適用し、`untintedOklab` はそのまま扱います。`tintedOklab` があり `untintedOklab` がなければ全層が着色対象、両方なければ `oklab` だけを未着色として扱います。`tint: none` のブロックにはモデルの `tintindex` にかかわらず着色しません。たとえば `grass_block` の側面には両方、上面には `tintedOklab` だけ、底面には追加フィールドを出しません。層別フィールドに対応しない既存利用側は、従来の `oklab` を引き続き読めます。旧生成物には層別フィールドがないため、この判定には再生成したデータを使用してください。

形状・遮光の補正と着色面の確認は client jar の blockstate と継承済みモデルの `elements`・`tintindex` を使います。client jar を省略した生成ではモデルによる補正と面色抽出を行いません。モデルから色登録や特殊描画の有無は決まらないため、登録対象と固定値だけを `visuals.py` の出典付き規則で補います。

面色の `top`・`side`・`bottom` は、既定状態の variant / multipart の `x`・`y` 回転を適用した後の向きです。立方体の外周6面の判定にも同じ回転計算を使います。

根拠は [Minecraft Wiki のバイオーム着色](https://minecraft.wiki/w/Biome#Tint)、[モデルの tintindex](https://minecraft.wiki/w/Block_model)、[スイレンの葉の固定色](https://minecraft.wiki/w/Lily_Pad#Appearance) と公式 jar です。状態依存の着色（レッドストーン・茎）や落ち葉の dry_foliage 色表は現在の v1 契約に表現がなく、本追加では対象に含めません。

## 範囲

| 担当する | 担当しない |
|---|---|
| Minecraft のブロックに関する事実のデータ | 実在建築の配色統計（mc-blueprint-color-stats） |
| 版間の差分の記録 | 生成時の配色選択（mc-blueprint） |
| | テクスチャ画像・jar の保存・配布 |

## 状態

ブロック一覧・状態・既定値、面ごとの色、状態ごとの光、着色、描画方式を生成します。配布するのは数値データだけで、Minecraftのjar・テクスチャ・モデルは含めません。抽出には利用者が取得したjarを使います。

本プロジェクトは非公式で、Mojang Studios・Microsoft とは関係ありません。
