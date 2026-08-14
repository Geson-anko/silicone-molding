# Changelog

形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)、バージョニングは
[Semantic Versioning](https://semver.org/lang/ja/) に従う。

リリースワークフローが `## [x.y.z] - YYYY-MM-DD` の節を抽出して GitHub Release の
本文にするため、**見出しの形式を崩さないこと**。

## [Unreleased]

### Added

- Blender Extension としてのパッケージング（`blender_manifest.toml`、Blender 5.1 以上）
- **Make Shell** オペレータ（`silicone_molding.make_shell`）— アクティブメッシュの外側にオフセットシェルを生成する
- 3D ビューサイドバーの **Silicone Molding** パネルと壁厚プロパティ
- 2 階層のテスト（PyPI `bpy` wheel 上の pytest / 実 Blender へインストールしての統合チェック）と golden mesh
- Windows / macOS / Linux での CI と、タグ push でのリリース自動化

[unreleased]: https://github.com/Geson-anko/silicone-molding/commits/main
