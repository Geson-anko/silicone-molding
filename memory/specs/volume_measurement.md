# 体積計測機能 / サイドバーのセクション分け 仕様書

- 対象リビジョン: `052d00e`（Solidify 機能マージ後）以降
- 作成日: 2026-08-14
- 改訂: 2026-08-14 — 計測の起動方式を「`draw()` ごとの常時再計算」から「**ボタンで 1 回計測 → 結果を Scene に保存 → 表示をクリックでコピー**」に変更（ユーザーによる設計変更）。改訂の影響範囲は §13 に要約
- ステータス: 実装待ち（未解決事項 OQ-1 〜 OQ-5 のみ要判断）
- ブランチ: `feature/20260814/volume-measurement`
- 関連仕様: [Solidify 機能](solidify.md)

______________________________________________________________________

## 1. 概要

本仕様は 2 つの変更を 1 つの単位として扱う。両者は「サイドバーの構造」を共有するため分離できない。

1. サイドバー「Silicone Molding」タブを **親パネル + 折りたたみ可能なサブパネル 2 つ** に再編する
2. サブパネル「Measurement」に新機能 **体積計測** を載せる

### 1.1 解決する問題

**(a) サイドバーが平坦である。** 現状 `SILMOLD_PT_main` に肉厚・方向反転・Solidify・Apply が一列に並んでいる。今後 分割面生成・湯口・エア抜き・インターロックといった機能が積まれると、関心の異なるコントロールが 1 枚のパネルに混在して探せなくなる。機能が 2 つに増えるこの時点でセクションを切り、以後の機能追加が「どのセクションに入るか」を先に決められる状態にする。

**(b) 注型量が分からない。** シリコーンや樹脂を計量するとき、ユーザーは「この型に何 mL 入るか」「この壁で樹脂が何 mL 必要か」を知りたい。現状これを得るには Blender 標準の統計オーバーレイ（頂点数・面数しか出ない）では足りず、サードパーティのアドオンか手計算に頼っている。造形の現場で使う単位は **mL（= cm³）** であり、計量カップとシリコーンの缶に書かれた単位と一致する。

### 1.2 対象ユーザー

このアドオンの利用者（Blender の操作と 3D プリントの実務知識を持つ造形者）。「閉じたメッシュでなければ体積が定義できない」という事実は既知である前提で UI を設計する（エラー文でその理由を教えることはしない）。

### 1.3 ゴール

- G-1. ボタン 1 つで、選択中の全メッシュオブジェクトの体積の **合計** を計測し、mL で表示する
- G-2. 計測される値が **モディファイア込み・ワールド実寸** であり、Solidify を掛けた壁の樹脂量がそのまま読める
- G-3. シーンの単位設定（`length_unit`）に関わらず常に mL で表示する（壁厚を mm 固定にしている既存方針と揃える）
- G-4. 体積が定義できない選択（境界辺・非多様体辺を持つメッシュを含む）では、数値を出さず **原因のオブジェクト名を含むエラー** を報告する
- G-5. 表示された数値を 1 クリックでクリップボードへコピーでき、スプレッドシートにそのまま貼れる
- G-6. サイドバーが「Measurement（計測）」「Processing（加工）」の 2 セクションに分かれ、それぞれ独立に折りたためる
- G-7. 既存の公開 API（`SILMOLD_PT_main` の `bl_idname` / `bl_category`、オペレータの `bl_idname`、`Scene.silicone_molding` の既存プロパティ名）を一切変えない
- G-8. 計測は **明示的な操作**（ボタン押下）でのみ走る。ビューポートの再描画が計測コストを払うことはない

### 1.4 非ゴール (out of scope)

以下は本仕様の範囲外であり、実装してはならない (MUST NOT)。

- N-1. 体積以外の計測（表面積、寸法、重心、断面積、質量）
- N-2. 表示単位の選択 UI（mm³ / mL / L / in³ の切り替え）。mL 固定とする
- N-3. 素材の比重を掛けた質量表示
- N-4. オブジェクトごとの内訳表示。合計値のみを出す
- N-5. **計測結果の自動無効化・自動再計測**。`depsgraph_update_post` などのハンドラ購読、選択変更の監視、タイマーによる更新はいずれも実装しない。結果はボタンを押した瞬間のスナップショットである（§8.5 L-1）
- N-6. 非多様体メッシュの自動修復、または体積の近似計算（凸包・ボクセル化などによる代替値の提示）
- N-7. メッシュ以外のオブジェクト（カーブ、テキスト、メタボール、サーフェス）の体積計測。`to_mesh()` は通るが、キャップ・ベベル・押し出しの解釈が別問題になるため対象外
- N-8. 実インスタンス（コレクションインスタンス、パーティクル、ジオメトリノードのインスタンス出力）の計上
- N-9. 3 つ目以降のサブパネルの新設。今回は Measurement と Processing の 2 つのみ
- N-10. 既存プロパティ・オペレータの改名
- N-11. 計測履歴（前回値との差分、複数スロットへの保存）

______________________________________________________________________

## 2. 用語定義

| 用語 | 定義 |
| --- | --- |
| **注型量** | 型のキャビティに流し込む材料の体積。造形の現場では mL（= cm³）で計量する |
| **watertight（閉じている）** | すべての辺がちょうど 2 枚の面に共有されている状態。本仕様ではこれを体積が定義できる唯一の条件として扱う |
| **境界辺 (boundary edge)** | 共有する面が 1 枚以下の辺。1 本でもあればメッシュは開いている |
| **非多様体辺 (non-manifold edge)** | 3 枚以上の面が共有する辺。内部に隔壁がある、または面が重なっている |
| **Blender units (BU)** | Blender のシーン内座標の単位。既定では 1 BU = 1 m |
| **BU³** | 体積の内部表現。ローカル空間・ワールド空間いずれも座標が BU なので体積は BU³ になる |
| **`scale_length`** | `scene.unit_settings.scale_length`。1 BU が何メートルに相当するかを表す係数。既定 1.0 |
| **mL（ミリリットル）** | 表示単位。1 mL = 1 cm³ であり、体積として完全に同一である。次元計算の文脈では cm³ と書き、ユーザーに見せる文脈では mL と書く |
| **ローカル空間 / ワールド空間** | メッシュの座標はローカル空間に格納され、`matrix_world` を掛けたものがワールド空間。実寸はワールド空間で決まる |
| **行列式 (determinant)** | `matrix_world` の線形部（3×3）の行列式。アフィン変換のもとで体積は `\|det\|` 倍される。負の行列式は鏡像（向きの反転）を意味する |
| **鏡像スケール** | いずれかの軸のスケールが負であること。面の向きが裏返り、符号付き体積の符号が反転する |
| **符号付き体積 (signed volume)** | 面法線の向きを考慮した体積。閉じたメッシュで法線が外向きなら正、内向きなら負 |
| **depsgraph 評価** | モディファイアやシェイプキーを適用した後の状態を得る操作。`obj.evaluated_get(depsgraph)` で評価済みオブジェクトを得る |
| **一時メッシュ** | `Object.to_mesh()` が返すメッシュ。オブジェクトが所有し `bpy.data.meshes` には登録されず、`to_mesh_clear()` で解放される |
| **スナップショット** | 計測ボタンを押した瞬間の結果。以後シーンが変わっても自動更新されない（§8.5 L-1） |
| **未計測 (not measured)** | 保存された結果が無い状態。`.blend` を新規に開いた直後、および計測が失敗した直後 |
| **サブパネル** | `bl_parent_id` に親パネルの `bl_idname` を指定したパネル。親の中に折りたたみ可能なセクションとして描画される |
| **固定名モディファイア** | Solidify 仕様で定義した `"Silicone Molding Solidify"`。本仕様は名前を参照しない（すべてのモディファイアの評価結果を測る） |

以下の造形ドメイン用語は本機能では扱わない（後続機能の語彙）: 分割面、パーティングライン、抜き勾配、湯口、エア抜き、インターロック、収縮代。

______________________________________________________________________

## 3. 要求仕様

### 3.1 機能要件 — パネル構造

- FR-1. `SILMOLD_PT_main` を親パネルとして残し、その `bl_idname`（`"SILMOLD_PT_main"`）と `bl_category`（`"Silicone Molding"`）を変更してはならない (MUST NOT)。既存ユーザーの UI 状態・キーマップから参照される公開 API である
- FR-2. `SILMOLD_PT_main.draw` は layout に何も追加してはならない (MUST NOT)。ヘッダーのみのパネルとする。`draw` メソッド自体は残す (MUST) — Blender は `draw` を持たないパネルの登録を拒否するため
- FR-3. 子パネルを 2 つ新設する (MUST)。`bl_parent_id` は両方 `"SILMOLD_PT_main"` とする

| クラス名 | `bl_idname` | `bl_label` | 内容 |
| --- | --- | --- | --- |
| `SILMOLD_PT_measurement` | `SILMOLD_PT_measurement` | `Measurement` | 計測ボタンと結果行（新規） |
| `SILMOLD_PT_processing` | `SILMOLD_PT_processing` | `Processing` | 壁厚 / 方向反転 / Solidify / Apply（既存からの移設） |

- FR-4. サブパネルの表示順は `bl_order` で明示する (MUST)。`SILMOLD_PT_measurement.bl_order = 0`、`SILMOLD_PT_processing.bl_order = 1`。登録順（`_CLASSES` のタプル順）に依存させてはならない (MUST NOT) — 順序が `_CLASSES` の並べ替えで暗黙に壊れるのを防ぐため
- FR-5. サブパネルには `bl_space_type` と `bl_region_type` を明示する (MUST)。`bl_category` は定義しない (SHOULD NOT) — 子パネルは親のカテゴリに従うため、書くと真実の出所が 2 つになる
- FR-6. サブパネルの `bl_options` に `"DEFAULT_CLOSED"` を含めない (MUST NOT)。2 セクションとも既定で開いた状態にする
- FR-7. サブパネルに `poll` を定義してはならない (MUST NOT)。編集モードでもパネルは表示され、ボタンは各オペレータの `poll` によりグレーアウトする
- FR-8. 登録順は「親パネル → 子パネル」でなければならない (MUST)。逆順だと Blender が `RuntimeError`（`parent 'SILMOLD_PT_main' ... not found`）を送出し、アドオン全体が有効化できなくなる
- FR-9. 既存のプロパティ行 2 つとボタン 2 つは、内容・順序・アイコンを変えずに `SILMOLD_PT_processing.draw` へ移設する (MUST)。この移設で Solidify 機能の振る舞いが変わってはならない

### 3.2 機能要件 — 測定対象と評価方法

- FR-10. 測定対象は `context.selected_objects` のうち `type == "MESH"` のものすべてとする (MUST)。アクティブオブジェクトのみを対象にしてはならない
- FR-11. メッシュ以外のオブジェクトは黙ってスキップする (MUST)。警告を出してはならない (MUST NOT) — 選択にライトやカメラが混ざるのは日常的な操作であり、Solidify の既存方針（solidify 仕様 §8.1）と揃える
- FR-12. 同じメッシュデータブロックを共有する複数オブジェクトは、**それぞれ独立に** 計上する (MUST)。オブジェクトごとに `matrix_world` が異なりうるため、実際に必要な材料量は個数分になる
- FR-13. 測定は depsgraph 評価後のメッシュに対して行う (MUST)。モディファイアの効果（Solidify を含む）が反映される
- FR-14. 「測るのはビューポートに評価された状態」を不変条件とする (MUST)。`show_viewport = False` のモディファイアは反映されない。これは仕様であり、バグとして扱わない
- FR-15. 一時メッシュの取得は `Object.to_mesh()` / `Object.to_mesh_clear()` で行う (MUST)。`bpy.data.meshes.new_from_object` を使ってはならない (MUST NOT) — データブロックを生成する必要が無く、解放漏れが `.blend` に残るリスクを負うだけである
- FR-16. `to_mesh()` と `to_mesh_clear()` は同一の評価済みオブジェクトに対して呼び、`to_mesh_clear()` は例外が発生した場合でも必ず実行する (MUST、`try` / `finally`)
- FR-17. ワールド実寸は `ローカル体積 × abs(matrix_world の 3×3 部分の行列式)` で求める (MUST)。非一様スケール・鏡像スケールのいずれでも正の値になること
- FR-18. 符号付き体積を使ってはならない (MUST NOT)。`BMesh.calc_volume()` を既定（`signed=False`）で呼び、絶対値を得る
- FR-19. 体積を返す条件は「すべての辺が共有面数ちょうど 2」とする (MUST)。判定基準は solidify 仕様の `is_watertight`（`tests/_helpers.MeshInvariants.is_watertight`）と同一で、境界辺 0 かつ非多様体辺 0 に等しい
- FR-20. 判定は評価後のメッシュに対して行う (MUST)。ベースメッシュが開いていても Solidify の Rim で閉じるなら watertight として扱う
- FR-21. 辺を 1 本も持たないメッシュ（頂点 0 のメッシュを含む）は、判定条件を空虚に満たすため watertight とし、体積 0 を返す (MUST)。特別扱いを書いてはならない (MUST NOT) — 数学的に一貫しており、防御的コードは本プロジェクトの設計原則に反する
- FR-22. `Depsgraph.update()` を呼んではならない (MUST NOT)。`context.evaluated_depsgraph_get()` が必要な評価を済ませている
- FR-23. `context.evaluated_depsgraph_get()` は 1 回の計測で **1 回だけ** 呼び、全オブジェクトで共有する (MUST)。この呼び出しは評価済みデータブロックへの既存の参照を無効化するため、ループ内で呼ぶと直前に得た一時メッシュが壊れる

### 3.3 機能要件 — 計測の起動と結果の保存

- FR-24. 計測は専用のオペレータ（ボタン）で起動する (MUST)。ボタン 1 回の押下で 1 回だけ計測する
- FR-25. `Panel.draw` の中で depsgraph 評価・`to_mesh()`・体積計算のいずれも行ってはならない (MUST NOT)。`draw` は保存された結果を読んで整形するだけとする (MUST)
- FR-26. 結果は `Scene.silicone_molding` に **2 つのプロパティ** として保存する (MUST)

| プロパティ名 | 型 | 意味 |
| --- | --- | --- |
| `volume_ml` | `FloatProperty` | 直近の計測で得た合計体積（mL）。`volume_measured` が偽のとき内容は未定義 |
| `volume_measured` | `BoolProperty` | 真なら `volume_ml` が直近の計測結果を保持している。偽なら未計測 |

