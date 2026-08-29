# Solidify 機能 仕様書

- 対象リビジョン: `8ffe6e6` (make_shell 削除後、機能ゼロの状態) 以降
- 作成日: 2026-08-14
- ステータス: 実装待ち（未解決事項 OQ-1 / OQ-2 のみ要判断）

______________________________________________________________________

## 1. 概要

### 1.1 解決する問題

シリコーン造形用の樹脂型を作る過程では、面（サーフェス）に肉厚を与えて印刷可能なソリッドにする操作が繰り返し現れる。現状ユーザーは Blender 標準の Solidify モディファイアを手でスタックに積み、毎回 Thickness をメートル系の Blender 単位に頭の中で換算し、必要になったら Ctrl+A で適用している。この一連の操作を、アドオンのサイドバーから **mm 入力で・選択した全メッシュに一括で** 行えるようにする。

### 1.2 対象ユーザー

このアドオンの利用者（Blender の操作と 3D プリントの実務知識を持つ造形者）。Solidify モディファイアそのものの概念は既知である前提で UI を設計する。

### 1.3 ゴール

- G-1. 選択中の全メッシュオブジェクトに、固定名の Solidify モディファイアを **追加または更新** できる
- G-2. 肉厚を **mm で入力** でき、シーンの単位スケール設定に関わらず実寸として正しく反映される
- G-3. 肉厚を付ける向き（外側 / 内側）を切り替えられる
- G-4. アドオンが付けたモディファイアだけを、`bpy.ops` を経由せずにメッシュへ焼き込める（適用）
- G-5. 角部でも指定した mm が実寸として出る Even Thickness を切り替えられる

### 1.4 非ゴール (out of scope)

以下は本仕様の範囲外であり、実装してはならない (MUST NOT)。

- N-1. Solidify の全パラメータ（Rim、Complex モード、素材オフセット、頂点グループ、クリース等）の UI 露出
- N-2. モディファイアの並び替え、削除 UI、他モディファイアの管理
- N-3. 非一様スケールされたオブジェクトに対する肉厚の補正
- N-4. 適用結果のマニフォールド性検査・修復（後続の型分割機能の責務）
- N-5. 肉厚の自動決定（プリンタ解像度やシリコーン硬度からの推定）
- N-6. アンドゥスタックの独自管理（Blender の `REGISTER`/`UNDO` に委ねる）

______________________________________________________________________

## 2. 用語定義

| 用語 | 定義 |
| --- | --- |
| **マスター** | 型取りの対象となる元モデル。本機能は直接扱わないが、肉厚を付ける面はマスターから導出されることが多い |
| **肉厚 (thickness)** | サーフェスに与える壁の厚み。本仕様では常に **mm で入力** し、内部で Blender units へ換算する |
| **外側 / 内側** | 面法線の向いている側を「外側」と呼ぶ。外側に肉厚を付けると元の面が壁の**内面**になり、内側に付けると元の面が壁の**外面**になる |
| **Blender units (BU)** | Blender のシーン内座標の単位。既定では 1 BU = 1 m |
| **`scale_length`** | `scene.unit_settings.scale_length`。1 BU が何メートルに相当するかを表す係数。既定 1.0 |
| **Even Thickness** | Solidify の `use_even_offset`。頂点法線の平均方向に押し出す際、面の傾きぶんだけ距離を補正して、各面が指定した肉厚ぶん**平行移動**するようにする機能 |
| **固定名モディファイア** | 本アドオンが付与する `"Silicone Molding Solidify"` という名前の Solidify モディファイア。アドオンの管理対象を名前で一意に識別するための規約 |
| **適用 (apply)** | モディファイアの評価結果をベースメッシュに焼き込み、モディファイアをスタックから取り除くこと |
| **watertight** | すべての辺がちょうど 2 枚の面に共有されている状態。3D プリント可能性の必要条件 |
| **loose part** | 辺で連結されていない独立した部分。閉じた面に肉厚を付けると外殻と内殻の 2 パーツになる |
| **マルチユーザーメッシュ** | 1 つのメッシュデータブロックを複数オブジェクトが共有している状態 (`mesh.users > 1`) |

以下の造形ドメイン用語は本機能では扱わない（後続機能の語彙）: 分割面、パーティングライン、抜き勾配、湯口、エア抜き、インターロック、収縮代。

______________________________________________________________________

## 3. 要求仕様

### 3.1 機能要件

**設定（プロパティ）**

- FR-1. `Scene.silicone_molding` に肉厚を mm で保持するプロパティ `solidify_thickness_mm` を持たせる (MUST)。既定値 3.0、最小値 `MIN_THICKNESS_MM` (= 1e-3)、ソフト上限 50.0、表示精度は小数 2 桁
- FR-2. `solidify_thickness_mm` に `unit="LENGTH"` を設定してはならない (MUST NOT)。設定するとシーンの `unit_settings.length_unit` に従って表示単位が変わり、「常に mm で入力する」という FR-1 の要件と衝突する
- FR-3. `Scene.silicone_molding` に方向反転フラグ `solidify_flip` を持たせる (MUST)。既定値は `False`（＝外側）
- FR-3a. `Scene.silicone_molding` に均一化フラグ `solidify_even_thickness` を持たせる (MUST)。既存の挙動を維持するため既定値は `True`

**単位換算**

- FR-4. mm から Blender units への換算は `mm / 1000 / scale_length` とする (MUST)。`scale_length` は `scene.unit_settings.scale_length` の値
- FR-5. 換算関数はシーンにもコンテキストにも依存してはならない (MUST NOT)。`scale_length` は呼び出し側が数値として渡す

**モディファイアの付与・更新**

- FR-6. 選択中の **全メッシュオブジェクト** に対して処理する (MUST)。アクティブオブジェクトのみを対象にしてはならない
- FR-7. 対象オブジェクトに固定名 `"Silicone Molding Solidify"` の Solidify モディファイアが無ければ新規追加し、あれば設定を上書きする (MUST)。同一オブジェクトに 2 つ以上作ってはならない
- FR-8. 設定するプロパティは `thickness` / `offset` / `use_even_offset` の 3 つのみとする (MUST)。それ以外は Blender の既定値のまま（`solidify_mode = "EXTRUDE"`、`use_rim = True` 等）に委ねる
- FR-9. `use_even_offset` は `solidify_even_thickness` と同じ値にする (MUST)。真なら角部でも指定 mm が実寸として出る
- FR-10. `offset` は `solidify_flip` が偽なら `+1.0`（外側）、真なら `-1.0`（内側）とする (MUST)
- FR-11. 同じ操作を繰り返した場合、モディファイアの個数と設定値は 1 回目と同一でなければならない (MUST、冪等性)

