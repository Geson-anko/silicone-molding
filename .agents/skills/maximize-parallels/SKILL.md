---
name: maximize-parallels
description: 独立な tool 呼び出しは同じターンにまとめて並列実行する。並列化可能の判定基準（出力 → 入力の依存なし／共有 mutable state を同時に書かない／tool 固有の排他なし）、典型的に並列化すべきパターン（複数 file の読み取り、独立 exec_command、複数角度の検索、disjoint な subagent 起動）、逐次必須の落とし穴（読み取り→apply_patch 連鎖、同 file への複数編集、依存する出力）、着手前の判定手順。複数タスクに着手する／複数 file を読む／複数エージェントを起動する／長めのコマンド列を組む前に読む
---

# 並列化を最大化する

複数の tool 呼び出しを行うとき、論理的に独立なものは **同じターンに開始**する。通常の tool は `functions.exec` 内で `Promise.all` を使える場合にまとめ、subagent は独立した `spawn_agent` 呼び出しとしてまとめて開始する。

「論理的に可能」とは、対象が **相互に依存していない** こと。以下 3 つを全て満たすときに並列化できる。

## 並列化可能の判定基準

1. **出力 → 入力の依存がない**: 一方の stdout / 戻り値 / 副作用が他方の入力に使われない
2. **共有 mutable state を同時に書き換えない**: 同じ file への並列 `apply_patch`、同じ branch への並列 checkout は不可
3. **tool 固有の排他がない**: Blender のユーザー設定や単一 MCP 接続などを共有する処理は並列禁止。`rg` / `sed` / `git diff` などの読み取りは並列化しやすい

3 つすべて満たす → 1 メッセージに並べる。1 つでも引っ掛かる → 逐次。

## 並列化すべき典型パターン

- **複数 file の読み取り**: 何を読むかが事前に決まっているなら複数の `exec_command` を並列化する。1 件の結果で次の対象を決める場合だけ逐次にする
- **独立な `exec_command`**: `git status` / `git diff` / `git log` のように互いを汚さない情報取得
- **検索の発散**: 複数の角度から同時に探す（`grep "bmesh.ops"` / `grep "bpy.ops"` / `find -name 'test_*.py'`）
- **複数 agent の起動**: 担当領域が disjoint な `spec-driven-implementer × N` と `spec-test-author × N`、独立モジュール毎の `code-quality-reviewer × N` は常に並列。詳細は [$agent-team](../agent-team/SKILL.md)

## このプロジェクト固有の並列化ポイント

- **`just test`（tier 1）と `just type` は並列に回せる**。前者は `.venv`、後者は `uv run --isolated` の使い捨て環境で、互いに触るものが disjoint
- **`just blender-test`（tier 2）は他と並列にしない**。`extension install-file` が Blender のユーザー設定という共有 mutable state を書き換えるため、同時に走らせると結果が不定になる
- **`just format` は単独で回す**。file を書き換えるので、読み取り系と並列にすると読んだ内容が古くなる
- **`src/` の実装と `tests/` のテストは常に並列**。担当エージェントが分かれており file が disjoint

## 並列化してはいけない（逐次必須）パターン

- **読み取り → `apply_patch` 連鎖**: 編集は事前に対象を読む必要がある。同じ file の読み取りと編集を並列にしない
- **同じ file への複数 `apply_patch`**: 後続パッチは前の適用後のテキストを前提にするため逐次にする
- **workdir が異なるコマンド**: 各 `exec_command` に `workdir` を明示し、`cd` の副作用に依存しない
- **依存する出力**: `just build` の生成物を `just blender-test` が食う、`just fixtures` の出力を `just test` が読む、といった連鎖
- **同じ git branch / worktree への並列操作**: 隔離が必要なら [$do-on-worktree](../do-on-worktree/SKILL.md)

## 着手前の判定手順

複数タスクに取り掛かる直前に、頭の中で（必要なら書き出して）これをやる:

1. 各タスクの **入力** と **出力** を 1 行で書き出す
2. あるタスクの出力が別のタスクの入力に現れるか確認する → 現れたら、その 2 つは逐次
3. 同じ file / branch / 設定を書くタスクがないか確認する → あれば逐次
4. 残ったものを 1 メッセージにまとめて発射する

依存があるタスクは「依存グループ」内では逐次、グループ間は並列にできる。5 つのタスクのうち 2 つに依存関係があるなら、3 並列 + 2 逐次であって、全部逐次ではない。
