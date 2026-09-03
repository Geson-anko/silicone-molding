---
name: knowledge-test-sensitivity-check
description: 期待値定数を一時的に壊してテストの感度を確かめる手順、pytest のアサーション書き換えキャッシュの罠、文言を検証できないテストの感度は --deselect + --cov-report=term-missing で示す
metadata:
  type: project
---

実装が先に揃っている状態でテストを書いたとき、「本当に検証しているか」を確かめる最短手段は **期待値定数を 1 文字変えて赤になる本数を数える** こと（`ONE_CUBE_CM3 = "8.00"` → `"9.00"` で 5 本落ちる、など）。仕様から手計算した期待値がそのまま緑だと、テストが効いているのか偶然緑なのかを区別できないため。

**罠:** 書き戻した直後の実行が **前の（壊した）ソースの結果を返す**。`"8.00"` → `"9.00"` のようにファイルサイズが変わらず、`cp` での復元が同じ秒に入ると、pytest のアサーション書き換えキャッシュ（`__pycache__/*-pytest-*.pyc`、mtime は秒精度 + size で検証）が無効化されない。

**How to apply:** 感度確認のあとは `find tests -name __pycache__ -type d -exec rm -rf {} +` を挟んでから再実行する。壊す側の編集も、できれば文字数が変わる値にする。

**期待値を持たないテストの場合:** 「例外が出る」ことだけしか assert できないテスト（`self.report({"ERROR"})` 経路など、文言の検証が仕様で禁じられている場合）は、壊す対象の期待値定数が無いので上の手順が使えない。代わりに **そのテストだけを外して該当行が Missing に戻ることを示す**:

```bash
uv run pytest tests/silicone_casting --cov=src/silicone_casting/operators \
  --cov-report=term-missing -q -p no:randomly --deselect "<nodeid>"
```

これで「このテストが実際にその分岐を通している」ことが確定する。`src/` を触れない立場でも実行できる点が利点。

**How to apply:** 分岐の到達だけを目的とするテスト（カバレッジ欠落埋め）を書いたら、必ずこの deselect 比較を 1 回走らせてから報告する。

関連: [[knowledge-operator-rna-and-error-reports]]