**適用**

- FR-12. 適用は `bpy.ops`（`bpy.ops.object.modifier_apply` を含む）を使わずに実現する (MUST)。depsgraph 評価と `bpy.data.meshes.new_from_object` で行う
- FR-13. 適用対象は固定名のモディファイアのみとする (MUST)。ユーザーが手動で積んだ他のモディファイアは、名前が違えば Solidify であっても焼き込んではならない
- FR-14. 適用時は自分以外のモディファイアを一時的に無効化し、そのモディファイアだけがベースメッシュに掛かった結果を得る (MUST)。これは Blender 標準の「特定のモディファイアを適用する」意味論と一致させるため
- FR-15. 一時的に変更したフラグは、例外が発生した場合でも必ず元に戻す (MUST)
- FR-16. 適用後、置き換え前のメッシュデータブロックを削除し、新しいメッシュに元の名前を引き継がせる (MUST)。orphan データブロックとメッシュ名の喪失を防ぐため
- FR-17. マルチユーザーメッシュには適用してはならない (MUST NOT)。他オブジェクトへ意図しない影響が及ぶため、エラーとして扱う

**UI とオペレータ**

- FR-18. サイドバーの Processing パネルに、3 プロパティと 2 ボタン（Solidify / Apply）を配置する (MUST)。`solidify_flip` と `solidify_even_thickness` は同じ行に配置する
- FR-19. オペレータは自前の `bpy.props` を持たず、設定は `context.scene.silicone_molding` から読む (MUST)
- FR-20. 適用オペレータは、対象となるモディファイアを持つオブジェクトが選択に 1 つも無いとき `poll` が偽を返し、ボタンがグレーアウトする (MUST)
- FR-21. 両オペレータの `bl_options` は `{"REGISTER", "UNDO"}` とする (MUST)
- FR-22. 処理できたオブジェクト数を `INFO` レベルで報告する (MUST)。個別の失敗は `WARNING` に落とし、残りの処理は続行する

### 3.2 非機能要件

- NFR-1. `core/` 配下は `bpy.ops` に依存してはならない (MUST NOT)。`core/units.py` はさらに `bpy` 自体にも依存しない
- NFR-2. Blender 5.1 で利用可能な API のみを使う (MUST)。5.2 で追加された API は使ってはならない
- NFR-3. `pyright` strict を通ること (MUST)。`bpy.types.Object.modifiers.new` の戻り値型は `Modifier` なので、`SolidifyModifier` として扱うには実行時の型絞り込みが必要になる
- NFR-4. `bl_idname`、`Scene.silicone_molding` 配下のプロパティ名、パネルの `bl_idname` / `bl_category` は公開 API として扱い、決定後は互換性を意識する (MUST)
- NFR-5. 性能要件は設けない（該当なし）。モディファイアの追加・評価はいずれも Blender 本体のコストが支配的であり、本機能が追加するオーバーヘッドは無視できる

______________________________________________________________________

## 4. アーキテクチャ概要

### 4.1 レイヤ配置

| レイヤ | 追加・変更するファイル | 責務 |
| --- | --- | --- |
| `core/` | `units.py`（新規） | mm ↔ BU の換算。純粋な数値計算 |
| `core/` | `solidify.py`（新規） | モディファイアの検索・付与・更新・焼き込み。`bpy` のデータ API のみ使用 |
| `core/` | `__init__.py`（変更） | `__all__` に公開面を集約 |
| `operators/` | `solidify.py`（新規） | 2 つのオペレータ。選択の走査、単位換算、エラーの `self.report` への変換 |
| `operators/` | `__init__.py`（変更） | オペレータクラスの再エクスポート |
| `ui/` | `properties.py`（変更） | `solidify_thickness_mm` / `solidify_flip` / `solidify_even_thickness` |
| `ui/` | `panel.py`（変更） | プロパティとボタンの描画 |
| ルート | `__init__.py`（変更） | `_CLASSES` へのオペレータ登録 |

### 4.2 データフロー

1. ユーザーがサイドバーで mm 値、向き、均一化の有無を入力 → `Scene.silicone_molding` に保存される
2. ユーザーが **Solidify** ボタンを押す → オペレータが `context.scene.unit_settings.scale_length` を読み、`mm_to_units` で BU に換算
3. オペレータが `context.selected_objects` のうち `type == "MESH"` のものを順に走査し、各オブジェクトに `ensure_solidify` を呼ぶ
4. ユーザーが **Apply** ボタンを押す → オペレータが `context.evaluated_depsgraph_get()` を取得し、各オブジェクトに `apply_solidify` を呼ぶ
5. `apply_solidify` が depsgraph 評価でメッシュを確定させ、オブジェクトのデータを差し替える

### 4.3 モジュール境界（並列実装のための分担）

2 名（2 エージェント）で並列実装できるよう、**ファイル単位で排他的に** 分割する。同じファイルを両モジュールが触ることはない。

| | モジュール A（core 層） | モジュール B（Blender 統合層） |
| --- | --- | --- |
| 実装 | `src/silicone_molding/core/units.py`<br>`src/silicone_molding/core/solidify.py`<br>`src/silicone_molding/core/__init__.py` | `src/silicone_molding/operators/solidify.py`<br>`src/silicone_molding/operators/__init__.py`<br>`src/silicone_molding/ui/properties.py`<br>`src/silicone_molding/ui/panel.py`<br>`src/silicone_molding/__init__.py` |
| テスト | `tests/silicone_molding/core/test_units.py`<br>`tests/silicone_molding/core/test_solidify.py` | `tests/silicone_molding/operators/test_solidify.py`<br>`tests/silicone_molding/test_register.py`（追記）<br>`tests/blender/run.py`（追記） |
| 依存方向 | B に依存しない | A の §5.1 / §5.2 のシグネチャにのみ依存 |

- 契約は本仕様書の §5 が唯一の真実とする。A と B は互いの実装を読まずに、§5 だけを見て書ける状態でなければならない
- B は A の完成を待たずに書き始められるが、B のテストは A がマージされるまで通らない（import 不能）。§10 の PR 分割を参照
- `tests/silicone_molding/core/` と `tests/silicone_molding/operators/` のディレクトリは新規作成となる。両者が同じ `conftest.py` を編集しないよう、共有 fixture が必要なら **A が** `tests/conftest.py` を編集する（B は編集しない）

______________________________________________________________________

## 5. インターフェース仕様

型は Python の型注釈で記す。識別子・docstring は英語で書く既存規約に従う。