- FR-27. 保存する値は **mL** とする (MUST)。BU³ で保存してはならない (MUST NOT) — 計測後に `scale_length` が変更されると、BU³ 保存では表示値が過去の計測と食い違う。mL で保存すればスナップショットが完全に凍結される
- FR-28. 整形済みの文字列を `Scene` に保存してはならない (MUST NOT)。データは数値として持ち、表示整形は UI 層で行う
- FR-29. `volume_ml` に `unit="VOLUME"` を設定してはならない (MUST NOT)。設定するとシーンの単位設定に従って表示単位が変わり、「常に mL」という FR-38 と衝突する（solidify 仕様 FR-2 と同じ理由）
- FR-30. 計測オペレータの `bl_options` は `{"REGISTER", "UNDO"}` とする (MUST)。シーンのプロパティを書き換えるため、アンドゥで前の結果へ戻せなければならない
- FR-31. 計測オペレータの `poll` は「選択に `type == "MESH"` のオブジェクトが 1 つ以上あること」とする (MUST)。モード条件を加えてはならない (MUST NOT) — 計測はシーンのジオメトリを一切変更しない読み取り操作であり、編集モードでも正しく動くことを実測で確認している（§5.11）
- FR-32. 選択に watertight でないメッシュが 1 つ以上あるとき、計測オペレータは `self.report({"ERROR"}, ...)` で報告し `{"CANCELLED"}` を返す (MUST)。数値を保存してはならない (MUST NOT)。部分的な合計を出してはならない (MUST NOT)
- FR-33. FR-32 の失敗時、`volume_measured` を偽に戻す (MUST)。前回の結果を残してはならない (MUST NOT) — 失敗したのに古い数値が見えていると、それが今の選択の値だと誤読される
- FR-34. FR-32 のエラーメッセージには原因のオブジェクト名を含める (MUST)。名前の列挙には上限を設ける (MUST)。先頭 3 件までを挙げ、残りがあれば件数を添える。ステータスバーは 1 行しかないため、上限が無いとメッセージが読めなくなる
- FR-35. 計測成功時は `self.report({"INFO"}, ...)` で結果を報告する (MUST)。文言は仕様として固定しない
- FR-36. 計測結果を自動的に無効化してはならない (MUST NOT)。選択変更・ジオメトリ変更・モディファイア変更を監視するハンドラを登録してはならない (MUST NOT、N-5)。値の鮮度はユーザーがボタンを押し直すことで担保する
- FR-37. 「選択にメッシュが 0 個」の分岐を `execute` に書いてはならない (MUST NOT)。`poll` が保証するため到達しない

### 3.4 機能要件 — 単位換算と表示

- FR-38. 表示単位は mL 固定とする (MUST)。`scene.unit_settings.length_unit` を参照してはならない (MUST NOT)
- FR-39. BU³ から mL への換算は `volume * (scale_length * 100) ** 3` とする (MUST)
- FR-40. 換算関数はシーンにもコンテキストにも依存してはならない (MUST NOT)。`scale_length` は呼び出し側が数値として渡す
- FR-41. 合計は BU³ で行い、mL への換算は最後に 1 回だけ行う (MUST)
- FR-42. 表示は小数 2 桁固定とする (MUST)。指数表記を使ってはならない (MUST NOT)。桁区切り（カンマ）を入れてはならない (MUST NOT) — スプレッドシートへの貼り付けで数値として解釈されなくなるため

### 3.5 機能要件 — UI とコピー

- FR-43. Measurement サブパネルは「計測ボタン」→「結果行」の順に描画する (MUST)
- FR-44. 結果行は 2 列とし、左に単位を含むラベル（推奨: `Volume (mL)`）、右に値を描画する (MUST)。値の文字列に単位を含めてはならない (MUST NOT)
- FR-45. `volume_measured` が偽のとき、値の位置に無効値を表す固定文字列（`--`）をラベルとして描画する (MUST)。コピー用ボタンを描画してはならない (MUST NOT) — コピーする値が無い
- FR-46. `volume_measured` が真のとき、値は `emboss=False` のオペレータボタンのテキストとして描画する (MUST)。`layout.label` はクリックできないため、値をクリック可能にする唯一の方法である
- FR-47. コピー用オペレータは `StringProperty` を 1 つだけ持つ (MUST)。値は `layout.operator()` の戻り値（`OperatorProperties`）への代入で渡す
- FR-48. 表示に使う文字列とコピーする文字列は **同一のローカル変数** から供給する (MUST)。書式化を 2 度行ってはならない (MUST NOT) — 「コピーされた値 = 表示された値」を構成上の不変条件にするため
- FR-49. コピー用オペレータの `bl_options` に `"UNDO"` を含めてはならない (MUST NOT)。シーンを一切変更しないため、アンドゥステップを積むのは誤りである
- FR-50. コピー用オペレータの `bl_options` は `{"REGISTER", "INTERNAL"}` とする (MUST)。`REGISTER` は `self.report` を Info エディタに出してコピー成功のフィードバックにするため、`INTERNAL` は値を伴わない F3 検索からの呼び出しが無意味であるため
- FR-51. コピー先は `context.window_manager.clipboard` とする (MUST)
- FR-52. コピー用オペレータには `bl_description` を設定する (MUST)。ボタンのテキストが数値なので、ホバー時のツールチップが「クリックするとコピーされる」ことを伝える唯一の手段である

### 3.6 非機能要件

- NFR-1. `core/` 配下は `bpy.ops` に依存してはならない (MUST NOT)。`core/units.py` はさらに `bpy` 自体にも依存しない
- NFR-2. Blender 5.1 で利用可能な API のみを使う (MUST)。5.2 で追加された API は使ってはならない。本仕様が用いる `Object.to_mesh` / `to_mesh_clear` / `BMesh.calc_volume` / `Panel.bl_parent_id` / `Panel.bl_order` / `WindowManager.clipboard` はいずれも 5.1 以前から存在する
- NFR-3. `pyright` strict を通ること (MUST)。§5.11 に、想定コード形状が strict で 0 エラーになることを実測で確認した記録がある
- NFR-4. `bl_idname`、`Scene.silicone_molding` 配下のプロパティ名、パネルの `bl_idname` / `bl_category` は公開 API として扱う (MUST)。本仕様で新設する `volume_ml` / `volume_measured` / `SILMOLD_PT_measurement` / `SILMOLD_PT_processing` / 2 つの `bl_idname` はいずれも決定後は互換性を意識する。パネルの `bl_idname` を含める理由は、開閉状態が `.blend` の画面データにその id で保存されるため
- NFR-5. 性能要件は設けない（該当なし）。計算量は「選択メッシュの評価後の辺数と面数の合計」に比例するが、**ボタン押下 1 回あたり 1 度しか走らない**。ビューポートの再描画は保存済みの float を読むだけで、計測コストを払わない（FR-25）。この性質があるため、キャッシュ機構を投機的に実装する必要がない
- NFR-6. 体積の数値精度: Blender のメッシュ座標は float32 であり、体積は座標誤差が 3 乗で効くため解析値と相対 1e-5 程度ずれる。テストの許容誤差は §9 の各項目で個別に指定する。`Scene` に保存する `FloatProperty` は Blender 内部で float32 に丸められるため、これも許容誤差の見積もりに織り込む

______________________________________________________________________

## 4. アーキテクチャ概要

### 4.1 レイヤ配置

| レイヤ | 追加・変更するファイル | 責務 |
| --- | --- | --- |
| `core/` | `units.py`（変更） | `cubic_units_to_ml` と `format_ml` を追記。`bpy` 非依存を維持 |
| `core/` | `volume.py`（新規） | 評価済みメッシュの watertight 判定とワールド体積、および選択全体の集計。`bpy` + `bmesh` のデータ API のみ |
| `core/` | `__init__.py`（変更） | `__all__` に公開面を追加 |
| `operators/` | `measure_volume.py`（新規） | 計測オペレータ。選択の走査、単位換算、結果の Scene への保存、エラーの `self.report` への変換 |
| `operators/` | `copy_value.py`（新規） | クリップボードへコピーする 1 オペレータ |
| `operators/` | `__init__.py`（変更） | オペレータクラスの再エクスポート |
| `ui/` | `properties.py`（変更） | `volume_ml` / `volume_measured` を追加 |
| `ui/` | `panel.py`（変更） | 親パネルの中身を空にし、サブパネル 2 つを新設。既存コントロールを Processing へ移設 |
| `ui/` | `__init__.py`（変更） | サブパネル 2 つを再エクスポート |
| ルート | `__init__.py`（変更） | `_CLASSES` にオペレータ 2 つとサブパネル 2 つを追加し、登録順のコメントを訂正 |
| `tests/fixtures/` | — | **該当なし**。golden mesh は作らない（§9 冒頭） |

### 4.2 データフロー

**計測（ボタン押下時）**

1. ユーザーが Measurement セクションの **Measure Volume** ボタンを押す
2. オペレータの `execute` が `context.evaluated_depsgraph_get()` を 1 回呼び、`context.selected_objects` と共に `total_volume` へ渡す
3. `total_volume` が各オブジェクトについて `world_volume` を呼ぶ
4. `world_volume` が `obj.evaluated_get(depsgraph)` → `to_mesh()` で一時メッシュを得て、`bmesh` に読み込み、辺の共有面数を検査する
   - 共有面数が 2 でない辺が 1 本でもあれば `None` を返す
   - そうでなければ `BMesh.calc_volume()`（ローカル BU³）に `abs(matrix_world.to_3x3().determinant())` を掛けて返す
   - いずれの経路でも `finally` で `BMesh.free()` と `to_mesh_clear()` を行う
5. `total_volume` が BU³ の合計、測定できたオブジェクト数、watertight でなかったオブジェクト名の並びを `VolumeSummary` として返す
6. `execute` が結果を 2 分岐で処理する
   - `non_watertight_names` が空でない → `volume_measured = False` にし、名前を含む `ERROR` を報告して `{"CANCELLED"}`
   - 空 → `cubic_units_to_ml` で mL に換算して `volume_ml` に保存し、`volume_measured = True` にして `INFO` を報告し `{"FINISHED"}`

**表示（リドローごと）**

7. `SILMOLD_PT_measurement.draw` が計測ボタンを描画する
8. `volume_measured` が偽なら、結果行の右に `--` のラベルを置いて終わる
9. 真なら `format_ml(volume_ml)` で文字列を 1 つ作り、それを `layout.operator(..., text=..., emboss=False)` のテキストと `OperatorProperties.value` の両方に渡す

**コピー（値のクリック時）**

10. `SILMOLD_OT_copy_value.execute` が `context.window_manager.clipboard` に文字列を代入し、`INFO` を報告する

### 4.3 モジュール境界（並列実装のための分担）

2 名（2 エージェント）で並列実装できるよう、**ファイル単位で排他的に** 分割する。同じファイルを両モジュールが触ることはない。

| | モジュール A（core 層） | モジュール B（Blender 統合層） |
| --- | --- | --- |
| 実装 | `src/silicone_molding/core/units.py`<br>`src/silicone_molding/core/volume.py`<br>`src/silicone_molding/core/__init__.py` | `src/silicone_molding/operators/measure_volume.py`<br>`src/silicone_molding/operators/copy_value.py`<br>`src/silicone_molding/operators/__init__.py`<br>`src/silicone_molding/ui/properties.py`<br>`src/silicone_molding/ui/panel.py`<br>`src/silicone_molding/ui/__init__.py`<br>`src/silicone_molding/__init__.py` |
| テスト | `tests/silicone_molding/core/test_units.py`（追記）<br>`tests/silicone_molding/core/test_volume.py`（新規） | `tests/silicone_molding/operators/test_measure_volume.py`（新規）<br>`tests/silicone_molding/operators/test_copy_value.py`（新規）<br>`tests/silicone_molding/ui/test_panel.py`（新規）<br>`tests/silicone_molding/test_register.py`（追記）<br>`tests/blender/run.py`（追記） |
| 依存方向 | B に依存しない | A の §5.1 / §5.2 のシグネチャにのみ依存 |

- 契約は本仕様書の §5 が唯一の真実とする。A と B は互いの実装を読まずに、§5 だけを見て書ける状態でなければならない
- B は A の完成を待たずに書き始められるが、B のテストは A がマージされるまで通らない（import 不能）。§10 の PR 分割を参照
- `tests/silicone_molding/ui/` は新規ディレクトリになる。プロジェクト規約どおり `__init__.py` は置かない
- テストモジュールの basename は `tests/` 全体で一意でなければならない（pytest の prepend import mode）。`test_volume.py`（core）と `test_measure_volume.py`（operators）は別名なので衝突しない。`operators/measure_volume.py` という名前を選んだのは、`core/volume.py` と同名を避けてこの制約を回避するためでもある
- 共有 fixture が必要になった場合、`tests/conftest.py` を編集するのは **A** とする（B は編集しない）。ただし本仕様の範囲では既存の `cube_object` / `make_object` / `empty_mesh` で足り、追加は不要と見込む

______________________________________________________________________

## 5. インターフェース仕様

型は Python の型注釈で記す。識別子・docstring は英語で書く既存規約に従う。

### 5.1 `core/units.py`（変更）

既存の `mm_to_units` は変更しない (MUST NOT)。モジュール docstring は現在「mm と Blender units の長さ換算」に限定した記述になっているため、体積換算と表示書式を含む内容へ更新する (MUST)。

**`cubic_units_to_ml(volume: float, scale_length: float) -> float`**

- 目的: 立方 Blender units で表された体積を mL に換算する
- 引数
  - `volume`: 換算元の体積（BU³）
  - `scale_length`: 1 BU が相当するメートル数。呼び出し側が `scene.unit_settings.scale_length` から渡す
- 戻り値: mL での体積（= cm³）
- 定義: 戻り値は `volume * (scale_length * 100.0) ** 3` に等しい。導出は「BU³ → m³ が `scale_length ** 3` 倍、m³ → cm³ が 10⁶ 倍」。cm³ と mL は同一量なので、この係数がそのまま mL への係数になる
- 事前条件: `scale_length` は 0 より大きい。Blender は `unit_settings.scale_length` を正の値にクランプする（0 を代入すると 1e-9 になることを実測済み）
- 事後条件: `volume` が非負なら戻り値も非負。`volume` に対して線形、`scale_length` に対して 3 次
- 不変条件: 副作用を持たない純粋関数。`bpy` を import しない (MUST NOT)
- 例外: 送出しない。`scale_length` に対するゼロ除算ガードやゼロ検査を書いてはならない (MUST NOT)

