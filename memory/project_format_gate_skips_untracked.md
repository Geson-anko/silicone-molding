---
name: project-format-gate-skips-untracked
description: just format (pre-commit run -a) は追跡対象のファイルしか検査しないため、新規ファイルは commit するまで違反が表面化しない
metadata:
  type: project
---

`just format` が実行する `pre-commit run -a` の "all files" は **git が追跡しているファイル** の意味であり、untracked のファイルは検査されない。そのため新規ファイルを作った直後に `just run` を通しても green になり、`git add` してコミットした後に初めて ruff-format や codespell の違反が出る。

**Why:** 2026-08-14 の Solidify 機能実装で実際に踏んだ。実装・テストを 4 エージェント並列で書かせ、`just run` が green（55 tests / pyright 0 errors）なのを確認してコミットしたところ、直後に `just format` が ruff-format 2 箇所と codespell 17 箇所で落ちた。原因は、検証時点で `memory/specs/solidify.md` と `tests/silicone_casting/operators/test_solidify_operators.py` が untracked だったこと。CI 側は checkout 済み = 全部追跡対象なので、この取りこぼしは **ローカルでは緑・CI では赤** という形で出る。

**How to apply:** 新規ファイルを含む変更では、`just run` の前に `git add -A` で intent を立てておく（`git add -N` でもよい）。あるいはコミット後にもう一度 `just format` を回して確認する。エージェントに実装させた場合は成果物がほぼ全部 untracked になるので、特に効く。

関連して、`just format` は失敗時にファイルを書き換えるので、`tests/` を触ってはいけないエージェントが `just run` を回すと担当外のファイルに差分が出る。[[feedback_planning_doc_language]] とは別軸の運用上の注意。