### 5.1 `core/units.py`

**`mm_to_units(mm: float, scale_length: float) -> float`**

- 目的: ミリメートル値を Blender units に換算する
- 引数
  - `mm`: 換算元の長さ（ミリメートル）
  - `scale_length`: 1 BU が相当するメートル数。呼び出し側が `scene.unit_settings.scale_length` から渡す
- 戻り値: Blender units での長さ
- 定義: 戻り値は `mm / 1000 / scale_length` に等しい
- 事前条件: `scale_length` は 0 より大きい（Blender の unit settings は正の値のみを許容する）
- 事後条件: `mm` が非負なら戻り値も非負。`scale_length` を固定したとき `mm` に対して線形
- 不変条件: 副作用を持たない純粋関数。`bpy` を import しない (MUST NOT)
- 例外: 送出しない。`scale_length` に対するゼロ除算ガードを書いてはならない (MUST NOT) — 到達しないシナリオへの防御的コードは本プロジェクトの設計原則に反する

### 5.2 `core/solidify.py`

このモジュールは `bpy` のデータ API のみを使う。`bpy.ops` は使わない (MUST NOT)。

**`MODIFIER_NAME: Final = "Silicone Molding Solidify"`**

- アドオンが管理する Solidify モディファイアの名前。この文字列は既存の `.blend` に保存された内容と結び付くため、公開 API として扱う（変更するとユーザーのファイル上のモディファイアが管理対象から外れる）

**`MIN_THICKNESS_MM: Final = 1e-3`**

- UI で受け付ける肉厚の下限（ミリメートル、＝ 1 µm）。`ui/properties.py` の `min` に流用するために `core` から公開する。単位が mm であるため `ensure_solidify`（引数は BU）では検証に使えない。§5.2 の関数はこの定数を参照しない

**`find_solidify(obj: bpy.types.Object) -> bpy.types.SolidifyModifier | None`**

- 目的: `obj` が持つアドオン管理下の Solidify モディファイアを返す
- 引数: `obj` — 任意のオブジェクト（メッシュでなくてもよい）
- 戻り値: `obj.modifiers` に `MODIFIER_NAME` の名前を持つモディファイアが存在し、それが SOLIDIFY 型であればそのモディファイア。存在しない、または型が異なる場合は `None`
- 事前条件: なし
- 事後条件: `obj` を変更しない（読み取りのみ）
- 例外: 送出しない
- 実装上の注記: 型の判定には `isinstance(mod, bpy.types.SolidifyModifier)` を用いると、実行時の検証と pyright の型絞り込みを同時に満たせる

**`ensure_solidify(obj: bpy.types.Object, thickness: float, *, flip: bool = False, even_thickness: bool = True) -> bpy.types.SolidifyModifier`**

- 目的: `obj` にアドオン管理下の Solidify モディファイアが存在することを保証し、設定を反映する
- 引数
  - `obj`: 対象オブジェクト。メッシュオブジェクトであること
  - `thickness`: 肉厚（**Blender units**）。mm からの換算は呼び出し側の責務
  - `flip`: 真なら内側、偽なら外側に肉厚を付ける
  - `even_thickness`: 真なら角部を補正して均一な厚みにする
- 戻り値: 追加または更新されたモディファイア
- 振る舞い
  1. `find_solidify(obj)` が `None` なら `obj.modifiers.new(MODIFIER_NAME, "SOLIDIFY")` で新規作成する。`None` でなければそれを再利用する
  2. `thickness` を `thickness` 引数の値に設定する
  3. `offset` を `-1.0`（`flip` が真）または `+1.0`（偽）に設定する
  4. `use_even_offset` を `even_thickness` に設定する
- 事前条件: `obj.data` がメッシュであること。呼び出し側（オペレータ層）が保証する
- 事後条件
  - `find_solidify(obj)` は戻り値と同一のモディファイアを返す
  - `MODIFIER_NAME` を名前に持つモディファイアはちょうど 1 つ（Blender が名前の一意性を保証する）
  - モディファイアはスタックの末尾に追加される（新規作成時）。既存の場合はスタック内の位置を変えない
  - 上記 3 プロパティ以外は変更しない
- 不変条件: 同じ引数で 2 回呼んでも結果は等しい（冪等）
- 例外: 送出しない。`thickness` の値域検証は行わない（値域は UI レイヤの `FloatProperty` の `min` が担保する）

**`apply_solidify(obj: bpy.types.Object, depsgraph: bpy.types.Depsgraph) -> None`**

- 目的: アドオン管理下の Solidify モディファイアだけを `obj` のメッシュへ焼き込み、モディファイアを取り除く
- 引数
  - `obj`: 対象オブジェクト。**view layer に存在している必要がある**（`evaluated_get` の前提）
  - `depsgraph`: 評価に用いる depsgraph。オペレータ層は `context.evaluated_depsgraph_get()` を渡す
- 戻り値: なし
- 振る舞い（この順序で行う）
  1. `find_solidify(obj)` が `None` なら `ValueError` を送出する
  2. `obj.data.users > 1` なら `ValueError` を送出する（マルチユーザーメッシュ）
  3. 対象モディファイア以外のすべてのモディファイアについて `show_viewport` の値を退避し、`False` に設定する
  4. `depsgraph.update()` → `obj.evaluated_get(depsgraph)` → `bpy.data.meshes.new_from_object(...)` で新しいメッシュデータブロックを得る
  5. `try` / `finally` により、3 で退避した `show_viewport` を **必ず** 元の値へ戻す
  6. 対象モディファイアを `obj.modifiers.remove(...)` で取り除く
  7. 旧メッシュの名前を控え、`obj.data` を新しいメッシュに差し替える
  8. 旧メッシュを `bpy.data.meshes.remove(...)` で削除する
  9. 新しいメッシュを控えておいた名前にリネームする（旧メッシュ削除後に行うことで `.001` の付与を避ける）
- 事前条件
  - `obj` が view layer 内にあること。背景実行・tier 1 テストでも同様で、オブジェクトをシーンコレクションに link する必要がある
  - `obj.data` がメッシュであること
- 事後条件（正常終了時）
  - `find_solidify(obj)` が `None` を返す
  - `obj.data` は新しいメッシュデータブロックで、名前は元と同一
  - 元のメッシュデータブロックは `bpy.data.meshes` に残らない
  - 対象以外のモディファイアは個数・順序・`show_viewport` ともに呼び出し前と同一
- 事後条件（例外送出時）
  - `obj` とその子データは一切変更されていない（1 と 2 の検査は副作用を起こす前に行う）
