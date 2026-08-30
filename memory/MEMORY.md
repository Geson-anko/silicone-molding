# MEMORY

このプロジェクトのメモリ索引。1 メモリ 1 ファイル、ここには 1 行のリンクだけを置く。詳細は各ファイルへ。

エージェント固有のメモリは [agents/](agents/) 配下にある。

## user

- [ユーザー像](user_role.md) — 日本語でやり取り。Blender / 3D プリント / シリコーン造形の実務者

## project

- [プロジェクトの目的](project_purpose.md) — シリコーン造形用の樹脂型を Blender で生成し 3D プリントする
- [既存プロトタイプアドオン](project_prototype_addons.md) — repo 外にある mold_cut / mold_split。次フェーズの移植元
- [format ゲートは untracked を見ない](project_format_gate_skips_untracked.md) — 新規ファイルは commit するまで違反が出ない。ローカル緑・CI 赤の原因
- [Blender ジオメトリ API の実測事実](knowledge_blender_geometry_api_facts.md) — to_mesh / calc_volume / stale な matrix_world / ERROR report が RuntimeError になる件 / RNA イントロスペクション / パネル登録順

## feedback

- [計画・仕様書の言語](feedback_planning_doc_language.md) — 仕様書・AGENTS.md・skill は日本語で書く
- [ユーザー向けドキュメントは後回し](feedback_defer_user_docs.md) — README / docs は依頼されるまで書かない
- [モディファイア出力に golden を作らない](feedback_no_golden_for_modifier_output.md) — Blender 標準モディファイアの結果は不変量だけで検証する
- [常時ライブ更新よりボタン起動](feedback_prefer_explicit_trigger.md) — 計測系は「押して計算 → Scene に保存 → draw は表示だけ」。テスト可能性が跳ね上がる
- [Mixture CalculatorのUI](feedback_mixture_calculator_ui.md) — Nパネル横の広いポップオーバーで開き、Enabled以外の行選択チェックボックスは使わない
- [Surface Cut と loose-part 分離](feedback_surface_cut_and_separation.md) — 1本の統合モディファイアと、評価済みコピーを元と同じコレクションへフラットに出力する分離フロー

## specs

- [Solidify 機能](specs/solidify.md) — 選択メッシュへの固定名 Solidify モディファイアの付与・更新と、bpy.ops 非依存の適用
- [体積計測 / サイドバーのセクション分け](specs/volume_measurement.md) — 親パネル + サブパネル 2 つへの再編と、ボタンで選択メッシュの合計体積を計測し mL で表示・クリックでコピーする機能
- [手入力式シリコーン配合計算表](specs/mixture_calculator.md) — 体積・密度・重量比からA/Bの体積と重量を算出し、行選択・小計・`.blend` 保存に対応
- [STL 出力機能](specs/stl_export.md) — 選択物のみ・モディファイア適用・1000 倍を固定し、オブジェクト名を既定名にする保存フロー
- [Boolean モディファイア追加機能](specs/boolean_modifier.md) — アクティブメッシュへ指定した Operand・Operation・Solver の Boolean モディファイアを追加する

## reference

- [Blender 実行環境](reference_blender_env.md) — ローカル Blender 5.2、Blender↔Python 対応、bpy wheel の OS 対応
