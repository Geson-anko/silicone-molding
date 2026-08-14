# MEMORY (spec-driven-implementer)

このエージェント固有のメモリ索引。1 メモリ 1 ファイル、ここには 1 行のリンクだけを置く。
プロジェクト全体で共有すべき知見は `memory/` 直下へ書き、`memory/MEMORY.md` に索引を足す。

<!-- - [タイトル](file.md) — 一行の要約 -->

- [bpy の型スタブと数値精度の落とし穴](bpy_typing_and_precision_gotchas.md) — `bpy_prop_collection.get` / `Context.selected_objects` の pyright strict 対策と、float32 由来で体積の相対誤差は ~1e-5 が下限