- 例外
  - `ValueError`: 対象モディファイアが存在しない場合
  - `ValueError`: `obj.data.users > 1` の場合
- 実装上の注記
  - 「自分以外を一時的に無効化する」のは、Blender の `modifier_apply` が持つ「そのモディファイアだけがベースメッシュに掛かった結果を焼き込む」意味論に合わせるため。無効化しないと、スタック上流・下流の他モディファイアの結果まで焼き込まれる
  - `new_from_object` は評価済みオブジェクトを受け取るため `depsgraph` 引数は渡さない。`preserve_all_data_layers` は既定 (`False`) のままとする。UV と材質インデックスは保持されるが、全カスタムデータレイヤの保持は保証しない（§8 の限界事項）
  - 結果はオブジェクトのローカル空間で、オブジェクトの変換行列は焼き込まれない

### 5.3 `core/__init__.py`

上記の公開面を再エクスポートし、`__all__` に集約する (MUST)。少なくとも `MIN_THICKNESS_MM`、`MODIFIER_NAME`、`apply_solidify`、`ensure_solidify`、`find_solidify`、`mm_to_units` を含む。

### 5.4 `operators/solidify.py`

**`OperatorReturn`**

削除された `operators/shell.py` にあった型エイリアスを同じ形で踏襲する (MUST)。すなわち `set[Literal["RUNNING_MODAL", "CANCELLED", "FINISHED", "PASS_THROUGH", "INTERFACE"]]` を自前で綴る。理由は元のコメントどおりで、Blender の `OperatorReturnItems` がスタブにしか存在せず実行時に import できないため。原文は `git show 8ffe6e6^:src/silicone_molding/operators/shell.py` で参照できる。

**`SILMOLD_OT_solidify`**

| 項目 | 値 |
| --- | --- |
| `bl_idname` | `silicone_molding.solidify` |
| `bl_label` | `Solidify` |
| `bl_options` | `{"REGISTER", "UNDO"}` |

- `poll`: `context.selected_objects` に `type == "MESH"` のオブジェクトが 1 つ以上あるとき真
- `execute`
  1. `props = context.scene.silicone_molding`
  2. `thickness = mm_to_units(props.solidify_thickness_mm, context.scene.unit_settings.scale_length)`
  3. `context.selected_objects` のうち `type == "MESH"` のものを順に走査し、各オブジェクトに `ensure_solidify(obj, thickness, flip=props.solidify_flip, even_thickness=props.solidify_even_thickness)` を呼ぶ
  4. 処理件数を `self.report({"INFO"}, ...)` で報告し `{"FINISHED"}` を返す
- 例外処理: `ensure_solidify` は例外を送出しないため、`try` / `except` を書いてはならない (MUST NOT)。`poll` が 1 件以上のメッシュを保証するので `{"CANCELLED"}` の分岐も持たない（§11 OQ-2 を参照）

**`SILMOLD_OT_apply_solidify`**

| 項目 | 値 |
| --- | --- |
| `bl_idname` | `silicone_molding.apply_solidify` |
| `bl_label` | `Apply` |
| `bl_options` | `{"REGISTER", "UNDO"}` |

- `poll`: `context.selected_objects` のうち `type == "MESH"` かつ `find_solidify(obj)` が `None` でないものが 1 つ以上あるとき真
- `execute`
  1. `depsgraph = context.evaluated_depsgraph_get()`
  2. `context.selected_objects` のうち `type == "MESH"` のものを順に走査し、各オブジェクトに `apply_solidify(obj, depsgraph)` を呼ぶ
  3. `ValueError` はオブジェクト単位で捕捉し、`self.report({"WARNING"}, ...)` に落として **処理を続行する** (MUST)。メッセージにはオブジェクト名を含める
  4. 成功件数が 0 なら `{"CANCELLED"}`、1 以上なら成功件数を `{"INFO"}` で報告して `{"FINISHED"}`
- 報告メッセージの文言は仕様として固定しない。テストで完全一致を検証してはならない (MUST NOT)

### 5.5 `ui/properties.py`

`SiliconeMoldingProperties` に 3 つのプロパティを追加する。

| プロパティ名 | 型 | 引数 |
| --- | --- | --- |
| `solidify_thickness_mm` | `FloatProperty` | `name="Thickness (mm)"`, `default=3.0`, `min=MIN_THICKNESS_MM`, `soft_max=50.0`, `precision=2` |
| `solidify_flip` | `BoolProperty` | `name="Flip Direction"`, `default=False` |
| `solidify_even_thickness` | `BoolProperty` | `name="Even Thickness"`, `default=True` |

- `unit="LENGTH"` を付けてはならない (MUST NOT、FR-2)
- `description` は付けてよい (MAY)。文言は公開 API ではない
- プロパティ**名** は公開 API（FR/NFR-4）。既存 `.blend` から参照されうる

### 5.6 `ui/panel.py`

`SILMOLD_PT_processing.draw` に以下を配置する。

1. `solidify_thickness_mm` のプロパティ行
2. `solidify_flip` と `solidify_even_thickness` を同じプロパティ行
3. `SILMOLD_OT_solidify` のボタン（アイコン `MOD_SOLIDIFY`）
4. `SILMOLD_OT_apply_solidify` のボタン

3 と 4 を同一の行にまとめるか縦に並べるかは実装者の裁量とする (MAY)。

### 5.7 `src/silicone_molding/__init__.py`

`_CLASSES` に 2 つのオペレータを追加する。登録順は「`SiliconeMoldingProperties` → オペレータ 2 種 → `SILMOLD_PT_main`」とする (MUST)。パネルはオペレータの `bl_idname` を参照するため、パネルより前に登録されている必要がある。

______________________________________________________________________

## 6. データモデル

### 6.1 パラメータ

| 名前 | 保持場所 | 単位 | 既定 | 値域 | 検証場所 |
| --- | --- | --- | --- | --- | --- |
| `solidify_thickness_mm` | `Scene.silicone_molding` | mm | 3.0 | `[1e-3, ∞)`、ソフト上限 50.0 | `FloatProperty` の `min`（RNA がクランプ） |
| `solidify_flip` | `Scene.silicone_molding` | — | `False` | `{False, True}` | 型により自明 |
| `solidify_even_thickness` | `Scene.silicone_molding` | — | `True` | `{False, True}` | 型により自明 |
| `thickness`（`ensure_solidify` 引数） | 引数 | BU | — | 制約なし | 検証しない（§5.2） |
| `scale_length` | `Scene.unit_settings` | m / BU | 1.0 | 正の実数 | Blender 本体 |

### 6.2 ジオメトリ

