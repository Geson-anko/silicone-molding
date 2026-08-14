---
name: reference_blender_env
description: ローカル Blender の場所とバージョン、Blender↔Python の対応表、PyPI bpy wheel の OS 対応
type: reference
---

## ローカル環境 (2026-08-14 時点)

- `blender` = `/opt/homebrew/bin/blender` → **Blender 5.2.0 LTS**、内蔵 Python **3.13.13**
- アプリ本体は `/Applications/Blender.app`。Extension のマニフェストテンプレートは
  `/Applications/Blender.app/Contents/Resources/5.2/scripts/templates_toml/blender_manifest.toml`
- ユーザー設定は `~/Library/Application Support/Blender/<version>/`

## Blender ↔ Python の対応

PyPI の `bpy` パッケージの `requires_python` から確定できる:

| Blender | Python |
| ------- | ------ |
| 5.0     | 3.11   |
| 5.1     | 3.13   |
| 5.2     | 3.13   |

**これが `blender_version_min = "5.1.0"` の根拠。** 5.0 に対応するとツールチェーン全体を py311 構文に落とし、CI マトリクスも Python 2 世代に割れる。5.1 以降なら Python 3.13 単一で通せる。

## PyPI `bpy` wheel

`bpy` は fake ではなく **本物の Blender ランタイム**。tier 1 テストがこれで動く。

- 5.1.2 / 5.2.0 とも cp313
- 対応プラットフォーム: `macosx_11_0_arm64` / `manylinux_2_28_x86_64` / `win_amd64` / `win_arm64` — CI の 3 OS すべてを覆う
- 1 wheel あたり 200〜380MB。CI では uv のキャッシュを効かせる

**落とし穴**: `bmesh` / `mathutils` は `bpy` の C 初期化時に builtin として登録されるため、`import bmesh` を単独で先に書くと `ModuleNotFoundError` になる。実 Blender 内では常に存在するので wheel 環境固有の問題。

## 型スタブ

`fake-bpy-module-5.1` / `-5.2` が PyPI にある。実 `bpy` と同じ `bpy` パッケージ名を占有するので **同じ環境に共存できない**。`just type` は `uv run --isolated --with fake-bpy-module-5.1` の使い捨て環境で pyright を走らせてこれを回避している。

## Blender MCP

`blender-mcp` (uvx) + Blender 側の BlenderMCP アドオン。詳細は `/blender-mcp` skill。