**`format_ml(volume_ml: float) -> str`**

- 目的: mL の体積を、画面表示とクリップボードコピーの両方で使う文字列に変換する
- 引数: `volume_ml` — mL での体積
- 戻り値: 小数点以下 2 桁に固定した十進表記。単位は含まない
- 定義: 戻り値は `f"{volume_ml:.2f}"` に等しい
- 事後条件
  - 指数表記を含まない（`1.2e9` は `"1200000000.00"` になる）
  - 桁区切りを含まない
  - 小数点以下は常に 2 桁
- 不変条件: 純粋関数。`bpy` を import しない (MUST NOT)
- 例外: 送出しない
- 設計判断: 表示の書式化は本来 UI の関心事だが、`core/units.py` に置く。理由は (a) この文字列が「表示される値」と「コピーされる値」を同時に定義する唯一の契約であり、tier 1 で検証できる場所に置く必要がある、(b) 単位系の約束（mL・小数 2 桁）を 1 ファイルに集約できる。代替案（`ui/panel.py` の private ヘルパ）は、唯一のユーザー可視な契約をテスト不能な場所に置くことになるため採らない
- 精度を設定可能にしてはならない (MUST NOT)

### 5.2 `core/volume.py`（新規）

このモジュールは `bpy` と `bmesh` のデータ API のみを使う。`bpy.ops` は使わない (MUST NOT)。

**import 順の制約（MUST）**

PyPI の `bpy` wheel は `bmesh` を bpy の C 初期化時に builtin モジュールとして登録するため、`import bpy` より先に `import bmesh` を書くと `ModuleNotFoundError` になる（実測確認済み）。isort は `bmesh` を `bpy` より前に並べるため、`tests/_helpers.py` と同じ形で `# isort: off` / `# isort: on` で囲み、`import bpy` を先に置く (MUST)。理由をコメントで残す (MUST)。本モジュールは `src/` 配下で初めて `bmesh` を import するファイルになる。

**「体積計算」と「watertight 判定」の分割に関する設計判断**

| 案 | 構成 | 長所 | 短所 | 評価 |
| --- | --- | --- | --- | --- |
| **案 1（採用）** | 1 関数 `world_volume(obj, depsgraph) -> float \| None`。判定と計算を 1 回の `BMesh` 生成で行い、判定に落ちたら `None` を返す | 一時メッシュと `BMesh` の生成が 1 回で済む。「体積が定義できない」を型で表現できるので、呼び出し側が判定を忘れられない。`to_mesh` / `to_mesh_clear` の対応も 1 箇所に閉じる | 「判定」だけを単体で呼べない | ○ |
| 案 2 | `is_watertight(mesh) -> bool` と `world_volume(mesh, matrix) -> float` を独立に公開し、呼び出し側が順に呼ぶ | 責務が名前に出る。判定を他機能から再利用できる | `BMesh` を 2 回作る。判定を呼ばずに体積を取れてしまい、開いたメッシュで無意味な数値が出る事故が起きうる。一時メッシュの寿命管理が呼び出し側に漏れる | × |
| 案 3 | `MeshMeasurement`（`is_watertight` と `volume` を持つ dataclass）を返す | 1 パスで両方得られる | `is_watertight` が偽のときの `volume` に意味が無く、「意味の無い値が入ったフィールド」を仕様に残すことになる。案 1 の `None` で同じ情報が表現できる | × |

案 2 の `is_watertight` は将来「型の検査」機能が必要とする可能性があるが、それは投機的な要求であり、本プロジェクトの「シンプルさを優先」原則に従って今は作らない。必要になった時点で `world_volume` から抽出すればよい（呼び出し側は `None` 判定のままで済むので、抽出は非破壊的な変更になる）。

なお `tests/_helpers.MeshInvariants.is_watertight` は境界辺数・非多様体辺数からテスト側で同じ判定を行っている。**判定基準が 2 箇所にあることになるが、統合してはならない (MUST NOT)** — `tests/_helpers.py` は「テストが期待値を独立に計算する」ための道具であり、実装と同じ関数を使うと検証にならない。

**`world_volume(obj: bpy.types.Object, depsgraph: bpy.types.Depsgraph) -> float | None`**

- 目的: `obj` の評価後メッシュのワールド空間体積を返す。体積が定義できない場合は `None` を返す
- 引数
  - `obj`: 対象オブジェクト。`type == "MESH"` であり、**view layer に存在している必要がある**（`evaluated_get` の前提）
  - `depsgraph`: 評価に用いる depsgraph。呼び出し側は `context.evaluated_depsgraph_get()` を渡す
- 戻り値
  - 評価後メッシュが watertight なら、ワールド空間での体積（BU³、非負）
  - watertight でなければ `None`
- 振る舞い（この順序で行う）
  1. `obj.evaluated_get(depsgraph)` で評価済みオブジェクトを得る
  2. `to_mesh()` で一時メッシュを得る
  3. 新しい `BMesh` に読み込み、すべての辺について共有面数を調べる。2 でない辺が 1 本でもあれば `None` を返す
  4. `BMesh.calc_volume()`（既定の `signed=False`）でローカル体積を得る
  5. `abs(obj.matrix_world.to_3x3().determinant())` を掛けて返す
  6. 3 の早期 return を含むすべての経路で、`finally` により `BMesh.free()` と 評価済みオブジェクトの `to_mesh_clear()` を行う
- 事前条件
  - `obj.type == "MESH"`。呼び出し側（`total_volume`）が保証する。カメラ等に対して `to_mesh()` を呼ぶと Blender が `RuntimeError`（`Object does not have geometry data`）を送出する
  - `obj` が view layer 内にあること
- 事後条件
  - `obj` とそのメッシュデータブロックを変更しない（読み取りのみ）
  - `bpy.data.meshes` の内容が呼び出し前と同一である（一時メッシュはデータブロックにならない）
  - 戻り値が `float` のとき非負
  - 剛体変換（回転・移動）に対して戻り値は不変
  - 一様スケール `s` を掛けると戻り値は `s ** 3` 倍になる
- 例外: 事前条件を満たす限り送出しない
- 実装上の注記
  - **ワールド体積を「ローカル体積 × |det|」で求める理由**: アフィン変換のもとで体積は行列式の絶対値倍になるという厳密な性質を使う。`BMesh.transform(matrix_world)` で頂点を動かしてから測る代替案と比べ、頂点数に比例する演算が不要で、数値誤差も小さい（実測: 鏡像スケールの立方体で transform 方式が 192.00000000000546、det 方式が 191.99999999999997、解析値 192）
  - **3×3 に落とす理由**: 体積スケールは線形部だけで決まる。`matrix_world` はアフィンなので 4×4 の行列式も同値だが、線形部を明示したほうが意図が読める
  - **`signed=False` を使う理由**: 鏡像スケールでは面の向きが裏返り符号付き体積が負になる。絶対値を取ることで符号で破綻しない。Solidify を掛けた 2 パーツ（外殻 + 内殻）では、内殻の法線が内向きなので符号付き体積が「外殻 − 内殻 = 壁の体積」になり、これが求めたい値そのものである
  - **`to_mesh()` を 2 回続けて呼ぶと 1 回目の参照が無効化される**（実測: `ReferenceError: StructRNA of type Mesh has been removed`）。一時メッシュへの参照を関数の外へ持ち出してはならない (MUST NOT)
  - `to_mesh()` を呼んでいない状態で `to_mesh_clear()` を呼んでもエラーにならない（実測確認済み）ため、`finally` に無条件で置いて差し支えない

**`VolumeSummary`**

`@dataclass(frozen=True)` とする (MUST)。フィールドは以下の 3 つのみ。

| フィールド | 型 | 意味 |
| --- | --- | --- |
| `volume` | `float` | 測定できたオブジェクトのワールド体積の合計（BU³）。測定対象が 0 件なら 0.0 |
| `measured_count` | `int` | 体積を測定できたオブジェクトの数 |
| `non_watertight_names` | `tuple[str, ...]` | watertight でなかったオブジェクトの名前。入力の反復順を保つ |

派生プロパティ（`is_valid` 等）を追加してはならない (MUST NOT) — オペレータの 2 分岐は `non_watertight_names` が空かどうかだけで決まり、追加の抽象は要らない。`measured_count` は成功時の `INFO` メッセージと、tier 1 のテストが「非メッシュを黙ってスキップしたこと」を確認するために使う。

**`total_volume(objects: Iterable[bpy.types.Object], depsgraph: bpy.types.Depsgraph) -> VolumeSummary`**

- 目的: 複数オブジェクトの体積を集計し、呼び出し側が判断に必要な情報をすべて 1 つの値として返す
- 引数
  - `objects`: 走査するオブジェクト。**メッシュ以外が混ざっていてよい**。呼び出し側は `context.selected_objects or ()` をそのまま渡せる
  - `depsgraph`: 全オブジェクトで共有する depsgraph
- 戻り値: `VolumeSummary`
- 振る舞い
  1. `objects` を順に走査する
  2. `obj.type != "MESH"` のものは黙ってスキップする（`measured_count` にも `non_watertight_names` にも数えない）
  3. `world_volume(obj, depsgraph)` が `None` なら `obj.name` を `non_watertight_names` に積む
  4. `None` でなければ `volume` に加算し `measured_count` を 1 増やす
- 事前条件: `objects` の各要素が view layer 内にあること
- 事後条件
  - `measured_count` は `objects` 中のメッシュオブジェクト数から `len(non_watertight_names)` を引いた値に等しい
  - `objects` が空、またはメッシュを含まないとき、`VolumeSummary(0.0, 0, ())` に等しい
  - オブジェクトを一切変更しない
  - 同一の引数で 2 回呼ぶと等しい結果を返す（シーンが変わらない限り冪等）
- 例外: 事前条件を満たす限り送出しない
- 設計判断: **メッシュ以外のフィルタを core 側に置く理由** — 呼び出し側にフィルタを持たせると、`operators/solidify.py` の `_selected_meshes` と同じ 3 行が 2 箇所目に増える。core が「体積を持つのはメッシュオブジェクトだけ」という定義を所有するほうが契約として明快である。既存 `_selected_meshes` との統合は今回行わない（§11 OQ-4）

**エラーを呼び出し側へ伝える方式の設計判断**

| 案 | 方式 | 長所 | 短所 | 評価 |
| --- | --- | --- | --- | --- |
| **案 1（採用）** | 結果オブジェクト（`VolumeSummary`）を返す | 原因オブジェクト名を **複数まとめて** 運べる。上限付きの列挙メッセージ（FR-34）を組むには、これが必要である。`measured_count` も同時に運べるので成功時の報告に使える。「測れなかった」は日常的な状態であって例外的事象ではない | 呼び出し側が分岐を書く（2 分岐で済む） | ○ |
| 案 2 | 最初の非 watertight オブジェクトで `ValueError` を送出する | 既存 `apply_solidify` と例外の使い方が揃う。core がメッセージを所有する既存規約（`memory/agents/code-quality-reviewer/knowledge_error_message_ownership.md`）にも沿う | 最初の 1 件で止まるため、他の原因オブジェクトが分からない。ユーザーは 1 つ直して押し直すたびに次の 1 件を知ることになる | × |
| 案 3 | `float` を返し、測れないときは `NaN` | 分岐が 1 つで済む | オブジェクト名を運べず、`Scene` に `NaN` が保存される危険がある | × |

**メッセージの所有者について**: このプロジェクトには「例外メッセージは `core` が自己完結して持ち、`operators` は `str(exc)` をそのまま `report` する」という規約がある。本仕様の `core` は **例外を送出しない** ため、その規約の適用対象外である。名前の列挙と上限（FR-34）はユーザー向け文言の組み立てであり、`operators` 層が担う。`core` が UI 向けの文言を組んではならない (MUST NOT)。

### 5.3 `core/__init__.py`（変更）

既存の再エクスポートを維持したうえで、`VolumeSummary`、`cubic_units_to_ml`、`format_ml`、`total_volume`、`world_volume` を追加し `__all__` に載せる (MUST)。`__all__` は既存どおり定数を先に置いたアルファベット順とする。

### 5.4 `operators/measure_volume.py`（新規）

**`OperatorReturn`**

`operators/solidify.py` にある型エイリアスを再定義せず、そこから import する (MUST)。`operators/solidify.py` 自体は変更しない (MUST NOT)。

**選択の走査**

`operators/solidify.py` の `_selected_meshes` を import してはならない (MUST NOT) — private 関数であり、`total_volume` が自前でメッシュを選別するため不要である。`context.selected_objects or ()` をそのまま `total_volume` に渡す (MUST)。`or ()` が必要な理由（スタブ上 optional であること）は既存コードと同じ形でコメントする。

**`SILMOLD_OT_measure_volume`**

| 項目 | 値 |
| --- | --- |
| `bl_idname` | `silicone_molding.measure_volume` |
| `bl_label` | `Measure Volume` |
| `bl_description` | ツールチップ。推奨文言「Measure the total volume of the selected meshes」 |
| `bl_options` | `{"REGISTER", "UNDO"}` |

- 自前の `bpy.props` を持たない (MUST NOT)。入力は選択とシーン設定のみ
- `poll`: `context.selected_objects` に `type == "MESH"` のオブジェクトが 1 つ以上あるとき真。`context.mode` を見てはならない (MUST NOT、FR-31)
- `execute`
  1. `summary = total_volume(context.selected_objects or (), context.evaluated_depsgraph_get())`
  2. `props = context.scene.silicone_molding`
  3. `summary.non_watertight_names` が空でなければ
     - `props.volume_measured = False` にする（FR-33）
     - 先頭 3 件までの名前と、残りがあればその件数を含むメッセージを `self.report({"ERROR"}, ...)` で報告する
     - `{"CANCELLED"}` を返す
  4. 空であれば
     - `props.volume_ml = cubic_units_to_ml(summary.volume, context.scene.unit_settings.scale_length)`
     - `props.volume_measured = True`
     - `self.report({"INFO"}, ...)` で結果を報告する（`format_ml` を使ってよい (MAY)。ただしこのメッセージはコピーの供給元ではない）
     - `{"FINISHED"}` を返す
