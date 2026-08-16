---
name: knowledge-volume-test-fixtures
description: 体積系テストの fixture 実測知見 — matrix_world は depsgraph flush まで stale、from_pydata で bmesh 無しに open / non-manifold メッシュを作る、退化 fixture には前提テストを添える
metadata:
  type: project
---

2026-08-14、体積計測機能（`memory/specs/volume_measurement.md` AC-12〜AC-30）のテストを書くときに実測で確かめた 3 点。

**1. `obj.scale` / `location` / `rotation_euler` への代入は `matrix_world` に即座に反映されない。** depsgraph が flush されるまで古い行列が返る（実測: `obj.scale = (2,1,1)` の直後に `obj.matrix_world.to_3x3().determinant()` を読むと **1.0**）。`bpy.context.evaluated_depsgraph_get()` が flush を行うので、**変換を設定した後に depsgraph を取る**だけで正しくなる。

```python
cube_object.scale = (2.0, 1.0, 1.0)
depsgraph = bpy.context.evaluated_depsgraph_get()  # ここで flush される
volume = world_volume(cube_object, depsgraph)      # 中で読む matrix_world は最新
```

**Why:** ワールド体積は `abs(matrix_world.to_3x3().determinant())` 倍で求まるため、行列が stale だとスケールを与えたテストが素の体積を測って落ちる（あるいは期待値を `matrix_world` から取っていれば **両方 stale で緑になる**）。後者が危険。

**How to apply:** 変換を与えるテストでは Arrange の最後に depsgraph を取る。期待値は行列から読まず、スケール値から解析的に書く（`2.0 * EXPECTED_CUBE_VOLUME`）。`view_layer.update()` を足す必要はない。

**2. 退化メッシュは `mesh.from_pydata` + `mesh.update()` で作れる。** `bmesh` の import は `tests/_helpers.py` が独占しているので、テストモジュール側で「面を 1 枚外した立方体」「辺に 3 枚目の面がある立方体」を作るにはこれが素直な手段になる。頂点リストと面リストがテストのソースに見えるのも利点。実測値:

- 立方体 6 面のうち +Z を外す → 境界辺 4 / 非多様体辺 0
- 立方体 6 面 + 既存辺に三角形 1 枚 → 非多様体辺 1 / 境界辺 2（仕様 §5.11 の実測と一致）
- 面リストの向きを揃えて書けば `from_pydata` 製の立方体でも `calc_volume()` は 8.0 を返す（`bmesh.ops.create_cube` と等価）

**3. 退化 fixture には「前提テスト」を 1 つ添える。** `mesh_invariants` で境界辺数・非多様体辺数を assert しておく。fixture が黙って閉じていると「開いたメッシュで `None` を返す」テストが **何も検証せずに緑** になるため。実装側の watertight 判定と `tests/_helpers.MeshInvariants.is_watertight` を統合してはならない（仕様 §5.2）という規約は、この前提テストがあって初めて意味を持つ。

関連: [[knowledge-modifier-bake-tests]]、[[knowledge-operator-tests-in-background]]
