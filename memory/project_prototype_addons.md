---
name: project_prototype_addons
description: repo 外の Blender addons ディレクトリに既存プロトタイプ mold_cut / mold_split がある。次フェーズの移植元
type: project
---

このリポジトリの **外** に、ユーザーが書いた型生成プロトタイプが 2 本ある:

- `~/Library/Application Support/Blender/5.0/scripts/addons/mold_cut_addon.py` (473 行, "Mold Cut" v1.0.0)
- `~/Library/Application Support/Blender/5.0/scripts/addons/mold_split_addon.py` (501 行, "Mold Split" v3.0.0 — インターロック段差付き)

共通のアプローチ: **seam でマークされた辺で面をフラッドフィル分割 → 領域境界を抽出 → 境界パスを順序化（開いた path / 閉じた loop 判定） → Newell 法で切断面の法線を求めて cut surface を生成 → Solidify で型の殻を作り → Boolean DIFFERENCE → loose parts で分離**。

**Why:** 2026-08-14 時点でこれが唯一の動作する実装であり、造形上どういう手順が必要かの根拠になっている。ただし repo 外にあるため **git 履歴からは一切辿れない**。ローカルマシンにしか存在しない。

**How to apply:** 型分割機能を実装するときの移植元・参照元として読む。ただしそのまま移植しない — プロトタイプは `bpy.ops`（`modifier_apply` / `mesh.separate` / `object.select_all`）に強く依存しており、この repo の「`core/` は `bpy.ops` 非依存」規約に反する。`bmesh.ops` とデータ API で書き直す前提で、**アルゴリズムだけを継承する**。移植前に `spec-planner` で仕様化するのが望ましい。

同ディレクトリには `geson_geometry_tools.py` / `hide_only_vertex.py` もあるが、これらは型生成とは無関係な汎用ツール。