- 例外処理: `try` / `except` を書いてはならない (MUST NOT)。`total_volume` は事前条件のもとで例外を送出しない
- `summary.measured_count == 0` の分岐を書いてはならない (MUST NOT)。`poll` が 1 件以上のメッシュを保証し、そのメッシュは「測れた」か「非 watertight」のいずれかに必ず分類されるため、成功経路では `measured_count >= 1` が保証される
- 報告メッセージの文言は仕様として固定しない。テストで完全一致を検証してはならない (MUST NOT)
- 名前列挙の上限（3）はモジュールレベルの `Final` 定数として名前を付ける (MUST)

**`{"CANCELLED"}` を返す前にシーンを書き換えることについて**

`volume_measured = False` の代入は `{"CANCELLED"}` を返す経路でも行う（FR-33）。Blender は `CANCELLED` のときアンドゥステップを push しないため、この「未計測へのリセット」は単独ではアンドゥできない。それでも古い数値を残すより誤読が少ないため、この非対称を受け入れる。この判断を実装のコメントに残す (MUST) — レビューで「CANCELLED なのに副作用がある」と指摘される形であるため。

**`{"CANCELLED"}` が呼び出し側にどう現れるか（実測、2026-08-15）**

`self.report({"ERROR"}, ...)` を呼んだあとに `{"CANCELLED"}` を返すと、`bpy.ops` 経由の呼び出しでは **戻り値が Python に届かず `RuntimeError: Error: <message>` が送出される**。`WARNING` レベルではこれは起こらない。

- GUI 上の振る舞いは意図どおりで、赤いステータス表示になる。実装を変える必要はない (MUST NOT)
- テストは戻り値を assert できない。検証方法は §9.4 の AC-43 〜 AC-45 の注記に従う (MUST)
- この差は既存の `apply_solidify`（`WARNING` + `{"CANCELLED"}`）との対比として覚えておく価値がある。**レベルの選択が、そのまま呼び出し側の制御フローを決める**

### 5.5 `operators/copy_value.py`（新規）

**`SILMOLD_OT_copy_value`**

| 項目 | 値 |
| --- | --- |
| `bl_idname` | `silicone_molding.copy_value` |
| `bl_label` | `Copy Value` |
| `bl_description` | ツールチップ。推奨文言「Copy this value to the clipboard」 |
| `bl_options` | `{"REGISTER", "INTERNAL"}` |

- プロパティ: `value` — `StringProperty(name="Value", default="")`。既存 `ui/properties.py` と同じく `# pyright: ignore[reportInvalidTypeForm]` を付ける
- `poll`: 定義しない (MUST NOT)。クリップボードへの書き込みは選択状態やモードに依存しない
- `execute`
  1. `context.window_manager.clipboard` に `self.value` を代入する
  2. コピーした旨を `self.report({"INFO"}, ...)` で報告する
  3. `{"FINISHED"}` を返す
- 例外処理: `try` / `except` を書いてはならない (MUST NOT)。クリップボードへの代入は失敗しない（GUI が無い環境では黙って no-op になる）
- 命名の判断: このオペレータは渡された文字列をコピーするだけで、体積という概念を一切知らない。`copy_volume` と名付けると実装の内容と乖離し、次の計測項目が入った時点で改名（＝公開 API の変更）が必要になる。中立な `copy_value` とする

**`self.value` を読む側の型付け（実測により追記、2026-08-15）**

`StringProperty` で宣言したプロパティを `execute` の中で `self.value` として **読む** と、`pyright` strict が 2 件落ちる（`reportUnknownMemberType` / `reportUnknownVariableType`）。`_PropertyDeferred` のジェネリック引数が解決されないためで、宣言側（`# pyright: ignore[reportInvalidTypeForm]`）とは別の問題である。

- 対処は `value = cast(str, self.value)  # pyright: ignore[reportUnknownMemberType]` の 1 行とする (MUST)。`cast` 単独でも、クラス変数への型注釈でも消えない（両方試して失敗を確認済み）
- `bpy.types.Operator` の RNA プロパティを読む箇所すべてに同じ制約が掛かる。今後オペレータに自前プロパティを足す場合はこの形を踏襲する
- 対比: `layout.operator()` の戻り値（`OperatorProperties`）への **代入** 側は、スタブの `__setattr__` が `Any` を受けるため無警告で通る。読み書きで非対称である

### 5.6 `operators/__init__.py`（変更）

`SILMOLD_OT_copy_value` と `SILMOLD_OT_measure_volume` を再エクスポートし、`__all__` に追加する (MUST)。

### 5.7 `ui/properties.py`（変更）

`SiliconeMoldingProperties` に 2 つのプロパティを追加する。既存の 2 つは変更しない (MUST NOT)。

| プロパティ名 | 型 | 引数 |
| --- | --- | --- |
| `volume_ml` | `FloatProperty` | `name="Volume (mL)"`, `default=0.0`, `min=0.0` |
| `volume_measured` | `BoolProperty` | `name="Measured"`, `default=False` |

- `volume_ml` に `unit="VOLUME"` を付けてはならない (MUST NOT、FR-29)
- `volume_ml` に `precision` を指定してもよい (MAY)。このプロパティは `layout.prop()` で描画しないため表示精度の効果は無いが、Python コンソールでの確認時に読みやすくなる
- `volume_measured` の名前は肯定形とする (MUST)。「未計測フラグ」の否定形にすると `if not props.volume_not_measured` のような二重否定が呼び出し側に生じる
- `description` は付けてよい (MAY)。`volume_ml` の description には「直近の計測結果であり、シーンの変更で自動更新されない」ことを書く (SHOULD) — スナップショットであるという最大の落とし穴（§8.5 L-1）に、ツールチップで気付けるようにする
- プロパティ**名** は公開 API（NFR-4）。既存 `.blend` から参照されうる
- 読み取り専用にする仕組み（`set` コールバック等）は実装しない (MUST NOT)。本アドオンの UI は `layout.prop()` でこれを描画しないため、通常操作で編集される経路が無い

### 5.8 `ui/panel.py`（変更）

3 つのパネルクラスを 1 ファイルに置く (MUST)。ファイル分割はしない — いずれも小さく、サブパネルは親と一体で読むべきものである。

**`SILMOLD_PT_main`（変更）**

| 項目 | 変更前 | 変更後 |
| --- | --- | --- |
| `bl_label` / `bl_idname` / `bl_space_type` / `bl_region_type` / `bl_category` | 現状 | **変更なし** |
| `draw` の中身 | `solidify_thickness_mm` / `solidify_flip` / Solidify ボタン / Apply ボタン | 空（docstring のみ） |

`draw` の本体は docstring 1 つで足りる（`pass` は不要）。「ヘッダーのみのパネルであり、コントロールはサブパネルが持つ」ことをその docstring に書く (MUST)。既存の `assert layout is not None` は不要になるので消す (MUST) — 自分の変更で不要になったコードは消す、という開発原則に従う。

**`SILMOLD_PT_measurement`（新規）**

| 項目 | 値 |
| --- | --- |
| `bl_label` | `Measurement` |
| `bl_idname` | `SILMOLD_PT_measurement` |
| `bl_space_type` / `bl_region_type` | `VIEW_3D` / `UI` |
| `bl_parent_id` | `SILMOLD_PT_main` |
| `bl_order` | `0` |

`draw` の手順:

1. `layout` を取り出し、既存パネルと同じ理由コメント付きで `assert layout is not None` する
2. `props = context.scene.silicone_molding`
3. `SILMOLD_OT_measure_volume` のボタンを 1 行に描画する。アイコンを付けるかは実装者の裁量とする (MAY)（`pyright` が `IconItems` の Literal で綴りを検証する）
4. 2 列のレイアウト（`layout.split`）を作り、左に `Volume (mL)` のラベルを置く
5. `props.volume_measured` が偽なら、右に無効値の固定文字列（`--`）のラベルを置いて `return` する
6. 真なら `text = format_ml(props.volume_ml)` を 1 度だけ評価する
7. 右に `layout.operator(SILMOLD_OT_copy_value.bl_idname, text=text, emboss=False)` を置き、戻り値の `value` に **同じ** `text` を代入する

- `draw` の中で `context.evaluated_depsgraph_get()`、`Object.to_mesh()`、`total_volume`、`world_volume`、`cubic_units_to_ml` のいずれも呼んではならない (MUST NOT、FR-25)。`draw` が `core` から使うのは `format_ml` だけである
- `--` と `Volume (mL)` はモジュールレベルの `Final` 定数として名前を付ける (SHOULD)
- 未計測の表示に `--` を採る理由: 結果行のレイアウト（左ラベル + 右の値）を計測前後で同じに保てる。`Not measured` のような文にすると値の列だけが伸び、押す前と後でパネルの見た目が変わる。ボタンがすぐ上にあるので「まだ押していない」ことは文脈から明らかである
- 左ラベルの表記は `Volume (mL)` とする (SHOULD)。単位記号は SI の慣行に従い `mL` と綴る (MUST) — リットルの記号は大文字 `L` であり、`ml` と綴ると別記法になる。`mL` は ASCII だけで書けるため、`cm³` のときにあった「Unicode の上付き 3 を使うか `cm3` と書くか」という選択は生じない

**`SILMOLD_PT_processing`（新規）**

| 項目 | 値 |
| --- | --- |
| `bl_label` | `Processing` |
| `bl_idname` | `SILMOLD_PT_processing` |
| `bl_space_type` / `bl_region_type` | `VIEW_3D` / `UI` |
| `bl_parent_id` | `SILMOLD_PT_main` |
| `bl_order` | `1` |

`draw` は、現在の `SILMOLD_PT_main.draw` の中身をそのまま持つ (MUST)。プロパティ行 2 つ → Solidify ボタン（アイコン `MOD_SOLIDIFY`）→ Apply ボタンの順序とアイコンを変えてはならない (MUST NOT)。

**実装で採用された裁量の記録（2026-08-15）**

本仕様が実装者の裁量 (MAY) としていた箇所について、実際に採られた選択を記録する。以後の変更はこれを起点にする（いずれも公開 API ではないため、理由があれば変えてよい）。

| 箇所 | 採用された選択 |
| --- | --- |
| 計測ボタンのアイコン | `DRIVER_DISTANCE` |
| 結果行のレイアウト | `layout.split(factor=0.5)` |
| 左ラベルの表記 | `Volume (mL)`（2026-08-16 の単位表記変更まではこの行が `Volume (cm3)` だった。§13.3） |
| サブパネルの `bl_parent_id` | リテラルではなく `SILMOLD_PT_main.bl_idname` を参照（値は同一なので AC-62 を満たす） |
| 定数名 | `_VOLUME_LABEL` / `_NOT_MEASURED` / `_MAX_REPORTED_NAMES`（いずれも private） |

### 5.9 `ui/__init__.py`（変更）

`SILMOLD_PT_measurement` と `SILMOLD_PT_processing` を再エクスポートし、`__all__` に追加する (MUST)。

### 5.10 `src/silicone_molding/__init__.py`（変更）

`_CLASSES` を以下の順序にする (MUST)。

1. `SiliconeMoldingProperties`
2. `SILMOLD_OT_solidify`
3. `SILMOLD_OT_apply_solidify`
4. `SILMOLD_OT_measure_volume`
5. `SILMOLD_OT_copy_value`
6. `SILMOLD_PT_main`
7. `SILMOLD_PT_measurement`
8. `SILMOLD_PT_processing`

- 6 が 7・8 より前であることは **必須** (MUST)。Blender はサブパネルの登録時に `bl_parent_id` を解決するため、親が未登録だと `RuntimeError` になり `register()` 全体が失敗する（実測でメッセージまで確認済み: `Registering panel class: parent 'X' for 'Y' not found`）
- 現在この `_CLASSES` には「Order within the tuple is cosmetic」というコメントが付いている。本変更で順序が意味を持つようになるため、このコメントを訂正する (MUST) — 誤った不変条件を残すと、次の実装者が安全に並べ替えられると誤解する
- `unregister` は既存どおり `reversed(_CLASSES)` を辿る。子パネルが親より先に unregister されるため追加の対応は不要

### 5.11 実装上の前提（実測で確認済み）

以下は 2026-08-14 に PyPI `bpy` 5.2.0 wheel（開発環境の `just test` と同じランタイム）で確認した事実である。実装者・テスト作成者はこれを前提にしてよい。