- 入力: 任意のメッシュデータブロック。閉じている必要も、多様体である必要もない
- 出力: Solidify モディファイア（未適用）または、それを焼き込んだ新しいメッシュデータブロック
- 座標系: オブジェクトのローカル空間。オブジェクトの変換行列は関与しない
- 単位の妥当性（3D プリント前提）: 樹脂型の壁厚は実用上おおむね **2〜10 mm**。既定値 3.0 mm はこの範囲の下寄りにあたり、FDM の一般的なノズル径 0.4 mm に対して十分な壁を確保できる。ソフト上限 50 mm は UI のスライダー範囲であり、それ以上の入力を禁止するものではない

### 6.3 バリデーション規則

- V-1. 肉厚は `MIN_THICKNESS_MM` 以上（RNA が保証）
- V-2. 適用対象はシングルユーザーメッシュのみ（`apply_solidify` が検証）
- V-3. 適用対象は固定名モディファイアを持つこと（`apply_solidify` が検証、`poll` が事前にフィルタ）
- V-4. その他の入力検証は行わない。特に、メッシュの多様体性・面の有無・自己交差は検証しない（§8 参照）

______________________________________________________________________

## 7. 振る舞い詳細

### S-1: 閉じたメッシュに外側の肉厚を付ける（基本シナリオ）

- **Given** 原点に 2×2×2 の立方体オブジェクトが 1 つあり、それだけが選択されている
- **And** `scale_length` が 1.0、`solidify_thickness_mm` が 3.0、`solidify_flip` が偽、`solidify_even_thickness` が真である
- **When** ユーザーが **Solidify** ボタンを押す
- **Then** 立方体に `"Silicone Molding Solidify"` という名前の Solidify モディファイアが 1 つ追加される
- **And** その `thickness` は 0.003、`offset` は `+1.0`、`use_even_offset` は `True` である
- **And** ビューポート上の立方体の外形は 2.006×2.006×2.006 になる（元の面が壁の内面になる）
- **And** `{"INFO"}` で 1 件処理した旨が報告される

### S-2: 設定を変えて再実行する

- **Given** S-1 の終了状態
- **When** ユーザーが `solidify_thickness_mm` を 5.0、`solidify_even_thickness` を偽に変えて再び **Solidify** を押す
- **Then** モディファイアは新規追加されず、既存のものの `thickness` が 0.005、`use_even_offset` が `False` に更新される
- **And** モディファイアの総数は 1 のまま、スタック内の位置も変わらない

### S-3: 内側に肉厚を付ける

- **Given** S-1 と同じ初期状態で `solidify_flip` が真
- **When** ユーザーが **Solidify** を押す
- **Then** モディファイアの `offset` は `-1.0` になる
- **And** ビューポート上の外形は 2×2×2 のまま変わらず、内側に壁ができる

### S-4: 適用する

- **Given** S-1 の終了状態（モディファイア未適用、メッシュはシングルユーザー）
- **When** ユーザーが **Apply** ボタンを押す
- **Then** モディファイアはスタックから消える
- **And** ベースメッシュ自体が頂点 16・辺 24・面 12 の二重殻になる
- **And** メッシュデータブロックの名前は適用前と同一で、旧データブロックは `bpy.data.meshes` に残らない
- **And** `{"INFO"}` で 1 件適用した旨が報告される
- **And** **Apply** ボタンはグレーアウトする（対象モディファイアが無くなったため）

### S-5: 複数オブジェクトを一括処理する

- **Given** メッシュ 3 つとカメラ 1 つが選択されている
- **When** ユーザーが **Solidify** を押す
- **Then** メッシュ 3 つすべてにモディファイアが付き、カメラは何も変化しない
- **And** `{"INFO"}` は 3 件と報告する

### S-6: 一部だけ失敗する適用

- **Given** メッシュ A（シングルユーザー、対象モディファイアあり）とメッシュ B（マルチユーザー、対象モディファイアあり）が選択されている
- **When** ユーザーが **Apply** を押す
- **Then** A には適用され、B には `{"WARNING"}` が報告される
- **And** B のメッシュとモディファイアは変更されていない
- **And** 戻り値は `{"FINISHED"}`（成功件数 1 ≥ 1）で、`{"INFO"}` は 1 件と報告する

### S-7: 単位スケールが mm のシーン

- **Given** `scale_length` が 0.001（1 BU = 1 mm のシーン設定）
- **And** `solidify_thickness_mm` が 3.0
- **When** ユーザーが **Solidify** を押す
- **Then** モディファイアの `thickness` は 3.0（BU）になる
- **And** ワールド上の実寸は 3 mm であり、`scale_length` が 1.0 のときと同じ物理的厚みになる

______________________________________________________________________

## 8. エッジケースとエラー処理

### 8.1 選択とオブジェクト種別

| 状況 | 期待される振る舞い |
| --- | --- |
| 選択が 0 個 | 両オペレータの `poll` が偽。ボタンはグレーアウトし、押せない。API から直接呼ぶと Blender が `RuntimeError` を送出する（アドオン側では扱わない） |
| 選択にメッシュが 1 つも無い（カメラ・ライトのみ） | 同上。`poll` が偽 |
| 選択にメッシュと非メッシュが混在 | メッシュのみ処理し、非メッシュは**黙って**スキップする。警告を出してはならない (MUST NOT) — 選択にライトやカメラが混ざるのは日常的な操作であり、警告が騒がしくなるため |
| アクティブオブジェクトが選択に含まれない | 影響しない。本機能はアクティブオブジェクトを参照しない |
| ライブラリリンクされたオブジェクト | 本仕様では扱わない。Blender 側が書き込みを拒否した場合の挙動は未定義（型型取りワークフローの想定外） |

### 8.2 ジオメトリの退化・破綻

| 状況 | 期待される振る舞い |
| --- | --- |
| 面が 0 のメッシュ（頂点・辺のみ、または完全に空） | 例外にしてはならない (MUST NOT)。モディファイアは追加され、評価結果は空のままとなる。適用も成功し、面 0 のメッシュが得られる。Blender 本体の Solidify と同じ挙動であり、アドオンが独自に拒否する理由がない |
| 開いたメッシュ（境界辺を持つ） | Solidify の既定 `use_rim=True` により縁が塞がれ、閉じたソリッドになる。これは肉厚付けの通常のユースケースであり、エラーではない |
| 非多様体入力（3 枚以上の面が共有する辺など） | 検証しない。Solidify が出す結果をそのまま受け入れる。結果が印刷可能かの判断は後続工程（型分割・検査機能）の責務 |
| 自己交差する入力 | 検証しない。肉厚が局所的な曲率半径を超えると出力も自己交差するが、本仕様では検出も警告もしない |
| ゼロ面積の面を含む | 検証しない。Solidify は法線が定まらない面を無視するか退化した結果を出す。いずれも Blender 本体の挙動に委ねる |
| 極端に小さい肉厚（1 µm 付近） | 受け付ける。`MIN_THICKNESS_MM` は下限であり、これ未満は RNA がクランプする |
| 極端に大きい肉厚（オブジェクトの寸法を超える） | 受け付ける。`soft_max` はスライダーの範囲にすぎず、入力の禁止ではない。結果が自己交差しても警告しない |

