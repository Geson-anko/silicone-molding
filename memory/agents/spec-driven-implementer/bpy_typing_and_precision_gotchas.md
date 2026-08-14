---
name: bpy-typing-and-precision-gotchas
description: fake-bpy-module-5.1 の型スタブの罠（bpy_prop_collection.get / Context.selected_objects が optional）と、Blender メッシュが float32 であることによる体積の相対誤差の下限
metadata:
  type: project
---

# `bpy` の型スタブと数値精度の落とし穴

## `bpy_prop_collection.get()` は pyright strict で使えない

`fake-bpy-module-5.1` の `bpy_prop_collection.get` は
`def get[_T](self, key, default: _T = None) -> _T | None` と綴られている。
`default` を省くと `_T` が `None` に解決され、戻り値の型が `None` になる。
その結果 `isinstance(mod, bpy.types.SolidifyModifier)` が
`reportUnnecessaryIsInstance` で落ちる。

**Why:** スタブ側のジェネリクスの綴り方の問題で、実行時の挙動とは無関係。

**How to apply:** コレクションから名前で 1 件取るときは `.get(name)` ではなく
`for item in collection: if item.name == NAME` で回す。Blender は同一コレクション内で
名前の一意性を保証するので、最初の一致が唯一の一致。

## `Context.selected_objects` はスタブ上 optional

`fake-bpy-module-5.1` では `Context.selected_objects: Sequence[Object] | None`。
そのまま内包表記で回すと `reportOptionalIterable` で落ちる。

**Why:** オブジェクト選択を持たないスペースタイプでは提供されないため、スタブが
`| None` を付けている。実行時（3D View / background とも）はリストが返る。

**How to apply:** `selected = context.selected_objects or ()` で narrow する。
`None` も空選択も「対象 0 件」に潰れるので、防御的コードにはならない。
`Panel.layout` の `assert layout is not None` と同じく、スタブ由来の narrow には
理由をコメントで残す。

## Blender のメッシュ座標は float32 → 体積の相対誤差は ~1e-5 が下限

`bm.calc_volume()` の結果は、頂点座標が float32 に丸められるぶんだけ解析値からずれる。
2×2×2 立方体に 3 mm の肉厚を付けた例では、
実測 0.07221672256582279 に対し解析値 `(2+2*0.003)**3 - 2**3` = 0.0722162159999975 で
**相対誤差 7.0e-6**。原因は `float32(1.003) = 1.00300002098083496`（座標の相対誤差 2.1e-8）が
3 乗で効くこと。bbox の絶対誤差自体は 1e-6 に十分収まる。

**Why:** `Mesh.vertices[].co` は float32 固定。`bmesh` 経由でも同じ。

**How to apply:** 仕様書やテストで体積を比較するときの相対許容誤差は **1e-4 程度**にする。
1e-6 を要求されたら、実装では到達不能なので仕様側の見直しを orchestrator に上げる。
bbox / 頂点座標の比較なら絶対誤差 1e-6 でよい。
