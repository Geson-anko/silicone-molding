---
name: format-gate-touches-tests
description: just run の format ゲートは tests/ と memory/ を書き換える・落とすため、tests 不可侵のリファクタでは src だけを個別に検証する
metadata:
  type: feedback
---

`just run` の format フェーズ（pre-commit）はリポジトリ全体を対象にするため、`tests/` 不可侵のリファクタ作業とそのまま噛み合わない。実際に踏んだ 2 つ:

1. **ruff-format が `tests/` を書き換える**。commit 済みのテストが ruff-format 非適合のまま入っていることがあり、`just run` を回すと勝手に整形されて working tree に `tests/` の diff が出る。→ **必ず `git status --short` を確認し、`git checkout -- tests/` で戻す**。
2. **codespell が "BU" を誤検知して Failed になる**。`memory/specs/solidify.md` と `tests/` に出てくる BU（Blender units）が `BY`/`BE`/`BUT`... の typo と判定される。`.pre-commit-config.yaml` の codespell に ignore-words が設定されていないため。commit 済みの内容なので **リファクタ着手前から赤**。

**Why:** どちらも自分の変更とは無関係な既存の赤 / 既存の未整形であり、これを「自分が壊した」と誤認して `tests/` を直しに行くと不可侵ルールを破る。逆に `just run` の赤を理由に作業を止めると、実際には自分のスコープは緑なのに進まなくなる。

**How to apply:** `tests/` を触れない立場でリファクタするときは、`just run` を回す前に「format は全体を対象にする」と織り込んでおく。ゲート確認は
- `just test` / `just type` はそのまま回す（これらは書き換えない）
- format は `uv run pre-commit run ruff-format --files $(git ls-files 'src/**/*.py')` のように **src だけに絞って** 回す（`uv run ruff` は venv に ruff 実体が無いので使えない。pre-commit 経由で呼ぶこと）
- `just run` を回してしまったら直後に `git status --short` → `git checkout -- tests/`

報告時は「src スコープは緑 / format ゲートの赤は既存で `tests/` `memory/` 側」と切り分けて伝える。テスト側の未整形は spec-test-author に、codespell の ignore-words 設定は orchestrator に差し戻す。
