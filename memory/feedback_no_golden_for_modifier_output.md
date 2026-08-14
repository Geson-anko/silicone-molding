---
name: feedback_no_golden_for_modifier_output
description: Blender 標準モディファイアの出力に golden mesh を作らない。検証は解析的な不変量で行う
type: feedback
---

**Blender 本体のモディファイア（Solidify / Boolean / Subdivision 等）の評価結果を golden mesh として `tests/fixtures/` に固定してはならない。** 検証は `mesh_invariants` の解析的な不変量（頂点数・面数・watertight・loose parts・volume・bbox）だけで行う。

**Why:** golden mesh は「このリポジトリのコードが生成したジオメトリ」を固定するためのもの。モディファイアの出力は Blender 側の実装に属し、頂点順・分割の仕方・数値がバージョン間で揺れる。CI は Blender 5.1 / latest の 2 系統を回すため、ピン留めすると自分たちの変更と無関係に赤くなる。2026-08-14 の Solidify 機能仕様（`memory/specs/solidify.md`）でこの方針をユーザーと確定した。

**How to apply:** 自前の `bmesh.ops` パイプラインで作ったジオメトリには従来どおり golden を使う（`/testing-strategy` の 2 段構え）。モディファイアを経由する機能では 2 段目を省き、期待値を仕様から手計算した不変量で押さえる。例: 2×2×2 の立方体に厚み 0.003 を外側 Solidify → `volume == 2.006**3 - 8`、bbox ±1.003、loose parts 2。この値は `use_even_offset=True` のときにのみ厳密に成立する（OFF だと角が 1/√3 に痩せる）ので、不変量そのものが設定の検証を兼ねる。
