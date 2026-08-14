---
name: knowledge-operator-rna-and-error-reports
description: bpy wheel でオペレータ / パネルのメタデータと失敗経路を検証するときの実測知見 — ERROR report は bpy.ops で RuntimeError になる、クラスの bl_rna にオペレータの props は載らない、Panel の bl_options / poll は未定義なら属性ごと無い
metadata:
  type: project
---

2026-08-14、体積計測機能（`memory/specs/volume_measurement.md` AC-31〜AC-70）のモジュール B のテストを書くときに `bpy` 5.2 wheel で実測した 4 点。

**1. `self.report({"ERROR"}, ...)` を出したオペレータを `bpy.ops` 経由で呼ぶと `RuntimeError` が飛ぶ。** 戻り値は受け取れない（実測: `RuntimeError: Error: <message>`）。したがって仕様に「`{"CANCELLED"}` を返す」と書かれていても、`result == {"CANCELLED"}` では検証できない。`WARNING` は飛ばないので、既存の `apply_solidify`（WARNING + CANCELLED）は普通に戻り値を assert できる。

```python
with pytest.raises(RuntimeError):   # message は match しない（文言は仕様でない）
    bpy.ops.silicone_molding.measure_volume()
assert not settings.volume_measured  # 観測できるのは副作用のほう
```

**Why:** `poll` 失敗も同じ `RuntimeError` なので、素朴に書くと「実は poll が偽で execute に到達していない」テストが緑になる。

**How to apply:** 失敗経路のテストでは (a) Arrange の最後に `SILMOLD_OT_x.poll(bpy.context)` が真であることを assert する、または (b) 失敗時にリセットされるフラグを事前に真へ仕込む（`poll` 失敗なら `execute` が走らないのでフラグは真のまま残り、区別できる）。tier 2 は pytest が無いので `try` / `except RuntimeError` で受けて (b) を併用する。

**2. オペレータクラスの `bl_rna.properties` に、そのオペレータが宣言した props は載らない。** `SILMOLD_OT_copy_value.bl_rna` は Blender の `Operator` 構造体の RNA（`bl_idname` / `bl_options` / `layout` …14 件）に解決され、`value` は入らない。登録の確認は `bpy.ops` 側の RNA から取る:

```python
assert "value" in bpy.ops.silicone_molding.copy_value.get_rna_type().properties
```

`PropertyGroup` は逆で、`bpy.context.scene.silicone_molding.bl_rna.properties` に宣言したプロパティがそのまま載る（`unit` の確認もここ）。仕様書が「`bl_rna.properties` を見る」と書いていても、オペレータの場合はこの読み替えが必要。

**3. `Panel` サブクラスの `bl_options` / `poll` は、宣言していなければ属性そのものが存在しない。** `bpy.types.Panel` に既定値が無いため `cls.bl_options` は `AttributeError`（`in` 検査が例外になる）。`hasattr(bpy.types.Panel, "poll")` も False。

- 「`DEFAULT_CLOSED` を含まない」は `getattr(cls, "bl_options", frozenset())` で読む（未定義＝既定で開いている、なので意味的にも正しい）
- 「独自の `poll` を持たない」は `not hasattr(cls, "poll")` で書ける

**4. 登録したクラスは `dir(bpy.types)` に現れる。ただし名前は RNA 識別子。** パネルは `bl_idname` そのまま（`"SILMOLD_PT_main"`）、オペレータは `bl_idname` 由来の `SILICONE_MOLDING_OT_copy_value` になり Python のクラス名では引けない。サブパネルの親子登録（`bl_parent_id` の解決）が通ったことは `dir(bpy.types)` で確認できる。[[knowledge-operator-tests-in-background]] の 3 はこの点を「生えない」と書いていたが、正しくは「Python のクラス名では生えない」。

関連: [[knowledge-operator-tests-in-background]]、[[knowledge-volume-test-fixtures]]
