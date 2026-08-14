---
name: format-gate-touches-tests
description: just run の format ゲートは tests/ と memory/ を書き換える・落とすため、tests 不可侵のリファクタでは src だけを個別に検証する
metadata:
  type: feedback
---

`just run` の format フェーズ（pre-commit）はリポジトリ全体を対象にするため、`tests/` 不可侵のリファクタ作業とそのまま噛み合わない。実際に踏んだのは:

- **ruff-format が `tests/` を書き換える**。commit 済みのテストが ruff-format 非適合のまま入っていることがあり、`just run` を回すと勝手に整形されて working tree に `tests/` の diff が出る。

**`git checkout -- tests/` を反射で打ってはならない。** 並列サイクルの途中では `tests/` に spec-test-author の **未コミットの変更** が載っている（tracked の `M` と untracked の新規テストが混在する）。HEAD に戻すとその成果物が消える。正しい手順は **スナップショット方式**:

1. `just run` の前に `cp -R tests/. <scratchpad>/tests-snapshot/`
2. `just run` を回す
3. `diff -r tests <scratchpad>/tests-snapshot` で差分ゼロを確認する（整形が入ったらスナップショットから戻す）

`git status --short` の行が作業開始時と一致していることも併せて確認する。

（かつてここに書いていた「codespell が BU を誤検知して Failed になる」は解消済み。`.pre-commit-config.yaml` の codespell に `--ignore-words-list=BU` が入っている。）

**Why:** 自分の変更とは無関係な既存の未整形であり、これを「自分が壊した」と誤認して `tests/` を直しに行くと不可侵ルールを破る。逆に `just run` の赤を理由に作業を止めると、実際には自分のスコープは緑なのに進まなくなる。

**How to apply:** `tests/` を触れない立場でリファクタするときは、`just run` を回す前に「format は全体を対象にする」と織り込んでおく。ゲート確認は

- `just test` / `just type` はそのまま回す（これらは書き換えない）
- format を `src/` だけに絞って回すときは **必ず `-z` + `xargs -0` で渡す**:
  `git ls-files -co --exclude-standard -z src/ | xargs -0 uv run pre-commit run --files`
  `--files $(...)` のようにシェル変数経由で渡すと、全フックが `(no files to check) Skipped` になって **緑に見えるが何も検査していない**。`-co --exclude-standard` にすると untracked の新規ファイルも対象に入るので、[[project-format-gate-skips-untracked]] の取りこぼしも同時に潰せる（`uv run ruff` は venv に ruff 実体が無いので使えない。pre-commit 経由で呼ぶこと）
- `just run` を回してしまったら `git status --short` と上のスナップショット比較で `tests/` を確認する

報告時は「src スコープは緑 / format ゲートの赤は既存で `tests/` `memory/` 側」と切り分けて伝える。テスト側の未整形は spec-test-author に差し戻す。
