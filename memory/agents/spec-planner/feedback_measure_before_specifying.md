---
name: measure-before-specifying
description: 仕様書に数値・許容誤差・API の前提を書く前に、bpy wheel で実測して確かめる。推測で MUST を書かない
metadata:
  type: feedback
---

`bpy` / `bmesh` の挙動を **推測で仕様に書かない**。scratchpad でスクリプトを走らせて確かめ、確認済みの前提を仕様書の一節（「実装上の前提（実測で確認済み）」）としてまとめる。想定するコード形状は pyright strict にも通しておく。手順と得られた事実は [[knowledge-blender-geometry-api-facts]] にある。

**Why:** 過去に仕様側の数値が実装で達成不能だった例が実際にある。Solidify 仕様の AC-17 / AC-21 が体積の相対誤差 1e-6 を要求していたが、Blender のメッシュ座標が float32 のため到達不能で、テストが恒常的に赤になった（[[bpy-typing-and-precision-gotchas]]）。逆に 2026-08-14 の体積計測仕様では先に実測したことで、(a) 背景実行では `window_manager.clipboard` を読み戻せないので受け入れ基準を手動確認に落とすしかない、(b) 親パネルより先に子パネルを登録すると `RuntimeError` になるので `_CLASSES` の順序が MUST になる、(c) 開いたメッシュの `calc_volume()` が無意味な値を返すので watertight の門が必須、という 3 つの MUST を根拠つきで書けた。いずれも推測では逆に書きかねない項目だった。

**実測の範囲は「機能の挙動」だけでは足りない。** 体積計測仕様では事前に 15 項目を実測し、そのすべてが正しかった。にもかかわらず実装後に 5 件の受け入れ基準を訂正することになった。外れたのは実測しなかった領域、すなわち **受け入れ基準に書こうとしている assert そのもの** である: `bpy.ops` 経由で呼んだときに戻り値が届くのか（`ERROR` レベルの `report` があると `RuntimeError` になって届かない）、RNA のイントロスペクション経路（`Operator.bl_rna` には宣言したプロパティが無い）、`bpy.types` の基底クラスが持つ属性（`Panel` は `bl_options` を持たない）。詳細は [[knowledge-blender-geometry-api-facts]]。

**How to apply:**

- 仕様に許容誤差を書く前に、その値を実測する。float32 由来の誤差は「体積のような高次の量」で特に効く
- 「この API は〜できる/できない」と書く前に呼んでみる。特に背景実行でしか走らないテスト階層（tier 1 / tier 2）で使えるかどうか
- **AC を書くときは、その assert 文を 1 度実際に走らせる。** 「オペレータを呼んで戻り値を assert」「`bl_rna.properties` にプロパティ名があることを assert」「クラス属性を読む」といった検証コードの形は、機能の挙動と同じくらい外しやすい
- 実測結果は仕様書に表としてそのまま残す。実装者とテスト作成者が同じ前提から出発でき、「仕様の数値を疑わずに写して赤くなる」事故が消える
- 型の形状（スタブ由来の narrow が必要か、`# pyright: ignore` が必要か）も scratchpad の使い捨てディレクトリで確認する。`src/` にプローブを残さない

関連: [[user-expects-decisions-not-reopened]]
