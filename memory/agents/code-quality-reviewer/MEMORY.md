# MEMORY (code-quality-reviewer)

このエージェント固有のメモリ索引。1 メモリ 1 ファイル、ここには 1 行のリンクだけを置く。
プロジェクト全体で共有すべき知見は `memory/` 直下へ書き、`memory/MEMORY.md` に索引を足す。

## feedback

- [format ゲートが tests/ を書き換える](knowledge_format_gate_touches_tests.md) — `just run` の後は `git checkout -- tests/`。codespell の "BU" 誤検知は既存の赤
- [例外メッセージの所有者は core](knowledge_error_message_ownership.md) — operators は `str(exc)` をそのまま report し、オブジェクト名の prefix を付けない
