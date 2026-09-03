---
name: knowledge-operator-tests-in-background
description: bpy wheel の background で operators 層をテストするときの実測知見 — 起動時シーンの選択、edit mode 検証の可否、bpy.ops 登録確認、batch_remove の segfault
metadata:
  type: project
---

`operators/` 層（`context.selected_objects` / `poll` / `bpy.ops` 経由の実行）を tier 1 で検証したときに実測で確かめた 4 点。

**1. 起動時シーンには選択済みの `Cube` が既に居る。** `bpy.context.selected_objects` は何もしなくても `[bpy.data.objects['Cube']]` を返すので、「選択 0 個で `poll` が偽」を検証するテストは **fixture の setup で全オブジェクトを deselect してから** でないと嘘になる。`for obj in bpy.context.scene.objects: obj.select_set(False)` で足りる（`bpy.ops.object.select_all` は不要）。

**2. background でも edit mode に入れる。** `bpy.context.view_layer.objects.active = obj` の後 `bpy.ops.object.mode_set(mode="EDIT")` が `{'FINISHED'}` を返し、`bpy.context.mode` は `"EDIT_MESH"` になる。**このとき選択は維持される**ので、「`poll` が OBJECT モードを要求する」という条件を空振りせずに検証できる。teardown では必ず OBJECT モードへ戻す（オブジェクト削除がモード依存で壊れるため）。

**3. `hasattr(bpy.ops.<namespace>, "<op>")` は常に True。** `bpy.ops` は属性アクセス時に遅延でオブジェクトを作るため、存在しないオペレータ名でも True が返る（呼び出して初めて `AttributeError`）。**オペレータが登録されたことの検証は `"solidify" in dir(bpy.ops.silicone_casting)` で書く。** 削除前の `tests/blender/run.py` はこの `hasattr` を使っており、実質的に何も検証していなかった。（2026-08-14 訂正: `register_class` したクラスは `bpy.types` に生える。ただし Python のクラス名ではなく RNA 識別子で、オペレータは `SILICONE_CASTING_OT_solidify`、パネルは `bl_idname` そのまま。詳細は [[knowledge-operator-rna-and-error-reports]] の 4）

**4. 削除済みデータブロックへの再アクセスは segfault する。** `bpy.data.batch_remove((mesh,))` を同じ参照に 2 回呼ぶと Python レベルの例外ではなく Segmentation fault になり、pytest の出力ごと消える。fixture の後始末では、削除対象を「型名 + 名前」でユニーク化し、`users == 0` を確認して **1 回だけ** 渡す。

**Why:** 2026-08-14 の Solidify 機能（`memory/specs/solidify.md` AC-30〜AC-37 / AC-42）で `tests/silicone_casting/operators/` と tier 2 を書いたときに確認した。1 と 3 はテストが常に緑になる（＝何も検証していない）タイプの罠なので特に危険。

**How to apply:** `poll` や選択走査を検証するテストでは、選択状態を自分で作る fixture を必ず用意する。オペレータの登録確認は `dir()`。関連: [[knowledge-modifier-bake-tests]]、[[knowledge-tier1-test-module-names]]