| 前提 | 実測結果 |
| --- | --- |
| `Object.to_mesh()` はデータブロックを作らない | `bpy.data.meshes` の内容は前後で不変。返るメッシュは `users == 0` の一時オブジェクト |
| `to_mesh_clear()` は `to_mesh()` 無しで呼んでもエラーにならない | `finally` に無条件で置ける |
| `to_mesh()` を 2 回呼ぶと 1 回目の参照が無効になる | `ReferenceError: StructRNA of type Mesh has been removed` |
| `Depsgraph.update()` は不要 | `context.evaluated_depsgraph_get()` のみで、モディファイアの追加・厚み変更・offset 反転がすべて反映される |
| `show_viewport = False` のモディファイアは評価結果に入らない | 立方体の体積が素の 8.0 に戻る |
| 非メッシュへの `to_mesh()` | カメラで `RuntimeError: Object does not have geometry data` |
| ローカル体積 × `\|det\|` と `BMesh.transform` 後の測定は一致する | 非一様スケール (2,3,4) の 2×2×2 立方体で両者 192。鏡像 (-2,3,4) でも `signed=False` により正の 192 |
| 開いたメッシュの `calc_volume()` は無意味な値を返す | 面を 1 枚外した 2×2×2 立方体で 6.67。watertight 判定で門を作る必要がある |
| 頂点 0 のメッシュ | `to_mesh()` は成功、辺 0、`calc_volume()` は 0.0 |
| 非多様体の検出 | 立方体の 1 辺に三角形を 1 枚足すと、共有面数 3 の辺が 1 本・境界辺 2 本として数えられる |
| `hide_viewport = True` のオブジェクト | `context.selected_objects` に現れない（`select_set(True)` しても入らない）。隠れたオブジェクトの扱いを実装で考える必要はない |
| 編集モード | `EDIT_MESH` でも `world_volume` 相当の処理が例外なく通り、オブジェクトモードと同じ値を返す（FR-31 の根拠） |
| 背景実行での起動時シーン | 選択済みの `Cube` が既に存在する。`poll` が偽になる状況を検証するテストは、先に全オブジェクトを deselect する必要がある |
| クリップボード（背景実行） | `window_manager.clipboard` への代入は例外を出さないが、読み戻すと空文字列になる。**背景実行ではコピー内容を検証できない** |
| `bl_options` に `INTERNAL` を含むオペレータ | `dir(bpy.ops.<namespace>)` には現れる。`bpy.ops` 経由の呼び出しも通る |
| 親パネル未登録での子パネル登録 | `RuntimeError`。逆に「親 → 子（`bl_order` 逆順）」の登録は成功する |
| `draw` が docstring だけのパネル | 正常に登録・描画できる。`draw` を持たないパネルは登録できない |
| `ERROR` レベルの `report` + `{"CANCELLED"}` | `bpy.ops` 経由では戻り値が届かず `RuntimeError: Error: <message>` になる。`WARNING` では起こらない。**`poll` 失敗も同じ例外型** なので、テストは `execute` への到達を別途担保する必要がある |
| `Operator.bl_rna.properties` | Blender 自身の `Operator` 構造体 RNA（14 項目）に解決され、**オペレータが宣言したプロパティを含まない**。宣言したプロパティは `bpy.ops.<ns>.<op>.get_rna_type().properties` で読む。`PropertyGroup.bl_rna.properties` は素直に宣言内容を返すので、両者は非対称 |
| `bpy.types.Panel` の `bl_options` / `poll` | 基底クラスに既定値が無く、サブクラスが宣言しない限り `AttributeError`。テストは `getattr(cls, "bl_options", frozenset())` / `not hasattr(cls, "poll")` で書く |
| `obj.scale` 代入直後の `obj.matrix_world` | **stale**。`to_3x3().determinant()` が 1.0 を返す。`context.evaluated_depsgraph_get()` がフラッシュを行うため、depsgraph を **transform の設定後に** 取得すれば正しくなる（`world_volume` の契約が既にこの順序を含意している）。危険なのは期待値を `matrix_world` から導出するテストで、**両辺が stale になり「通るのに何も検証していない」状態**になる。期待値は解析値（例: `8.0 * 2 * 3 * 4`）で書く |
| `f"{x:.2f}"` の挙動 | `8.0` → `"8.00"`、`0.0` → `"0.00"`、`72216.7225` → `"72216.72"`、`1e-7` → `"0.00"`、`1.2e9` → `"1200000000.00"`（指数表記・桁区切りなし） |
| `pyright` strict | 想定コード形状（`# isort: off` の bmesh import、`calc_volume`、`to_3x3().determinant()`、frozen dataclass、`OperatorProperties` への属性 **代入**、`Panel.bl_order` / `bl_parent_id`、docstring のみの `draw`）で 0 エラー。`context.window_manager` / `context.scene` の narrow は既存コードと同様に不要。**ただしオペレータ自身の `StringProperty` を `self.value` として読む側は 2 件落ちる** — §5.5 の注記を参照（この行は 2026-08-15 に実測で訂正） |
| `unit_settings.scale_length` | 0 を代入すると 1e-9 にクランプされる。float32 精度（0.001 → 0.0010000000474974513） |

______________________________________________________________________

## 6. データモデル

### 6.1 パラメータと状態

ユーザーが直接設定するパラメータは無い。読み書きする値は以下。

| 名前 | 保持場所 | 単位 | 既定 | 読み / 書き |
| --- | --- | --- | --- | --- |
| `volume_ml` | `Scene.silicone_molding` | mL | 0.0 | 計測オペレータが書き、パネルが読む |
| `volume_measured` | `Scene.silicone_molding` | — | `False` | 計測オペレータが書き、パネルが読む |
| `scale_length` | `Scene.unit_settings` | m / BU | 1.0 | 計測オペレータが読む |
| `matrix_world` | 各 `Object` | — | — | `world_volume` が読む |
| 選択 | `Context.selected_objects` | — | — | `poll` と `execute` が読む |
| `value`（コピーオペレータ） | オペレータのプロパティ | — | `""` | パネルが書き、オペレータが読む |

`volume_ml` と `volume_measured` は `.blend` に保存され、再読込後も残る。これは PropertyGroup の既定の振る舞いであり、意図的に打ち消さない（§11 OQ-2）。

### 6.2 ジオメトリ

- 入力: depsgraph 評価後の一時メッシュ。閉じている必要は無いが、閉じていなければ体積を返さない
- 出力: ジオメトリを一切出力しない。数値と文字列のみ
- 座標系: 判定はトポロジのみなので座標系に依存しない。体積はローカル空間で測り、行列式でワールド空間へ換算する
- メッシュを変更しない (MUST NOT)。本機能はジオメトリに対して完全に読み取り専用である

### 6.3 単位の妥当性（3D プリント前提）

| 対象 | おおよその体積 | 表示 |
| --- | --- | --- |
| 2 cm 角の立方体 | 8 mL | `8.00` |
| 手のひらサイズの型（10×10×5 cm の外形、壁 3 mm） | 数十 mL | `50.00` 前後 |
| 2 m 角の立方体（テストフィクスチャ） | 8,000,000 mL | `8000000.00` |

実務では 1〜500 mL のオーダーが中心になる。小数 2 桁は「シリコーンを 0.01 mL 単位で読む意味は無いが、小さな部品で有効数字が足りなくなるのは避けたい」という妥協点である。1 mL 未満の部品では `0.00` と表示されうる（§8.5 L-4）。

**mL 表記を選んだ理由**: シリコーン・レジン・離型剤はいずれも容器に mL（と g）で表示され、計量カップの目盛りも mL である。値は cm³ と完全に同一だが、ユーザーが計量作業で実際に読む単位に合わせることで、パネルの数値を目盛りへそのまま持っていける。cm³ 表記だと造形者が頭の中で読み替える一手間が挟まる（2026-08-16 にこの理由で cm³ 表記から改めた。§13.3）。

### 6.4 バリデーション規則

- V-1. 測定対象は `type == "MESH"` のオブジェクトのみ（`total_volume` が保証）
- V-2. 体積を保存するのは、選択中の全メッシュの評価後メッシュが watertight な場合のみ（オペレータが保証）
- V-3. `volume_ml` の値域は `min=0.0`（RNA がクランプ）。`world_volume` が非負を返すため、通常経路でこの下限に触ることはない
- V-4. `scale_length` の値域は Blender 本体が保証する。アドオン側で検査しない
- V-5. その他の入力検証は行わない。特に自己交差・法線の向きの一貫性・面の縮退は検査しない（§8.5）

______________________________________________________________________

## 7. 振る舞い詳細

### S-1: 閉じた 1 オブジェクトを測る（基本シナリオ）

- **Given** 一辺 2 cm の立方体（変換なし）が 1 つあり、それだけが選択されている
- **And** `scale_length` が 1.0、結果は未計測である
- **When** ユーザーが **Measure Volume** ボタンを押す
- **Then** `Volume (mL)` の行の表示が `--` から `8.00` に変わる
- **And** その数値はボタン枠なしで描画され、マウスを乗せるとツールチップが出る
- **And** ステータスバーに計測結果が `INFO` として報告される

### S-2: 値をコピーする

- **Given** S-1 の終了状態
- **When** ユーザーが `8.00` をクリックする
- **Then** クリップボードの内容が `8.00`（単位なし・桁区切りなし）になる
- **And** ステータスバーにコピーした旨が `INFO` として表示される
- **And** アンドゥ履歴には何も積まれない

### S-3: 複数オブジェクトの合計

- **Given** 一辺 2 cm の立方体が 2 つ、離れた位置にあり、両方選択されている
- **When** **Measure Volume** を押す
- **Then** `16.00` と表示される（合計値のみ。内訳は出さない）

### S-4: モディファイアが反映される

- **Given** 2 m 角の立方体に Solidify（壁厚 3 mm、外側）が付いており、未適用のまま選択されている
- **When** **Measure Volume** を押す
- **Then** 表示されるのは立方体の中身ではなく **壁の体積**（外殻 − 内殻）である
- **And** 壁厚を 5 mm に変えても表示は変わらない（スナップショットであるため）
- **And** もう一度 **Measure Volume** を押すと、5 mm の壁の体積に更新される

### S-5: 開いたメッシュが混ざっている

- **Given** 閉じた立方体 `A` と、面を 1 枚削った立方体 `B` が選択されている
- **And** 直前に `A` だけを測った結果（`8.00`）が表示されている
- **When** **Measure Volume** を押す
- **Then** ステータスバーに `B` の名前を含むエラーが表示される
- **And** 結果行の表示が `8.00` から `--` に戻る（古い値を残さない）
- **And** `A` の体積は表示されない（部分的な合計は出さない）

### S-6: 選択が空

- **Given** 何も選択されていない、またはカメラとライトだけが選択されている
- **When** ユーザーが Measurement セクションを見る
- **Then** **Measure Volume** ボタンがグレーアウトしていて押せない
- **And** 結果行には直前の計測結果（あれば）がそのまま残っている

### S-7: 単位スケールが mm のシーン

- **Given** `scale_length` が 0.001（1 BU = 1 mm のシーン設定）
- **And** 一辺 20 BU（= 2 cm）の立方体だけが選択されている
- **When** **Measure Volume** を押す
- **Then** `8.00` と表示される（`scale_length` が 1.0 で一辺 0.02 BU のときと同じ物理量）

### S-8: 非一様スケール・鏡像スケール

- **Given** 一辺 2 cm の立方体に `scale = (2, 1, 1)` が掛かっており、それだけが選択されている
- **When** **Measure Volume** を押す
- **Then** `16.00` と表示される
- **And** `scale = (-2, 1, 1)`（鏡像）にして測り直しても `16.00` になる（負の値やゼロにならない）

### S-9: 計測をアンドゥする

- **Given** `8.00` が表示されている状態で、選択を別の立方体に変えて測り直し `16.00` になっている
- **When** ユーザーが Ctrl+Z を押す
- **Then** 結果行の表示が `8.00` に戻る
- **And** さらに Ctrl+Z を押すと、`8.00` を計測する前の状態（`--`）まで戻る

### S-10: スナップショットが古くなる

- **Given** `8.00` が表示されている
- **When** ユーザーがそのオブジェクトを 2 倍にスケールする（測り直さない）
- **Then** 表示は `8.00` のまま変わらない（実際の体積は 64 mL になっている）
- **And** ユーザーが **Measure Volume** を押すと `64.00` に更新される
- これは仕様である（N-5・§8.5 L-1）。自動で無効化する仕組みは持たない

### S-11: セクションを折りたたむ

- **Given** サイドバーに `Silicone Molding` パネルがあり、その中に Measurement と Processing が上から順に並んでいる
- **When** ユーザーが Measurement の三角形をクリックして折りたたむ
- **Then** 計測ボタンと結果行が隠れる
- **And** Processing のコントロール（壁厚・方向反転・Solidify・Apply）は従来どおり機能する
- **And** 折りたたみ状態は `.blend` を保存・再読込しても保たれる

______________________________________________________________________

## 8. エッジケースとエラー処理

### 8.1 選択とオブジェクト種別

| 状況 | 期待される振る舞い |
| --- | --- |
| 選択が 0 個 | `poll` が偽。ボタンはグレーアウトし押せない。API から直接呼ぶと Blender が `RuntimeError` を送出する（アドオン側では扱わない） |
| 選択にメッシュが 1 つも無い（カメラ・ライトのみ） | 同上。`poll` が偽 |
| 選択にメッシュと非メッシュが混在 | メッシュのみ測り、非メッシュは**黙って**スキップする。警告を出してはならない (MUST NOT) |
| 選択にカーブ・テキスト・メタボールが含まれる | 非メッシュとしてスキップする。`to_mesh()` は通るが対象外（N-7）。ユーザーには「カーブが数えられていない」ことが分からないという限界がある（§11 OQ-3） |
| アクティブオブジェクトが選択に含まれない | 影響しない。本機能はアクティブオブジェクトを参照しない |
| ビューポートで非表示のオブジェクト | `context.selected_objects` に現れないため、そもそも対象にならない（§5.11 で実測確認） |
| 編集モード中 | ボタンは押せ、編集中のメッシュの評価結果を測る。オブジェクトモードと同じ値になる（§5.11 で実測確認） |
| ライブラリリンクされたオブジェクト | ジオメトリは読み取りのみなので問題にならない。書き込むのは自シーンの `Scene.silicone_molding` だけである |
| 計測後に選択を変える | 表示は変わらない。次に押したときの対象だけが変わる（S-6・S-10） |

### 8.2 ジオメトリの退化・破綻

| 状況 | 期待される振る舞い |
| --- | --- |
| 開いたメッシュ（境界辺を持つ） | `world_volume` が `None` → `ERROR` を報告し `{"CANCELLED"}`、`volume_measured` は偽 |
| 非多様体入力（3 枚以上の面が共有する辺） | 同上。境界辺と非多様体辺をメッセージ上で区別しない（ユーザーの対処は同じ「メッシュを閉じる」であるため） |
| 面が 0 で辺がある（頂点・辺のみのメッシュ） | すべての辺が境界辺になるので `None`。エラーになる |
| 頂点 0 の完全に空なメッシュ | 辺が 0 本なので判定条件を空虚に満たし、体積 0.0 として計上する。特別扱いしない (MUST NOT)（FR-21）。1 つだけ選んで測ると `0.00` が保存される |
| ゼロ面積の面を含む | 検査しない。`calc_volume` はその面の寄与を 0 として扱う |
| 自己交差する閉じたメッシュ | 検査しない。交差部が二重に数えられた値が出る。これは検出困難であり、後続の「型の検査」機能の責務（§11 OQ-5） |
| 法線の向きが不統一な閉じたメッシュ | 検査しない。`is_watertight` は向きの一貫性を見ないため、符号付き体積が打ち消し合って過小な値（極端な場合 `0.00`）になりうる。既知の限界（L-2） |
| 内部に隔壁を持つメッシュ | 隔壁の辺は共有面数 3 以上になるのでエラーになる。ただし Solidify が作る外殻 + 内殻は 2 つの独立したパーツであり、どの辺も共有面数 2 なので watertight として正しく壁体積が出る |
| 極端に小さい体積 | `0.00` と表示される。エラーではない（L-4） |
| 極端に大きい体積 | 指数表記にはならず桁が伸びる（例: `1200000000.00`）。パネル幅を超えると Blender が末尾を省略表示する（L-5） |

### 8.3 変換行列・単位設定

