---
name: spec-pins-code-shape
description: このプロジェクトの仕様書は式レベルまで MUST / MUST NOT で形を固定するため、リファクタ候補を適用する前に必ず仕様の該当節を読んで衝突を確認する
metadata:
  type: feedback
---

`memory/specs/*.md` は「何を作るか」だけでなく **どう書くか** まで MUST / MUST NOT で固定している。リファクタ候補を思いついたら、**適用する前に仕様の該当節を grep して衝突を確認する**。衝突していたら実施せず、改善提案として報告に回す。

**Why:** 2026-08-15 の体積計測サイクルで、`operators/measure_volume.py` と `operators/copy_value.py` が型エイリアス `OperatorReturn` を feature モジュール `operators/solidify.py` から import している形を見つけた。共有 private モジュール（`operators/_types.py`）へ移すのが素直な構造改善に見えたが、仕様 §5.4 に「`operators/solidify.py` にある型エイリアスを再定義せず、そこから import する (MUST)。`operators/solidify.py` 自体は変更しない (MUST NOT)」と明記されていた。同節は「`_selected_meshes` を import してはならない (MUST NOT)」「`context.selected_objects or ()` をそのまま `total_volume` に渡す (MUST)」まで固定していた。仕様を読まずに「重複排除」として着手すれば、並列実装のファイル排他設計を壊し、レビュー済みの決定を蒸し返すことになっていた。

これは仕様が悪いのではなく、**並列実装のためにファイル境界を仕様側で保証している** 設計である。サイクル終了後にその境界を崩すかどうかは orchestrator の判断であり、リファクタ担当が独断で決めることではない。

**How to apply:**

- 候補を列挙したら、各候補について `grep -n "<関数名やファイル名>" memory/specs/*.md` を打つ。MUST / MUST NOT / 「変更しない」が出たら **報告行き**
- 仕様に「§10.4 コードレビューのチェックリスト（自動検証できない項目）」節がある場合、それが自分の一次成果物である。1 項目ずつ現物と突き合わせ、結果を報告に列挙する
- 「変更ゼロ」は正当な結論になりうる。仕様駆動で書かれた直後のコードは既に品質バーに乗っていることが多い。チェックリスト検証の結果と、見送った提案とその理由を示せば、churn を出さないことが最良の成果である
- 見送った提案には **いつ解禁されるか** を書き添える（例: 「3 箇所目のパネルが増えたとき」「§5.4 の MUST が緩んだとき」）。次のサイクルで判断をやり直さずに済む

関連: [[format-gate-touches-tests]]
