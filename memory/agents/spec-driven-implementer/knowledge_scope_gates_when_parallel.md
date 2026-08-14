---
name: scope-gates-when-parallel
description: 並列実装で仕様がファイル排他に分担されているとき、just type / just test は他エージェントの未完成ファイルで赤くなる。検証を自分の担当ディレクトリに絞り、他モジュールのエラーは直さず orchestrator に報告する
metadata:
  type: feedback
---

`just type` は `src/silicone_molding` 全体、`just test` は `tests/` 全体を対象にする。仕様が
「モジュール A = `core/`、モジュール B = `operators/` + `ui/`」のようにファイル排他で分担されている
並列実装では、**自分の diff が完璧でもゲートは赤くなる**（相手の in-flight なファイルが原因）。

**Why:** 体積計測機能（`memory/specs/volume_measurement.md` §4.3）の P1/P2 並列実装で実際に起きた。
`core/` は pyright 0 エラーだったが `just type` は `operators/copy_value.py` の 2 エラーで落ちた。
これを「自分の責務」と誤認して他エージェントのファイルを直すと、ファイル排他の前提が壊れて
編集が衝突する。

**How to apply:**

- 自分の担当分の型検査は範囲を絞って回す:
  `uv run --isolated --with fake-bpy-module-5.1 --with pyright pyright src/silicone_molding/<自分のディレクトリ>`
- テストも `uv run pytest tests/silicone_molding/<自分の担当> -q` に絞る
- そのうえで `just type` / `just test` を全体で 1 回回し、**残ったエラーが全部他モジュール由来である
  ことを確認**して、ファイル名付きで報告に含める（直さない）
- 報告前に `git status --short` を見て、自分の diff が担当ファイルだけであることを確認する。
  他エージェントの変更が同じ working tree に混ざっているので、diff 全体を自分の成果と誤って要約しない

関連: [[bpy-typing-and-precision-gotchas]]