| 状況 | 期待される振る舞い |
| --- | --- |
| 一様スケール `s` | 体積は `s ** 3` 倍。ワールド実寸として正しい |
| 非一様スケール `(sx, sy, sz)` | 体積は `abs(sx * sy * sz)` 倍。正しい。Solidify 仕様の N-3（壁厚は補正しない）とは別の話であり、体積側に補正漏れは無い |
| 鏡像スケール（行列式が負） | 絶対値を取るので正の値になる（FR-17・FR-18） |
| いずれかの軸のスケールが 0（潰れたオブジェクト） | 行列式が 0 になり体積 0.0。エラーにしない |
| 回転・移動のみ | 体積は不変 |
| 親子付け・コンストレイントによるワールド変換 | `matrix_world` に織り込まれているので正しく反映される |
| `unit_settings.system` が `IMPERIAL`、`length_unit` が `MILLIMETERS` 等 | 影響しない。mL 固定で表示する（FR-38） |
| 計測後に `scale_length` を変更する | 表示は変わらない。mL で保存しているため（FR-27）、過去の計測は当時の物理量を保ち続ける。押し直せば新しい `scale_length` で計測される |
| `scale_length` が極端に小さい（1e-9） | 換算結果が極端に小さくなるが、計算は破綻しない。ゼロ除算は起こらない（掛け算のみ） |

### 8.4 オペレータと状態遷移

| 状況 | 期待される振る舞い |
| --- | --- |
| 同じ選択で連続 2 回押す | 冪等。2 回目も同じ値が保存される（シーンが変わっていない限り） |
| 未計測の状態でパネルを見る | 結果行は `--`。コピーボタンは描画されない（FR-45） |
| 未計測の状態で `bpy.ops.silicone_molding.copy_value` を直接呼ぶ | 通常操作では到達しないが、呼べば空文字列がコピーされる。防御しない（`poll` を足してはならない） |
| 計測が失敗した直後 | `volume_measured` が偽になり表示が `--` に戻る。`volume_ml` の値は未定義（前回値が残っていてよい。読み手が居ないため） |
| 失敗を Ctrl+Z で戻す | `{"CANCELLED"}` はアンドゥステップを push しないため、失敗直前の値には単独では戻せない。もう一度測り直すのが正しい操作（§5.4 の注記） |
| `.blend` を保存して開き直す | `volume_ml` と `volume_measured` は保存されるため、前回の結果が表示される。シーンが変わっていなければ正しい値である（§11 OQ-2） |
| 別シーンに切り替える | `Scene.silicone_molding` はシーン単位なので、シーンごとに独立した結果を持つ。これは望ましい振る舞いである |
| アンドゥ後の表示 | Blender がシーンデータを巻き戻すので、結果行も自動的に前の値に戻る（S-9） |

### 8.5 既知の限界事項

- L-1. **結果はボタンを押した瞬間のスナップショットである。** 選択の変更、ジオメトリの編集、モディファイアの変更、オブジェクトのスケール変更のいずれによっても自動更新されない。古い値が表示されていることをユーザーが見分ける手段は無い（表示に時刻や対象オブジェクト名を添えない）。これは自動無効化の仕組み（ハンドラ購読）を持たない代償であり、意図的な割り切りである（N-5）。緩和は §11 OQ-1
- L-2. 法線の向きが不統一な閉じたメッシュでは、符号付き体積が打ち消し合って過小な値が出る。`is_watertight` は向きの一貫性を検査しないため検出できない。Blender の「Recalculate Outside」で直せる範囲の問題であり、本仕様では警告しない
- L-3. 自己交差する閉じたメッシュでは、交差部の体積が重複して数えられる
- L-4. 1 mL の 1/100 未満の体積は `0.00` と表示される。表示精度が固定であることの帰結（FR-42）
- L-5. 桁数の多い値はパネル幅に収まらず、Blender が末尾を省略して描画する。コピーされる文字列は省略されない完全な値である
- L-6. 実インスタンス（コレクションインスタンス、パーティクル、ジオメトリノードのインスタンス出力）は計上されない（N-8）
- L-7. カーブ・テキスト等の非メッシュオブジェクトが選択に含まれても、何も言わずスキップするため、ユーザーはそれが数えられていないことに気付けない（§11 OQ-3）
- L-8. 背景実行ではクリップボードの読み書きが no-op になるため、コピー内容の自動検証ができない。tier 1・tier 2 のいずれでも担保できず、手動確認に頼る（§9.7）
- L-9. `Scene` の `FloatProperty` は float32 で保持されるため、保存された `volume_ml` は計測時に計算した double 値から約 1e-7 の相対誤差で丸められる。小数 2 桁の表示には影響しない

______________________________________________________________________

## 9. 受け入れ基準

各項目に検証階層を明記する。tier 1 = `just test`（PyPI `bpy` wheel 上の pytest）、tier 2 = `just blender-test`（実 Blender）。

**golden mesh は作らない（該当なし）。** 本機能はジオメトリを出力しない。入力側の期待値も、Blender 自身のモディファイア出力に依存する部分は解析的な不変量で検証する（solidify 仕様 §9 の判断を踏襲）。

**許容誤差の方針。** Blender のメッシュ座標は float32、`Scene` の `FloatProperty` も float32 なので、体積は解析値に対して相対 1e-5 程度ずれる。BU³ の比較は「その規模での絶対誤差」で書く。mL の比較は `format_ml` を通した **文字列一致** で書けるので、そちらを優先する（表示が仕様であり、内部の浮動小数点値は仕様ではない）。

**選択状態を作る fixture が必要。** 背景実行の起動時シーンには選択済みの `Cube` が既に居る（§5.11）。オペレータのテストは、setup で全オブジェクトを deselect してから自分で選択を作る fixture を用意する (MUST)。

### 9.1 単位換算と書式（tier 1、モジュール A）

- [ ] AC-1. `cubic_units_to_ml(1.0, 1.0)` が 1e6 を返す（相対誤差 1e-12 以内）
- [ ] AC-2. `cubic_units_to_ml(8e-6, 1.0)` が 8.0 を返す（相対誤差 1e-9 以内）＝ 2 cm 角の立方体
- [ ] AC-3. `cubic_units_to_ml(8000.0, 0.001)` が 8.0 を返す（相対誤差 1e-6 以内）＝ 1 BU = 1 mm のシーンでの同じ物体
- [ ] AC-4. `cubic_units_to_ml(0.0, 1.0)` が 0.0 を返す
- [ ] AC-5. `scale_length` を 2 倍にすると戻り値が 8 倍になる（3 次であることの確認）
- [ ] AC-6. `core/units.py` が `bpy` を import していない（モジュールのソース確認、またはレビューでの目視確認でよい）
- [ ] AC-7. `format_ml(8.0)` が `"8.00"` を返す
- [ ] AC-8. `format_ml(0.0)` が `"0.00"` を返す
- [ ] AC-9. `format_ml(72216.7225)` が `"72216.72"` を返す（桁区切りが入らないことの確認）
- [ ] AC-10. `format_ml(1.2e9)` の戻り値に `"e"` が含まれない（指数表記にならないことの確認）
- [ ] AC-11. `format_ml(1e-7)` が `"0.00"` を返す（L-4 の明文化）

### 9.2 単一オブジェクトの体積（tier 1、モジュール A）

前提: `tests/conftest.py` の `make_object` / `cube_object` でシーンコレクションに link したオブジェクトを使う（`cube_mesh` / `empty_mesh` fixture との二重解放に注意）。depsgraph は `bpy.context.evaluated_depsgraph_get()` から得る。

- [ ] AC-12. 変換なしの 2×2×2 立方体で `world_volume` が 8.0 を返す（絶対誤差 1e-5 以内）
- [ ] AC-13. `scale = (2, 1, 1)` の同オブジェクトで 16.0 を返す（絶対誤差 1e-5 以内）
- [ ] AC-14. `scale = (-2, 1, 1)`（鏡像）で **正の** 16.0 を返す（絶対誤差 1e-5 以内）
- [ ] AC-15. 回転と移動のみを与えた場合、戻り値が 8.0 のまま変わらない（絶対誤差 1e-5 以内）
- [ ] AC-16. 面を 1 枚削った立方体（境界辺あり）で `None` を返す
- [ ] AC-17. 1 辺に 3 枚目の面を足した立方体（非多様体辺あり）で `None` を返す
- [ ] AC-18. 頂点 0 のメッシュで `None` ではなく 0.0 を返す
- [ ] AC-19. 固定名 Solidify（壁厚 0.003 BU、外側、Even Thickness）を付けた 2×2×2 立方体で、`2.006 ** 3 - 2 ** 3` を返す（絶対誤差 1e-5 以内。モディファイア込み評価の確認）
- [ ] AC-20. AC-19 のモディファイアの `show_viewport` を `False` にすると 8.0 を返す（FR-14 の確認）
- [ ] AC-21. `world_volume` の呼び出し前後で `len(bpy.data.meshes)` が変わらない（一時メッシュを残さないことの確認）
- [ ] AC-22. 非 watertight で `None` を返す経路でも `len(bpy.data.meshes)` が変わらない（早期 return でも `to_mesh_clear` されることの確認）

### 9.3 選択全体の集計（tier 1、モジュール A）

- [ ] AC-23. 2 cm 角の立方体 2 つを渡すと、`measured_count == 2`、`non_watertight_names == ()`、`volume` が単体の 2 倍（絶対誤差 1e-9 以内）
- [ ] AC-24. メッシュ 2 つと非メッシュ（カメラ等）1 つを渡すと、`measured_count == 2` で例外が出ない
- [ ] AC-25. 空のイテラブルを渡すと `volume == 0.0`、`measured_count == 0`、`non_watertight_names == ()`
- [ ] AC-26. 非メッシュのみを渡した場合も AC-25 と同じ結果になる
- [ ] AC-27. 閉じたメッシュ 1 つと開いたメッシュ 1 つを渡すと、`measured_count == 1` かつ `non_watertight_names` が開いたメッシュのオブジェクト名だけを含む
- [ ] AC-28. 開いたメッシュを 3 つ渡すと `non_watertight_names` の長さが 3 で、**渡した順序** と一致する（`VolumeSummary` の反復順の保証）
- [ ] AC-29. 同じメッシュデータブロックを共有する 2 オブジェクト（一方に一様スケール 2）を渡すと、`measured_count == 2` で `volume` が「単体 + 単体の 8 倍」になる（FR-12。絶対誤差 1e-5 以内）
- [ ] AC-30. `total_volume` の呼び出しがどのオブジェクトのメッシュも変更しない（呼び出し前後で各メッシュの頂点数・面数が同一）

### 9.4 計測オペレータ（tier 1、モジュール B）

**ここが今回いちばん重要な階層である。** 従来「`draw()` の目視レビューでしか確認できない」としていた計測ロジックは、オペレータを呼んで `Scene` プロパティを読むことで自動検証できる。

- [ ] AC-31. 選択が 0 個のとき `SILMOLD_OT_measure_volume.poll` が偽（fixture で先に全 deselect する）
- [ ] AC-32. カメラのみを選択したとき `poll` が偽
- [ ] AC-33. メッシュを選択したとき `poll` が真
- [ ] AC-34. 編集モードでメッシュを選択しているとき `poll` が真（FR-31。モード条件を付けていないことの確認）
- [ ] AC-35. 登録直後の `Scene.silicone_molding` で `volume_measured` が偽（既定値の意味的確認）
- [ ] AC-36. 一辺 0.02 BU の立方体 1 つを選択して実行すると `{"FINISHED"}` を返し、`volume_measured` が真、`format_ml(volume_ml) == "8.00"`
- [ ] AC-37. 同じ立方体 2 つを選択して実行すると `format_ml(volume_ml) == "16.00"`
- [ ] AC-38. メッシュ 2 つと非メッシュ 1 つを選択して実行すると、非メッシュが無いときと同じ値になる（黙ってスキップすることの確認）
- [ ] AC-39. `scale_length = 0.001` のシーンで一辺 20 BU の立方体を測ると `format_ml(volume_ml) == "8.00"`（S-7）
- [ ] AC-40. `scale = (2, 1, 1)` の 2 cm 立方体を測ると `"16.00"`、`scale = (-2, 1, 1)` でも `"16.00"`（S-8）
- [ ] AC-41. 固定名 Solidify を付けた立方体を測ると、素の立方体とは異なる値になり、かつ解析値（壁の体積）と一致する（絶対誤差は §9 冒頭の方針に従う。FR-13）
- [ ] AC-42. 同じ選択で 2 回連続実行すると、2 回目の `volume_ml` が 1 回目と等しい（冪等性）
- [ ] AC-43. 開いたメッシュのみを選択して実行すると `RuntimeError` が送出され、`volume_measured` が偽になる
- [ ] AC-44. 閉じたメッシュ 1 つと開いたメッシュ 1 つを選択して実行すると `RuntimeError` が送出され、`volume_measured` が偽になる（部分的な合計を出さないことの確認。FR-32）
- [ ] AC-45. **成功して値が入っている状態から** 開いたメッシュを含む選択で実行すると、`volume_measured` が偽に戻る（FR-33。古い値を残さない）

**AC-43 〜 AC-45 の検証方法（実測により訂正、2026-08-15）**

`self.report({"ERROR"}, ...)` を呼んだオペレータは、`{"CANCELLED"}` を返しても `bpy.ops` 経由では **戻り値が Python に届かず `RuntimeError: Error: <message>` が送出される**。したがってこれらを `bpy.ops` 経由で検証するテストは、戻り値を assert できない (MUST NOT)。

- 受け方は `pytest.raises(RuntimeError)` とする (MUST)。`match=` を使ってはならない (MUST NOT) — メッセージ文言は仕様ではない
- **`poll` 失敗も同じ `RuntimeError` を出す。** そのため `pytest.raises(RuntimeError)` だけでは「`execute` に到達せず `poll` で弾かれた実行」を誤って合格にしてしまう。各テストは次のいずれかで `execute` への到達を担保する (MUST)
  - Arrange で `poll` が真であることを assert する
  - `volume_measured = True` を先に仕込み、Act の後に偽へ変わったことを assert する（副作用の観測により `execute` が走ったと分かる）
