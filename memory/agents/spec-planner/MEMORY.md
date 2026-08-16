# MEMORY (spec-planner)

このエージェント固有のメモリ索引。1 メモリ 1 ファイル、ここには 1 行のリンクだけを置く。
プロジェクト全体で共有すべき知見は `memory/` 直下へ書き、`memory/MEMORY.md` に索引を足す。

## feedback

- [合意事項は蒸し返さない](feedback_decisions_not_reopened.md) — 決定済みの箇条書きは FR へ翻訳するだけ。不明点は仕様書に残さず質問で返す
- [仕様を書く前に実測する](feedback_measure_before_specifying.md) — bpy の挙動を推測で MUST に書かない。scratchpad で実測してから契約を固める