### 8.3 モディファイアスタックの状態

| 状況 | 期待される振る舞い |
| --- | --- |
| ユーザーが手動で付けた **別名の** Solidify がある | 無視する。`ensure_solidify` は固定名のものだけを見るため、アドオンのモディファイアが別に追加され、肉厚は二重に掛かる（ビューポート上の見た目に反映される）。適用時は別名のものが一時無効化されるため、焼き込まれるのはアドオン管理下の 1 つだけ。この結果は仕様どおりであり、警告は出さない |
| 固定名だが SOLIDIFY 型でないモディファイアがある | `find_solidify` は `None` を返す。`ensure_solidify` は `obj.modifiers.new(MODIFIER_NAME, "SOLIDIFY")` を呼び、Blender が名前の衝突を回避して `"Silicone Molding Solidify.001"` を割り当てる。その結果 `find_solidify` は以後も `None` を返し続け、**Solidify を押すたびにモディファイアが増える**。これは実質的に到達不能な状況（ユーザーが意図的に同名を付けた場合のみ）であり、本仕様では防御しない。§11 OQ-3 を参照 |
| 対象モディファイアの前後に他のモディファイアがある | 適用時、他はすべて一時無効化される。結果として「ベースメッシュ + Solidify のみ」が焼き込まれる。これは Blender が「1 番目でないモディファイアを適用した」際に出す警告と同じ意味論であり、上流モディファイアの結果は反映されない |
| 対象モディファイアが元から `show_viewport = False` | 適用処理はそのまま進む。無効化されているのは他のモディファイアのみで、対象自身のフラグは触らない。ただし depsgraph 評価では対象も無効なので、**元のメッシュがそのまま焼き込まれ、モディファイアだけが消える**。この挙動は Blender 本体と同じ（本体も非表示モディファイアを適用すると同様に振る舞う） |

### 8.4 データブロックと反復操作

| 状況 | 期待される振る舞い |
| --- | --- |
| マルチユーザーメッシュ（`obj.data.users > 1`） | `apply_solidify` が `ValueError` を送出する。オペレータは `{"WARNING"}` に落として続行する。オブジェクトは一切変更されない |
| 同じ選択で **Solidify** を 2 回連続 | 冪等。モディファイアの個数・設定値ともに 1 回目と同一（FR-11） |
| 同じ選択で **Apply** を 2 回連続 | 1 回目で成功し、2 回目は対象モディファイアが無いため `poll` が偽になりボタンが押せない。API から直接 2 回呼んだ場合、2 回目は `poll` が偽で Blender が `RuntimeError` を送出する。`apply_solidify` を直接 2 回呼んだ場合は `ValueError` |
| 選択内に同じメッシュデータを共有する 2 オブジェクト | 両方とも `obj.data.users > 1` なので 2 件とも `{"WARNING"}` になり、成功件数 0 で `{"CANCELLED"}` |
| 適用対象のメッシュに他のオブジェクトからの参照が無い | 旧メッシュは削除される。orphan は残らない |

### 8.5 変換行列とスケール

| 状況 | 期待される振る舞い |
| --- | --- |
| オブジェクトに一様スケールが掛かっている | 肉厚はローカル空間で適用されるため、ワールド上の実寸はスケール倍される。例: スケール 2 のオブジェクトに 3 mm を指定すると、ワールド上は 6 mm の壁になる |
| オブジェクトに **非一様** スケールが掛かっている | 上記に加えて、壁厚が方向によって変わる。本仕様では補正も警告もしない (N-3)。ユーザーがスケールを適用 (Ctrl+A) してから使うことを前提とする。§11 OQ-4 を参照 |
| オブジェクトに回転・移動がある | 影響しない。肉厚は法線方向のローカル量であり、剛体変換で不変 |

### 8.6 既知の限界事項

- L-1. `preserve_all_data_layers=False` のため、標準的な UV・材質インデックスは保持されるが、カスタムデータレイヤの完全な保持は保証しない
- L-2. シェイプキーは適用によって失われる。これは depsgraph 評価による焼き込み全般の性質であり、Blender 本体の `modifier_apply` も同様（本体はエラーにするが、本仕様では検査しない）
- L-3. エディットモード中の挙動は未定義。§11 OQ-1 を参照

______________________________________________________________________

## 9. 受け入れ基準

各項目に検証階層を明記する。tier 1 = `just test`（PyPI `bpy` wheel 上の pytest）、tier 2 = `just blender-test`（実 Blender）。

**golden mesh は作らない（該当なし）。** Blender 自身のモディファイア出力をピン留めすると Blender のバージョン差で CI が落ちるため、検証はすべて解析的に導ける不変量で行う。この判断は `/testing-strategy` の「golden mesh で正確な形状を固定する」原則に対する意図的な例外であり、モディファイア出力を扱うすべての機能に適用する。

### 9.1 単位換算（tier 1、モジュール A）

- [ ] AC-1. `mm_to_units(3.0, 1.0)` が 0.003 を返す（相対誤差 1e-12 以内。IEEE 754 では厳密一致するが、テストは近似比較で書く）
- [ ] AC-2. `mm_to_units(3.0, 0.001)` が 3.0 を返す（相対誤差 1e-12 以内）
- [ ] AC-3. `mm_to_units(0.0, 1.0)` が 0.0 を返す
- [ ] AC-4. `core/units.py` が `bpy` を import していない（モジュールのソースまたは `sys.modules` への非依存で確認できる。あるいはレビューでの目視確認でもよい）

### 9.2 モディファイアの付与（tier 1、モジュール A）

