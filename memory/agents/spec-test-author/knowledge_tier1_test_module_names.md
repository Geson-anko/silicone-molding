---
name: knowledge-tier1-test-module-names
description: tests/ 配下のテストファイル名は全体でユニークでなければならない（__init__.py が無く pytest が prepend import mode のため）。1 対 1 ミラーと衝突する
metadata:
  type: project
---

`tests/` 配下には `__init__.py` を置かない規約で、pytest は既定の prepend import mode で動くため、**テストモジュールの basename はディレクトリを跨いでユニークである必要がある**。重複すると `import file mismatch` で collection error になり、スイート全体が動かなくなる。

これは「`tests/silicone_casting/` を `src/silicone_casting/` と 1 対 1 でミラーする」規約と正面から衝突する。`src/silicone_casting/core/solidify.py` と `src/silicone_casting/operators/solidify.py` のように **同名モジュールが層をまたいで存在すると必ず起きる**（2026-08-14 の Solidify 機能で実際に発生）。

**How to apply:** 層をまたいで同名の src モジュールにテストを書くときは、`operators/` 側の basename に層名を足す（例: `tests/silicone_casting/operators/test_solidify_operators.py`）。ディレクトリによるミラーは保たれる。

**恒久対策（未適用・要 orchestrator 判断）:** `pyproject.toml` の `[tool.pytest.ini_options]` に `--import-mode=importlib` を足し、`pythonpath = ["src", "tests"]` に広げれば basename の一意性は不要になり、両方 `test_solidify.py` のままにできる。`pythonpath` に `tests` を足すのは必須で、importlib mode ではテストファイルのディレクトリが `sys.path` に入らず `from _helpers import ...` が壊れるため。この構成で 55 テストが緑になることは実測済み。
