# MEMORY (spec-test-author)

このエージェント固有のメモリ索引。1 メモリ 1 ファイル、ここには 1 行のリンクだけを置く。
プロジェクト全体で共有すべき知見は `memory/` 直下へ書き、`memory/MEMORY.md` に索引を足す。

<!-- - [タイトル](file.md) — 一行の要約 -->

- [モディファイア焼き込みテストの落とし穴](knowledge_modifier_bake_tests.md) — float32 由来の体積誤差、空メッシュで落ちる mesh_invariants、data 差し替え前提の fixture 後始末
- [background でのオペレータテスト](knowledge_operator_tests_in_background.md) — 起動時シーンの選択、edit mode 検証、`hasattr(bpy.ops...)` が常に真、batch_remove の segfault
- [体積系テストの fixture](knowledge_volume_test_fixtures.md) — matrix_world は depsgraph flush まで stale、from_pydata で退化メッシュ、退化 fixture には前提テストを添える
- [オペレータの RNA と ERROR report](knowledge_operator_rna_and_error_reports.md) — ERROR report は `bpy.ops` で RuntimeError、クラスの `bl_rna` に props は載らない、Panel の `bl_options` / `poll` は未定義なら属性ごと無い
- [テストの感度確認](knowledge_test_sensitivity_check.md) — 期待値を 1 文字壊して赤の本数を数える。同サイズ・同秒で戻すと pytest のキャッシュが古いまま。文言不検証なら deselect + term-missing
- [テストモジュール名の一意性](knowledge_tier1_test_module_names.md) — `__init__.py` 無し + prepend import mode のため basename 重複で collection error。ミラー規約と衝突する