- [ ] AC-5. モディファイアを持たないメッシュオブジェクトに `ensure_solidify(obj, 0.003)` を呼ぶと、`obj.modifiers` の長さが 1 になり、その名前が `MODIFIER_NAME`、型が `"SOLIDIFY"` である
- [ ] AC-6. 同オブジェクトに対して `thickness` を変えて 2 回目を呼ぶと、`obj.modifiers` の長さは 1 のままで、`thickness` が新しい値に更新されている
- [ ] AC-7. `flip=False` のとき `offset == 1.0`、`flip=True` のとき `offset == -1.0`
- [ ] AC-8. `even_thickness=True` のとき `use_even_offset` が `True`、`even_thickness=False` のとき `False`
- [ ] AC-9. `solidify_mode` が `"EXTRUDE"`、`use_rim` が `True`（Blender 既定を変更していないことの確認。既定値が変わった場合に気付くためのピン）
- [ ] AC-10. `find_solidify` は、モディファイアが無いオブジェクトに対して `None` を返す
- [ ] AC-11. `find_solidify` は、`ensure_solidify` 後のオブジェクトに対して同一のモディファイアを返す

### 9.3 適用後のジオメトリ（tier 1、モジュール A）

前提: 原点に配置した 2×2×2 の立方体（各軸 -1..1）を持つオブジェクトをシーンコレクションに link し、`ensure_solidify(obj, 0.003, flip=False)` の後 `apply_solidify(obj, bpy.context.evaluated_depsgraph_get())` を呼ぶ。不変量は `tests/_helpers.mesh_invariants` で取得する。

- [ ] AC-12. `vertex_count == 16`
- [ ] AC-13. `edge_count == 24`
- [ ] AC-14. `face_count == 12`
- [ ] AC-15. `is_watertight` が真（`boundary_edge_count == 0` かつ `non_manifold_edge_count == 0`）
- [ ] AC-16. `loose_part_count == 2`（外殻と内殻）
- [ ] AC-17. `volume` が `(2 + 2 * 0.003) ** 3 - 2 ** 3` に等しい（= 2.006³ − 8 ≈ 0.072216216、相対誤差 1e-6 以内）
- [ ] AC-18. `bbox_min` が (-1.003, -1.003, -1.003)、`bbox_max` が (1.003, 1.003, 1.003)（絶対誤差 1e-6 以内）
- [ ] AC-19. AC-18 は `use_even_offset = True` に依存する。`False` の場合は角部が平均法線方向に `thickness` だけしか動かず、bbox は ±(1 + 0.003/√3) ≈ ±1.001732 に痩せる。この差が出ることを利用して、Even Thickness が効いていることを AC-18 が担保している（この項目自体は単独のテストにしなくてよい。AC-18 の意図をテスト名またはコメントに残す）
- [ ] AC-20. `flip=True` で同じ手順を踏むと、`bbox_min` が (-1, -1, -1)、`bbox_max` が (1, 1, 1) のまま変わらない
- [ ] AC-21. AC-20 の場合の `volume` が `2 ** 3 - (2 - 2 * 0.003) ** 3` に等しい（= 8 − 1.994³ ≈ 0.071784216、相対誤差 1e-6 以内）

### 9.4 適用の副作用（tier 1、モジュール A）

- [ ] AC-22. 適用後、`find_solidify(obj)` が `None` を返す
- [ ] AC-23. 適用後、`obj.data.name` が適用前のメッシュ名と等しい（`.001` などのサフィックスが付いていない）
- [ ] AC-24. 適用後、適用前のメッシュデータブロックが `bpy.data.meshes` に存在しない
- [ ] AC-25. 対象以外のモディファイア（例: Subdivision Surface を 1 つ追加しておく）が、適用後も存在し `show_viewport` が元の値のままである
- [ ] AC-26. AC-25 の状況で焼き込まれたジオメトリが、他のモディファイアの効果を **含まない**（頂点数が AC-12 と同じ 16 であることで確認できる）
- [ ] AC-27. モディファイアを持たないオブジェクトに `apply_solidify` を呼ぶと `ValueError` が送出される（メッセージの完全一致は検証しない）
- [ ] AC-28. マルチユーザーメッシュ（同じメッシュを 2 オブジェクトが共有）に `apply_solidify` を呼ぶと `ValueError` が送出され、モディファイアもメッシュも変更されていない
- [ ] AC-29. 面が 0 のメッシュに対して `ensure_solidify` → `apply_solidify` が例外なく完了し、結果の面数が 0 である

### 9.5 オペレータ（tier 1、モジュール B）

- [ ] AC-30. 選択が 0 個のとき、両オペレータの `poll` が偽
- [ ] AC-31. メッシュが選択されているとき `SILMOLD_OT_solidify.poll` が真、`SILMOLD_OT_apply_solidify.poll` が偽（まだモディファイアが無いため）
- [ ] AC-32. `bpy.ops.silicone_molding.solidify()` の実行後、`SILMOLD_OT_apply_solidify.poll` が真になる
- [ ] AC-33. メッシュ 2 つと非メッシュ 1 つを選択して solidify を実行すると、メッシュ 2 つだけにモディファイアが付く
- [ ] AC-34. `scale_length = 0.001` のシーンで `solidify_thickness_mm = 3.0` のまま実行すると、モディファイアの `thickness` が 3.0 になる（`scale_length = 1.0` なら 0.003）
- [ ] AC-35. `solidify_flip = True` で実行すると `offset == -1.0` になる
- [ ] AC-35a. `solidify_even_thickness = False` で実行すると `use_even_offset` が `False` になる
- [ ] AC-36. 適用オペレータをマルチユーザーメッシュのみの選択で実行すると `{"CANCELLED"}` を返す
- [ ] AC-37. 適用オペレータをシングルユーザー 1 件・マルチユーザー 1 件の選択で実行すると `{"FINISHED"}` を返し、シングルユーザー側にだけ適用されている

### 9.6 公開 API 契約（tier 1、モジュール B、`api_contract` マーカー）

これらは振る舞いテストではなく契約のピン留めである旨をコメントに明記する。

- [ ] AC-38. `SILMOLD_OT_solidify.bl_idname == "silicone_molding.solidify"`
- [ ] AC-39. `SILMOLD_OT_apply_solidify.bl_idname == "silicone_molding.apply_solidify"`
- [ ] AC-40. 登録後、`Scene.silicone_molding` に `solidify_thickness_mm`、`solidify_flip`、`solidify_even_thickness` が存在する。`solidify_even_thickness` の既定値は `True`
- [ ] AC-41. `MODIFIER_NAME == "Silicone Molding Solidify"`（既存 `.blend` との結び付きを守るため）

### 9.7 実 Blender での統合（tier 2、モジュール B、`tests/blender/run.py` に追記）

`bmesh` を import せず、`mesh.vertices` / `mesh.polygons` から直接算出できる範囲に留める（tier 2 は third-party 非依存の方針）。

