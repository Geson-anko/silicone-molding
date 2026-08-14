---
name: knowledge-modifier-bake-tests
description: モディファイア焼き込みを tier 1 で検証するときの落とし穴 — float32 由来の体積誤差、空メッシュで落ちる mesh_invariants、data 差し替えを前提にした fixture の後始末
metadata:
  type: project
---

Blender のモディファイア評価結果を tier 1 で検証するときに実測で確かめた 3 点。仕様書の受け入れ基準をそのまま数値として写すと落ちる場合がある。

**1. 体積の許容誤差は相対 1e-6 では足りない。** Blender はメッシュ座標を float32 で保持するので、解析値 1.003 は 1.0030000209808350 として格納される。2×2×2 立方体に厚み 0.003 の Solidify を焼き込んだ体積は `2.006**3 - 8 = 0.0722162` に対し実測 `0.0722167`（絶対 5.1e-7 / 相対 7.0e-6）。体積が「8 前後の大きな数の差」であるため座標の丸め誤差が 12 倍に増幅される。bbox 側は絶対 2.1e-8 なので `abs=1e-6` で通る。**体積は絶対許容誤差（この規模なら `abs=1e-5`）で書く。** それでも厚みが 0.1% ずれれば検出できる。

**Why:** 2026-08-14 の Solidify 仕様 (`memory/specs/solidify.md` AC-17 / AC-21) が相対 1e-6 を要求していたが、実測すると達成不能だった。仕様の数値を疑わずに写すとテストが恒常的に赤くなる。

**How to apply:** ジオメトリの体積を assert するときは、まず「float32 座標の丸めが体積にどれだけ効くか」を見積もってから許容誤差を決める。目安は `dV/dx * 6e-8`（`dV/dx` は寸法変化に対する体積の感度）。

**2. `tests/_helpers.mesh_invariants` は頂点 0 のメッシュで `ValueError` を投げる**（bbox の `min()` が空 iterable になる）。面 0 / 頂点 0 のケースは `len(mesh.polygons)` / `len(mesh.vertices)` を直接読む。

**3. 焼き込みはオブジェクトの mesh データブロックを差し替えて旧ブロックを削除する。** fixture の後始末は「作った時点のメッシュ」ではなく **teardown 時点の `obj.data`** を読むこと。`tests/conftest.py` の `make_object` factory がこの形で、共有メッシュに備えて `mesh.users == 0` を見てから remove する。conftest の `cube_mesh` / `empty_mesh` fixture は自分が作ったメッシュを remove するため、焼き込みを行うテストに渡すと二重 remove（stale datablock アクセス）になる。焼き込み系では `make_object` / `cube_object` を使う。