- `{"CANCELLED"}` を返す設計（FR-32）自体は正しく、変更しない。GUI では赤いステータス表示になるのが望ましい振る舞いであり、`RuntimeError` は「`bpy.ops` から呼んだ場合の現れ方」に過ぎない
- 対比: `WARNING` レベルの `report` では例外が送出されない。既存の `apply_solidify` のテストが `{"CANCELLED"}` を assert できているのはこのためである（solidify 仕様 AC-36）
- [ ] AC-46. 計測がどのオブジェクトのメッシュも変更しない（実行前後で頂点数・面数・モディファイア数が同一）
- [ ] AC-47. `"UNDO" in SILMOLD_OT_measure_volume.bl_options`（FR-30）
- [ ] AC-48. `SILMOLD_OT_measure_volume.bl_idname == "silicone_molding.measure_volume"`（`api_contract` マーカー。契約のピン留めである旨をコメントに明記する）
- [ ] AC-49. `"measure_volume"` が `dir(bpy.ops.silicone_molding)` に含まれる（`hasattr` は常に真になるので使わない）
- 注記: エラーメッセージの文言を検証してはならない (MUST NOT)。オブジェクト名が含まれることの確認は `pytest.raises(match=...)` 相当の部分一致すら使えない（`self.report` は例外ではない）ため、メッセージ内容は §10.4 のレビューと §9.7 の手動確認で担保する

### 9.5 コピーオペレータ（tier 1、モジュール B）

- [ ] AC-50. `bpy.ops.silicone_molding.copy_value(value="8.00")` が `{"FINISHED"}` を返す
- [ ] AC-51. `"copy_value"` が `dir(bpy.ops.silicone_molding)` に含まれる
- [ ] AC-52. `SILMOLD_OT_copy_value.bl_idname == "silicone_molding.copy_value"`（`api_contract`）
- [ ] AC-53. `"UNDO" not in SILMOLD_OT_copy_value.bl_options`（FR-49。シーンを変更しないオペレータがアンドゥを積まないという意味的不変条件）
- [ ] AC-54. `SILMOLD_OT_copy_value.bl_description` が空文字列でない（FR-52）
- [ ] AC-55. `value` プロパティが登録済みである。読み取り先は `bpy.ops.silicone_molding.copy_value.get_rna_type().properties` とする (MUST)。**`SILMOLD_OT_copy_value.bl_rna.properties` を見てはならない (MUST NOT)** — そちらは Blender 自身の `Operator` 構造体 RNA（`bl_idname` / `bl_options` / `layout` など 14 項目）に解決され、オペレータが宣言したプロパティを含まない（実測により訂正、2026-08-15）
- 注記: クリップボードの内容そのものは背景実行では検証できない（L-8）。§9.7 の手動確認で担保する。`window_manager.clipboard` を読んで assert するテストを書いてはならない (MUST NOT) — 常に空文字列が返り、何も検証しないテストになる

### 9.6 シーンプロパティとパネル構造（tier 1、モジュール B）

- [ ] AC-56. `silicone_molding.register()` と `unregister()` が例外なく往復する。これがサブパネルの登録順（FR-8）の回帰検出になる。既存 `tests/silicone_molding/test_register.py` の module scope fixture が失敗すれば検出される
- [ ] AC-57. 登録後、`Scene.silicone_molding` に `volume_ml` と `volume_measured` が存在する（`api_contract`。NFR-4）
- [ ] AC-58. `volume_ml` の RNA の `unit` が `"NONE"` である（FR-29。既存の `solidify_thickness_mm` に対する同種のテストと対になる）
- [ ] AC-59. 既存の `solidify_thickness_mm` と `solidify_flip` が引き続き存在する（`api_contract`。プロパティ追加で既存を壊していないことの確認）
- [ ] AC-60. `SILMOLD_PT_main.bl_idname == "SILMOLD_PT_main"` かつ `bl_category == "Silicone Molding"`（`api_contract`。FR-1）
- [ ] AC-61. `SILMOLD_PT_measurement.bl_idname == "SILMOLD_PT_measurement"` および `SILMOLD_PT_processing.bl_idname == "SILMOLD_PT_processing"`（`api_contract`。パネルの開閉状態が `.blend` にこの id で保存される）
- [ ] AC-62. 両サブパネルの `bl_parent_id` が `SILMOLD_PT_main.bl_idname` に等しい
- [ ] AC-63. `SILMOLD_PT_measurement.bl_order < SILMOLD_PT_processing.bl_order`（順序の意味的不変条件。リテラル値は固定しない）
- [ ] AC-64. 両サブパネルの `bl_options` に `"DEFAULT_CLOSED"` が含まれない（FR-6）。`getattr(cls, "bl_options", frozenset())` で読む (MUST) — `bpy.types.Panel` は `bl_options` を既定値として持たないため、クラスが宣言しない限り `cls.bl_options` は `AttributeError` になる（実測により訂正、2026-08-15）
- [ ] AC-65. 両サブパネルが `poll` を独自に定義していない（FR-7）。`not hasattr(cls, "poll")` で書く (MUST) — 同じ理由で、`bpy.types.Panel` は `poll` を基底クラスに持たない

`draw()` の内容（2 分岐、`text` と `value` の同一性、`draw` が計測しないこと）は背景実行では検証できない。§10.4 のレビューチェックリストと §9.7 の手動確認で担保する。

### 9.7 実 Blender での統合（tier 2、モジュール B、`tests/blender/run.py` に追記）

既存方針どおり third-party を import しない。**インストール済み extension モジュールの import も不要** になった — 計測結果が `Scene` プロパティに載るため、すべて `bpy.ops` と RNA だけで到達できる。

- [ ] AC-66. `"measure_volume"` と `"copy_value"` が `dir(bpy.ops.silicone_molding)` に含まれる（既存 `check_addon_is_enabled` のリストに追記）
- [ ] AC-67. `Scene.silicone_molding` に `volume_ml` と `volume_measured` がある（既存 `check_scene_properties` のリストに追記）
- [ ] AC-68. 一辺 0.02 BU の立方体 1 つを選択して `bpy.ops.silicone_molding.measure_volume()` を呼ぶと `{"FINISHED"}` が返り、`volume_measured` が真、`volume_ml` が 8.0（絶対誤差 1e-4 以内）。実 Blender のビルドでも tier 1 と同じ値が出ることの確認
- [ ] AC-69. 面を 1 枚削ったメッシュを選択して呼ぶと `volume_measured` が偽になる。tier 2 は pytest を使わないため、`try` / `except RuntimeError` で囲んで「例外が出たこと」と「`volume_measured` が偽であること」の両方を assert する (MUST)。`{"CANCELLED"}` を assert してはならない (MUST NOT) — §9.4 の AC-43 〜 AC-45 と同じ理由（`ERROR` レベルの `report` が `bpy.ops` 経由で `RuntimeError` になる）
- [ ] AC-70. `bpy.ops.silicone_molding.copy_value(value="8.00")` が `{"FINISHED"}` を返す

### 9.8 手動確認（実 Blender GUI、`just dev`）

自動化できない項目。実施したことを PR 本文に記録する (MUST)。

- [ ] AC-71. サイドバー `Silicone Molding` タブに、親パネル 1 つと `Measurement` → `Processing` の順で並ぶサブパネル 2 つが表示される
- [ ] AC-72. 各サブパネルが独立に折りたためる。折りたたみ状態が `.blend` の保存・再読込を越えて保たれる
- [ ] AC-73. Processing の壁厚・方向反転・Solidify・Apply が従来どおり動作する（solidify 仕様 S-1 の再確認）
- [ ] AC-74. 未計測の状態で結果行が `--` になっており、その行がクリックできない
- [ ] AC-75. 何も選択していないとき **Measure Volume** ボタンがグレーアウトしている
- [ ] AC-76. 表示された数値をクリックし、別アプリケーション（テキストエディタ・表計算）に貼り付けて、単位も桁区切りも含まない数値だけが入ることを確認する（L-8 の唯一の検証手段）
- [ ] AC-77. 数値にマウスを乗せるとコピーを促すツールチップが出る（FR-52）
- [ ] AC-78. 開いたメッシュを含む選択で計測すると、ステータスバーに **オブジェクト名を含む** 赤いエラーが出て、結果行が `--` に戻る（FR-34 の文言確認を含む）
- [ ] AC-79. 開いたメッシュを 4 つ以上含む選択で計測すると、エラーメッセージが 3 件の名前 + 残り件数の形に収まり、1 行で読める（FR-34）
- [ ] AC-80. 計測後に Ctrl+Z で前の結果に戻り、もう一度 Ctrl+Z で未計測まで戻る（S-9）
- [ ] AC-81. 数値をクリックした後 Ctrl+Z を押しても、コピー操作は取り消されず直前の造形操作が取り消される（FR-49）
- [ ] AC-82. Solidify の壁厚を変えても表示は変わらず、押し直すと更新される（S-4・S-10。スナップショットであることの確認）

### 9.9 品質ゲート

- [ ] AC-83. `just run`（format → test → type）が通る
- [ ] AC-84. `just blender-test` が通る

______________________________________________________________________

## 10. 実装計画

### 10.1 フェーズ

| フェーズ | 内容 | 成果物 | 依存 |
| --- | --- | --- | --- |
| P1 | モジュール A の実装とテスト | `core/units.py`、`core/volume.py`、`core/__init__.py`、`tests/silicone_molding/core/test_units.py`（追記）、`tests/silicone_molding/core/test_volume.py` | なし |
| P2 | モジュール B の実装とテスト | `operators/measure_volume.py`、`operators/copy_value.py`、`operators/__init__.py`、`ui/properties.py`、`ui/panel.py`、`ui/__init__.py`、`__init__.py`、`tests/silicone_molding/operators/test_measure_volume.py`、`tests/silicone_molding/operators/test_copy_value.py`、`tests/silicone_molding/ui/test_panel.py`、`tests/silicone_molding/test_register.py`（追記） | A の §5.1 / §5.2 のシグネチャ。実行時には P1 の成果物 |
| P3 | tier 2 の統合チェック追記 | `tests/blender/run.py` | P1・P2 |
| P4 | 手動確認 | `just dev` で AC-71 〜 AC-82 を実施 | P1〜P3 |
| P5 | ドキュメント | docstring、`CHANGELOG.md` の `## [Unreleased]` 更新 | P1〜P4 |

P1 と P2 は §4.3 の分担どおりファイルが排他なので **並列に着手できる**。P2 のテストは P1 がマージされるまで赤のままになる。

P2 の内部には順序がある。`ui/panel.py` は `operators/__init__.py` 経由で 2 つの `bl_idname` を参照し、`ui/properties.py` の 2 プロパティを読むため、**プロパティ → オペレータ → パネル → ルート `__init__.py`** の順に書くのが素直である。ただしすべて同一エージェントの担当なので、ファイル排他の制約には影響しない。

P5 では `## [Unreleased]` に「サイドバーのセクション分け」と「体積計測」の 2 項目を書く。セクション分けはユーザー可視な変更なので、内部リファクタとして黙って通してはならない (MUST NOT)。

### 10.2 PR 分割案

| 案 | 構成 | 長所 | 短所 | 評価 |
| --- | --- | --- | --- | --- |
| **案 1（採用）** | P1〜P5 を 1 本の PR に積む | セクション分けは体積計測のために行うものであり、レビュー観点が「計測セクションを足す」という 1 つの関心事に収まる。Solidify 機能で採った方針（solidify 仕様 §10.2 の決定）と揃う | 変更ファイル 12 本前後 | ○ |
| 案 2 | PR#1 = パネル分割のみ、PR#2 = 体積計測 | PR#1 が純粋な UI リファクタとして独立に読める | 空のセクション分けだけを入れる中間状態が `main` に残る。`ui/panel.py` と `__init__.py` を 2 度触る | △ |
| 案 3 | P1 / P2 / P3 / P4+P5 を 4 本 | 各 PR が小さい | P2 単独では機能が使えず、P3・P5 の PR が細かすぎる | × |

**決定（2026-08-14, orchestrator）: 案 1 を採る。** ブランチは `feature/20260814/volume-measurement` 1 本とし、P1〜P5 をコミット分けで積んで PR は 1 本にする。

### 10.3 検証手順

1. P1 完了時 → `uv run pytest tests/silicone_molding/core -v` が緑（AC-1 〜 AC-30）
2. P2 完了時 → `just test` が緑（AC-31 〜 AC-65 を追加）
3. P3 完了時 → `just blender-test` が緑（AC-66 〜 AC-70）
4. P4 → `just dev` で AC-71 〜 AC-82 を手で確認し、結果を PR 本文に書く
5. 最終 → `just run` と `just blender-test`（AC-83・AC-84）

`just run` の format フェーズはリポジトリ全体を対象にするため、`tests/` に無関係な整形差分が出ることがある。テストを触れない立場で作業している場合は `git status --short` を確認する。

### 10.4 コードレビューのチェックリスト（自動検証できない項目）

- [ ] `SILMOLD_PT_measurement.draw` の中に `total_volume` / `world_volume` / `evaluated_depsgraph_get` / `to_mesh` / `cubic_units_to_ml` の呼び出しが **無い**（FR-25）
- [ ] `draw` の中で `format_ml` を呼ぶのが 1 箇所だけであり、その結果が `text=` と `OperatorProperties.value` の両方に渡っている（FR-48）
- [ ] 計測オペレータの `execute` の中に `Depsgraph.update()` の呼び出しが無い（FR-22）
- [ ] `execute` の中で `context.evaluated_depsgraph_get()` を呼ぶのが 1 箇所だけである（FR-23）
- [ ] `bpy.data.meshes.new_from_object` を使っていない（FR-15）
- [ ] `core/volume.py` の `to_mesh_clear()` が `finally` の中にあり、早期 return の経路でも通る（FR-16）
- [ ] `core/volume.py` の import が `# isort: off` ブロックで `bpy` → `bmesh` の順に固定され、理由がコメントされている（§5.2）
- [ ] `core/` の中にユーザー向けのエラー文言を組む処理が無い（§5.2 の「メッセージの所有者」）
- [ ] エラーメッセージの名前列挙に上限があり、上限値が名前付き定数になっている（FR-34）
- [ ] `{"CANCELLED"}` を返す前に `volume_measured = False` を書いている理由がコメントされている（§5.4）
- [ ] `execute` に `measured_count == 0` の分岐が無い（FR-37）
- [ ] `SILMOLD_PT_main.draw` が layout に何も追加していない（FR-2）
- [ ] サブパネルに `bl_category` が定義されていない（FR-5）
- [ ] `_CLASSES` の「順序は cosmetic」というコメントが訂正されている（§5.10）
- [ ] `SILMOLD_PT_processing.draw` が移設前のプロパティ行・ボタン・アイコン・順序を保っている（FR-9）
- [ ] ハンドラ登録（`depsgraph_update_post` 等）、タイマー、キャッシュが一切入っていない（N-5・FR-36）
- [ ] `volume_ml` に `unit=` が付いていない（FR-29）

