# MEMORY (code-quality-reviewer)

このエージェント固有のメモリ索引。1 メモリ 1 ファイル、ここには 1 行のリンクだけを置く。
プロジェクト全体で共有すべき知見は `memory/` 直下へ書き、`memory/MEMORY.md` に索引を足す。

## feedback

- [format ゲートが tests/ を書き換える](knowledge_format_gate_touches_tests.md) — `git checkout -- tests/` は禁物。スナップショット比較で確認する
- [例外メッセージの所有者は core](knowledge_error_message_ownership.md) — operators は `str(exc)` をそのまま report し、オブジェクト名の prefix を付けない
- [仕様書が式レベルまで形を固定する](knowledge_spec_pins_code_shape.md) — 候補を適用する前に specs を grep する。「変更ゼロ」は正当な結論
