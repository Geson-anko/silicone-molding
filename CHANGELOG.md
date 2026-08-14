# Changelog

形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)、バージョニングは
[Semantic Versioning](https://semver.org/lang/ja/) に従う。

リリースワークフローが `## [x.y.z] - YYYY-MM-DD` の節を抽出して GitHub Release の
本文にするため、**見出しの形式を崩さないこと**。

## [Unreleased]

### Added

- Blender Extension としてのパッケージング（`blender_manifest.toml`、Blender 5.1 以上）
- **Solidify** オペレータ（`silicone_molding.solidify`）— 選択中のメッシュに、アドオン専用の Solidify モディファイアを付与する。既にあれば同じものを更新するので重ね掛けにならない
- **Apply** オペレータ（`silicone_molding.apply_solidify`）— そのモディファイアだけをメッシュに焼き込む。`bpy.ops` を使わず depsgraph 評価で行うため background でも動く
- 3D ビューサイドバーの **Silicone Molding** パネルと、壁厚（mm 入力。シーンの単位設定に依らない）・方向反転のプロパティ
- サイドバーの **Measurement**（計測）/ **Processing**（加工）の 2 セクション構成。それぞれ独立に折りたためる。壁厚・方向反転・Solidify・Apply は Processing に入る
- **Measure Volume** オペレータ（`silicone_molding.measure_volume`）— 選択中のメッシュの体積を合計し、cm³（= ml）で表示する。モディファイア込みのワールド実寸で測るので、Solidify を掛けた壁に必要な樹脂量がそのまま読める。閉じていないメッシュが混ざっている場合は数値を出さず、原因のオブジェクト名を挙げてエラーにする。結果はボタンを押した時点のスナップショットで、シーンを変えても自動更新はされない（押し直して更新する）
- 表示された体積をクリックしてクリップボードへコピーする機能（`silicone_molding.copy_value`）。単位も桁区切りも含まない数値だけが入るので、表計算にそのまま貼れる
- 2 階層のテスト（PyPI `bpy` wheel 上の pytest / 実 Blender へインストールしての統合チェック）と golden mesh 比較の基盤
- Windows / macOS / Linux での CI と、タグ push でのリリース自動化

[unreleased]: https://github.com/Geson-anko/silicone-molding/commits/main