- [ ] AC-42. `bpy.ops.silicone_molding.solidify` と `bpy.ops.silicone_molding.apply_solidify` が実 Blender 上で解決できる
- [ ] AC-43. 2×2×2 の立方体に対して solidify → apply を通すと、頂点数 16・面数 12 になる
- [ ] AC-44. AC-43 の結果メッシュの座標の最小・最大が各軸で ±1.003 になる（絶対誤差 1e-5 以内）

### 9.8 品質ゲート

- [ ] AC-45. `just run`（format → test → type）が通る
- [ ] AC-46. `just blender-test` が通る

______________________________________________________________________

## 10. 実装計画

### 10.1 フェーズ

| フェーズ | 内容 | 成果物 | 依存 |
| --- | --- | --- | --- |
| P1 | モジュール A の実装とテスト | `core/units.py`、`core/solidify.py`、`core/__init__.py`、`tests/silicone_molding/core/test_units.py`、`tests/silicone_molding/core/test_solidify.py` | なし |
| P2 | モジュール B の実装とテスト | `operators/solidify.py`、`operators/__init__.py`、`ui/properties.py`、`ui/panel.py`、`__init__.py`、`tests/silicone_molding/operators/test_solidify.py`、`tests/silicone_molding/test_register.py` 追記 | P1 のシグネチャ（本仕様 §5）。実行時には P1 の成果物 |
| P3 | tier 2 の統合チェック追記 | `tests/blender/run.py` | P1・P2 |
| P4 | ドキュメント | docstring、`CHANGELOG.md` の `## [Unreleased]` 更新 | P1〜P3 |

P1 と P2 は §4.3 の分担どおりファイルが排他なので **並列に着手できる**。P2 のテストは P1 がマージされるまで赤のままになる。

`CHANGELOG.md` の `## [Unreleased]` には、削除済みの **Make Shell** に関する記述がまだ残っている。P4 でこれを整理し、Solidify 機能の記述に差し替える (MUST)。

### 10.2 PR 分割案

| 案 | 構成 | 長所 | 短所 | 評価 |
| --- | --- | --- | --- | --- |
| **案 1（推奨）** | PR#1 = P1、PR#2 = P2 + P3 + P4 | レビュー単位が「純粋なジオメトリ層」と「Blender 統合層」で分かれ、それぞれ独立に読める。PR#1 は単体で CI が緑になる | PR#2 が PR#1 のマージ待ちになる（または PR#1 のブランチから分岐する必要がある） | ○ |
| 案 2 | 1 本の PR に全部 | マージ順の調整が不要。機能として意味のある最小単位で入る | 変更ファイル 10 本超。UI とジオメトリのレビュー観点が混ざる | △ |
| 案 3 | P1 / P2 / P3 / P4 を 4 本 | 各 PR が小さい | P2 単独では機能が使えず、P3・P4 の PR が細かすぎる。レビュー往復のコストが上回る | × |

**決定（2026-08-14, orchestrator）: 案 2 を採る。** `feature/20260814/solidify-modifier` 1 本に P1〜P4 をコミット分けで積み、PR は 1 本にする。P1 単体では機能として意味を成さず、レビュー観点も「肉厚を付ける」という 1 つの関心事に収まるため。

### 10.3 検証手順

1. P1 完了時 → `uv run pytest tests/silicone_molding/core -v` が緑（AC-1〜AC-29）
2. P2 完了時 → `just test` が緑（AC-30〜AC-41 を追加）
3. P3 完了時 → `just blender-test` が緑（AC-42〜AC-44）
4. 最終 → `just run` と `just blender-test`（AC-45・AC-46）
5. 任意 → `just dev` で実 Blender を起動し、S-1〜S-5 を手で確認する

______________________________________________________________________

## 11. 未解決事項

| ID | 内容 | 推奨案 | 判断者 / 期限 |
| --- | --- | --- | --- |
| ~~OQ-1~~ **決定済** | `SILMOLD_OT_apply_solidify.poll` にオブジェクトモード条件 (`context.mode == "OBJECT"`) を加えるか | **加える**。推奨案を採用（2026-08-14, orchestrator 判断）。両オペレータに適用する | 決定済 |
| ~~OQ-2~~ **決定済** | `SILMOLD_OT_solidify` に「1 件も処理できなければ `{"CANCELLED"}`」の分岐を持たせるか | **持たせない**。推奨案を採用（2026-08-14, orchestrator 判断）。§5.4 の記述どおり実装する | 決定済 |
| **OQ-3** | 固定名で SOLIDIFY 型でないモディファイアが既にある場合（§8.3）、`ensure_solidify` を呼ぶたびにモディファイアが増える。防御するか | **防御しない (SHOULD NOT)**。ユーザーが意図的に同名を付けた場合にのみ起きる。仕様として §8.3 に記録するに留める | 実装者 / 実装時に本仕様どおりで進めてよい |
| **OQ-4** | 非一様スケールされたオブジェクトに対して警告を出すか | 今回は **出さない**（N-3）。実務で問題が出た時点で再検討する。判断を保留するだけで、実装は不要 | ユーザー / 実際に使ってみてから |
| **OQ-5** | 適用後のメッシュに対する自己交差・非多様体の検査を、どの機能の責務にするか | 型分割機能または独立した「型の検査」機能の側に置く。本仕様では扱わない | 後続機能の仕様策定時 |

______________________________________________________________________

## 12. 将来の拡張余地

今回スコープ外だが、設計上ふさぐべきでない方向:

- E-1. **オフセット中心 (`offset = 0`)**。分割型で「面の両側に均等に肉厚を付ける」需要が出る可能性がある。`solidify_flip` を真偽値からモード列挙 (`OUTSIDE` / `INSIDE` / `CENTER`) に広げれば拡張できるが、プロパティ名が公開 API なので変更時は互換性の検討が要る
- E-2. **Complex モード (`solidify_mode = "NON_MANIFOLD"`)**。自己交差しやすい形状での品質改善に効く。§5.2 で `solidify_mode` を明示的に触らない設計にしてあるため、後から設定項目を足すだけで対応できる
- E-3. **High Quality Normals (`use_quality_normals`)**。複雑な形状で肉厚の均一性が上がる。今回は Blender 既定 (`False`) のまま
- E-4. **`preserve_all_data_layers=True` への切り替え**。材質スロットによる型パーツの区別を後続機能で使うようになったら再検討する（L-1）
- E-5. **モディファイアの一括削除 UI**。付けた肉厚を取り消す操作は現状 Blender 標準のモディファイアパネルに任せている
- E-6. **プリセット**。「シリコーン用 3 mm」「レジン用 5 mm」といった肉厚プリセット。実運用で値が固まってきたら検討する