______________________________________________________________________

## 11. 未解決事項

| ID | 内容 | 推奨案 | 判断者 / 期限 |
| --- | --- | --- | --- |
| **OQ-1** | スナップショットが古くなっていることをユーザーが見分けられない（L-1）。緩和策を入れるか | **今回は何もしない (MUST NOT、N-5)**。緩和の選択肢は、軽い順に (a) 結果行に「計測時の対象オブジェクト数」を添える、(b) 選択が変わったら `volume_measured` を偽に戻す（`draw` から選択のハッシュを比べる形なら handler 不要）、(c) `depsgraph_update_post` で無効化。実際に誤読が起きたら (a) → (b) の順で検討する。(c) は投機的複雑性として採らない | ユーザー / 実際に使ってみてから |
| **OQ-2** | `volume_ml` / `volume_measured` が `.blend` に保存され、開き直したときに前回の結果が表示される。これでよいか | **そのままでよい (SHOULD)**。シーンが変わっていなければ正しい値であり、保存を打ち消すには `load_post` ハンドラが必要になる（N-5 の方針に反する）。誤読の懸念は OQ-1 と同じ性質なので、対処するなら OQ-1 と一緒に決める | ユーザー / OQ-1 と同時 |
| **OQ-3** | 選択にカーブ・テキスト等の非メッシュジオメトリが含まれるとき、黙ってスキップするか通知するか（L-7） | 今回は **黙ってスキップ (FR-11)**。ライト・カメラが選択に混ざるのは日常的で、通知は騒がしい。カーブを扱う造形ワークフローが出てきた時点で「カーブは Convert to Mesh してから」と案内するか、専用の扱いを決める | ユーザー / 後続機能の仕様策定時 |
| **OQ-4** | `operators/solidify.py` の `_selected_meshes` と `total_volume` 内のメッシュフィルタが同じ判定を 2 箇所で持つ。共通化するか | **今回は共通化しない (SHOULD NOT)**。共通化すると `operators/solidify.py` がモジュール B の変更対象に加わり、並列実装の排他性が崩れる。判定は 1 行であり、抽象を足す価値が薄い。3 箇所目が現れたら共通の置き場（`core` か `operators/_selection.py`）を決める | 実装者 / 3 箇所目が現れた時点で再提起 |
| **OQ-5** | 自己交差・法線の向きの不統一（L-2・L-3）を検出する責務をどこに置くか | 独立した「型の検査」機能の側に置く。本仕様では扱わない。solidify 仕様 OQ-5 と同じ受け皿になる | 後続機能の仕様策定時 |

**取り下げた未解決事項**: 改訂前の OQ-1（エラー行の表示上限）は、エラーがパネル行から `self.report` の 1 行に移ったため FR-34 として確定した。改訂前の OQ-2（Measurement を `DEFAULT_CLOSED` にするか）と OQ-3（キャッシュの再検討条件）は、描画ごとの計測が無くなり性能上の動機が消えたため取り下げ、開いた状態で確定（FR-6）。

______________________________________________________________________

## 12. 将来の拡張余地

今回スコープ外だが、設計上ふさぐべきでない方向:

- E-1. **計測項目の追加**（表面積、寸法、重心、パーツ数）。`VolumeSummary` にフィールドを足し、`Scene` に `<項目>` と `<項目>_measured` の対を足す形で伸ばせる。`SILMOLD_OT_copy_value` を体積に紐づけない中立な名前にしてあるため、追加した行からもそのまま使える。項目が 3 つを超えたら `measured` フラグを 1 つに統合するか、計測結果を `PropertyGroup` の入れ子にまとめる整理を検討する
- E-2. **オブジェクトごとの内訳表示**。`total_volume` を「1 オブジェクト 1 行の結果の並び」を返す形に広げれば対応できる。現在の `VolumeSummary` はその集約結果とみなせるので、破壊的な変更にはならない。表示側は `UIList` か折りたたみ可能な入れ子サブパネルになる
- E-3. **比重からの質量表示**。シリコーン（約 1.1 g/cm³）やレジン（約 1.1〜1.2 g/cm³）を選ぶ列挙プロパティを足せば、mL（= cm³）からの掛け算で出せる。比重が g/cm³ で表記されるのに対し保存値が mL であっても、両者は同一量なので係数はそのままでよい。表示単位を mL 固定にしてあるため換算の起点が安定している
- E-4. **注型量の見積もり**（型のキャビティ体積 − マスターの体積）。分割型の機能が入り「どれがキャビティか」を型側が知るようになってから
- E-5. **スナップショットの鮮度表示**（OQ-1 の (a)(b)）。結果と一緒に計測時の対象オブジェクト数や名前を保存すれば、`draw` 側だけで「今の選択と違う」ことを示せる。ハンドラを使わずに実現できる範囲がある
- E-6. **3 つ目以降のサブパネル**（Split / Gate / Inspect など）。`bl_order` を明示する方針にしてあるため、間に挿入するときも既存の順序を壊さずに済む
- E-7. **サブパネルのさらなる入れ子**。Blender はサブパネルの子も描画できる。Processing が肥大化したら Solidify / Split に分けられる
- E-8. **他の値へのコピー機能の再利用**。`SILMOLD_OT_copy_value` は文字列を受け取るだけなので、寸法・面数・見積もりコストなど、今後表示するどの値からも使える

______________________________________________________________________

## 13. 改訂履歴

### 13.1 2026-08-14 — 起動方式の変更（`draw()` 常時再計算 → ボタン起動 + 結果保存）

ユーザーによる設計変更。「ボタンを押して体積計算を行い、表示された結果をクリックでコピーする」方式に変更した。

**変わったもの**

| 項目 | 改訂前 | 改訂後 |
| --- | --- | --- |
| 計測の起動 | `Panel.draw` のたびに再計算 | `SILMOLD_OT_measure_volume` の押下時に 1 回 |
| 結果の保持 | 保持しない（毎回計算） | `Scene.silicone_molding.volume_ml` / `volume_measured` |
| `draw` の責務 | depsgraph 評価・`to_mesh`・体積計算・整形 | 保存された値の整形のみ（`format_ml` だけを使う） |
| 非 watertight の伝達 | パネル内のエラー行（最大 3 行 + 残り件数） | `self.report({"ERROR"}, ...)` + `{"CANCELLED"}`（名前は最大 3 件 + 残り件数） |
| 結果オブジェクト方式の根拠 | 「`draw` に `try` / `except` を持ち込めないから」 | 「原因オブジェクト名を複数運べるから」（`measured_count` も同時に運べる） |
| 「メッシュ 0 個」の扱い | パネルに `--` を表示 | `poll` が偽（ボタンがグレーアウト） |
| `--` の意味 | 「選択にメッシュが無い」 | 「未計測」 |
| 性能の議論 | リドローごとのコスト。折りたたみが実質のオプトアウト | ボタン 1 回あたりのコスト。リドローは float を読むだけ |
| tier 2 の検証方法 | 値が `draw` の中にしか無いため extension モジュールを import する必要があった | `bpy.ops` と RNA だけで到達できる（import 不要） |
| 受け入れ基準 | 計測ロジックの多くが「レビューでの目視」扱い | 大半が tier 1 で自動検証可能（§9.4） |

**変わらなかったもの**

- `core/units.py` の `cubic_units_to_ml` / `format_ml` の契約
- `core/volume.py` の `world_volume` / `VolumeSummary` / `total_volume` の契約（呼び出し元が `draw` からオペレータに移っただけ）
- `to_mesh()` / `to_mesh_clear()` を使う方針、`Depsgraph.update()` を呼ばない方針、`BMesh.calc_volume()` と行列式によるワールド体積、体積の単位換算（この時点の表記は cm³。§13.3 で mL に改めたが計算は不変）
- サブパネル 2 つによるセクション分け（`bl_idname`・`bl_order`・登録順の制約を含む）
- コピーオペレータの仕様（`StringProperty`、`window_manager.clipboard`、単位なしの数値文字列、`UNDO` を含めない、`REGISTER` + `INTERNAL`）
- §5.11 の実測事実（`draw` 前提だった記述は文脈のみ読み替え）

**新たに生じた限界事項**: 結果がスナップショットになり、シーンの変更で自動更新されない（L-1）。緩和は §11 OQ-1。

### 13.2 2026-08-15 — 実装で判明した実行時事実に合わせた AC の訂正

実装とテストが完了し `just run`（123 passed / pyright strict 0 errors）と `just blender-test`（6/6、実 Blender 5.2）が緑になった時点で、**受け入れ基準の書き方が実行時の挙動と食い違っている箇所** が 5 件見つかった。

**FR は 1 つも変更していない。実装も変更していない。** 訂正したのは AC の検証方法と §5.11 の実測事実表であり、機能の振る舞い（GUI で赤いエラーが出る、`{"CANCELLED"}` を返す、など）は当初の仕様どおりである。

| # | 訂正前の記述 | 実測された事実 | 訂正後 |
| --- | --- | --- | --- |
| 1 | AC-43 / AC-44 / AC-69 が `{"CANCELLED"}` を assert していた | `self.report({"ERROR"}, ...)` を呼ぶと `bpy.ops` 経由では戻り値が届かず `RuntimeError` が送出される。`WARNING` では起こらない。**`poll` 失敗も同じ例外型** | `pytest.raises(RuntimeError)`（`match` なし）+ 観測可能な副作用で受ける。`execute` への到達を Arrange の `poll` assert か `volume_measured = True` の仕込みで担保することを MUST 化。tier 2 は `try` / `except RuntimeError` |
| 2 | AC-55 が `SILMOLD_OT_copy_value.bl_rna.properties` を読んでいた | `Operator.bl_rna` は Blender 自身の `Operator` 構造体 RNA（14 項目）に解決され、宣言したプロパティを含まない。`PropertyGroup.bl_rna` は素直に返すので非対称 | `bpy.ops.silicone_molding.copy_value.get_rna_type().properties` を読む。AC-57 / AC-58 の `PropertyGroup` 側はそのままで正しい |
| 3 | AC-64 / AC-65 が `cls.bl_options` / `poll` の存在を前提にしていた | `bpy.types.Panel` は両者を基底に持たず、宣言しなければ `AttributeError` | `getattr(cls, "bl_options", frozenset())` と `not hasattr(cls, "poll")` |
| 4 | （記載なし） | `obj.scale` 代入直後の `obj.matrix_world` は stale で行列式が 1.0 になる。depsgraph 取得でフラッシュされる | §5.11 に追記。期待値を `matrix_world` から導出すると両辺が stale になり「通るのに何も検証しない」テストになる、という警告を添えた |
| 5 | §5.11 が「想定コード形状で pyright strict 0 エラー」と書いていた | 検証したのは `OperatorProperties` への **代入** 側だった。オペレータ自身の `StringProperty` を `self.value` として **読む** 側は 2 件落ちる（`_PropertyDeferred` のジェネリック引数が未解決） | §5.5 に `value = cast(str, self.value)  # pyright: ignore[reportUnknownMemberType]` の 1 行を MUST として明記。§5.11 の該当行にも但し書きを追加 |

**この 5 件から得た教訓（§13.2）**: 仕様執筆前の実測（§5.11）は当初 15 項目あり、そのうち 1 件も外れなかった。外れたのは **実測しなかった項目** — 具体的には「オペレータを `bpy.ops` 経由で呼んだときの戻り値の届き方」「RNA のイントロスペクション経路」「`bpy.types` の基底クラスが持つ属性」という、いずれも *検証コードの書き方* に属する領域である。次の仕様では、機能の挙動だけでなく **受け入れ基準に書こうとしている assert そのもの** を 1 度実測することが、同種の食い違いを防ぐ最短経路になる。1・2・3・4 は他機能にも波及するため `memory/knowledge_blender_geometry_api_facts.md` へ反映済み。

### 13.3 2026-08-16 — 表示単位を cm³ 表記から mL 表記へ

ユーザーの指示「cm3 ではなく、mL で出してください」による。

**数値と計算は一切変わっていない。** 1 cm³ = 1 mL は定義上の同一量であり、換算式 `volume * (scale_length * 100) ** 3` も、その導出（BU³ → m³ → cm³）も、`f"{value:.2f}"` の書式も、すべてのテストの期待値（`"8.00"` / `"16.00"` など）もそのままである。変わったのは **表記と識別子だけ** であり、コピーされる文字列は元から単位を含まないため（FR-44）まったく影響を受けない。

| 種別 | 変更前 | 変更後 |
| --- | --- | --- |
| Scene プロパティ（公開 API） | `volume_cm3` | `volume_ml` |
| `core/units.py` の換算関数 | `cubic_units_to_cm3` | `cubic_units_to_ml` |
| `core/units.py` の書式化関数 | `format_cm3` | `format_ml` |
| パネルの左ラベル | `Volume (cm3)` | `Volume (mL)` |
| 成功時の `INFO` 報告 | `8.00 cm3 from 1 object(s)` | `8.00 mL from 1 object(s)` |

**識別子まで変えられたのは、このタイミングだけだった。** `volume_cm3` は NFR-4 で公開 API と定めたプロパティ名であり、`.blend` に焼き付く。PR #3 が **まだマージされていない** ＝ この名前を含むリリースがまだ存在しない時点だったため、互換性の負債をゼロにして改名できた。マージ後だったら選択肢は「`volume_cm3` という名前のまま mL と表示する」（名前と表示の恒久的な不一致）か「移行コードを書く」のどちらかになっていた。**公開 API の命名は、最初のリリースの前が唯一のノーコスト訂正機会である。**

**次元計算の文脈では cm³ 表記を残した。** §5.1 の換算の導出（「BU³ → m³ が `scale_length ** 3` 倍、m³ → cm³ が 10⁶ 倍」）と §12 E-3 の比重（g/cm³）は、単位系としての正しさが表記に依存するため cm³ のまま置き、「1 cm³ = 1 mL なので係数はそのまま」と等価であることを添える形にした。§2 の用語定義にこの使い分けを明文化してある。数式の正しさを、表記の統一より優先している。
