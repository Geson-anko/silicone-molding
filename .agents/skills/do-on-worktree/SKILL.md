---
name: do-on-worktree
description: "メインの作業ツリーを汚さずにサブタスクを隔離実行する。ChatGPT desktop app の Codex Worktree モードを第一選択とし、CLI では git worktree add .worktrees/NAME を使う。worktree ごとに uv sync が要る点、dist/ と Blender ユーザー設定という共有 state の扱い、後始末。Triggers: 'worktree', 'ワークツリー', '別ブランチで試して', '本流を汚さずに', '隔離して実行', '並行して別の作業', 'サブタスクを分けて'."
---

# worktree でサブタスクを隔離する

メインタスクの作業ツリーを汚さずに、別ブランチでの調査・実験・並行実装を行うための手順。

**いつ使うか**: 本流の作業を中断せずに別の変更を試したいとき、複数エージェントに同じ file を触らせたいとき、大きめのリファクタを本流に混ぜずに検証したいとき。

**いつ使わないか**: 読み取りだけの調査（worktree は不要）、同じ file を触らない並列作業（[$maximize-parallels](../maximize-parallels/SKILL.md) の通常の並列で足りる）。worktree は 1 つあたり `uv sync` のコストが乗るので、安易に増やさない。

______________________________________________________________________

## 第一選択: Codex の Worktree モードを使う

ChatGPT desktop app では、新しい Codex chat の開始時に **Worktree** を選び、基点ブランチを指定する。Codex が detached HEAD の worktree を作成し、必要なら **Handoff** で Local と Worktree の間を移動できる。

カスタム subagent は親セッションの作業ディレクトリを共有するため、同じ file を編集しうる subagent を同じ checkout で並列実行しない。分離が必要なら chat 自体を Worktree モードで開始するか、以下の手動 worktree を使う。

______________________________________________________________________

## 手動で作る場合

Codex CLI を使う場合や、特定のブランチ名で長期間残したい場合:

```bash
git fetch origin main
git worktree add .worktrees/<name> -b <種別>/$(date +%Y%m%d)/<slug> origin/main
git worktree list
```

- `.worktrees/` は gitignore 済み
- ブランチ名は [$git-ops](../git-ops/SKILL.md) の規約に従う
- ベースは `origin/main`（ローカル `main` が古い可能性があるため）

### worktree に入ったら最初にやること

```bash
cd .worktrees/<name>
just setup
```

**`uv sync` は worktree ごとに必要**。`.venv` は共有されない。`bpy` wheel は 380MB あるが uv のキャッシュが効くので実際のダウンロードは初回のみ。

______________________________________________________________________

## worktree をまたぐ共有 state に注意

worktree は file system 上は独立だが、以下は **プロセス / OS レベルで共有される**。複数 worktree で同時に触ると結果が不定になる。

| 共有される state                                        | 影響するコマンド                                                           | 対処                                                                                                                          |
| ------------------------------------------------------- | -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Blender のユーザー設定 / インストール済み extension** | `just blender-test`（`extension install-file` がユーザー設定を書き換える） | **同時に走らせない**。1 つの worktree で完了してから次へ。どちらの worktree の zip が入っているか分からなくなるのが最悪ケース |
| **Blender MCP の接続**                                  | `$blender-mcp` 経由の実機操作                                              | MCP サーバーは同時 1 インスタンスのみ。worktree をまたいで同時に使わない                                                      |
| **git のオブジェクトストア / ref**                      | `git switch` 等                                                            | 同じブランチを 2 つの worktree で同時に checkout できない（git が拒否する）                                                   |
| **uv のキャッシュ**                                     | `uv sync`                                                                  | 並行実行に安全。気にしなくてよい                                                                                              |

`just test`（tier 1）と `just type` は worktree 内に閉じるので、複数 worktree で同時に走らせて問題ない。

`dist/` は worktree ごとに独立して作られるので衝突しないが、`just blender-test` は結局 Blender のユーザー設定を触るので上記の制約が効く。

______________________________________________________________________

## 成果の取り込み

worktree で作った変更は独立したブランチに乗っている。取り込み方は 2 通り:

1. **PR にする**: そのまま push して [$github-pr](../github-pr/SKILL.md)。レビューを通す価値がある変更ならこちら
2. **メインの作業ブランチに merge する**: メイン側で `git merge <worktree-branch>`。調査結果を取り込むだけの小さい変更ならこちら

どちらの場合も、取り込む前に worktree 内で `just run` が green であることを確認する。

______________________________________________________________________

## 後始末

```bash
git worktree remove .worktrees/<name>            # 変更が残っていると拒否される
git worktree list                                # 消えたことを確認
git branch -d <種別>/<日付>/<slug>               # 不要ならブランチも消す
```

- 変更を捨ててよいと **明示的に判断できる場合のみ** `--force` を使う。判断がつかないなら残してユーザーに確認する
- `git worktree prune` はディレクトリを手で消してしまった後の後始末用。通常は `remove` を使う
- 使い終わった worktree を放置しない。`git worktree list` に残り続けると、どれが生きているか分からなくなる

______________________________________________________________________

## やってはいけないこと

- worktree 内から `main` に commit する
- 複数 worktree で `just blender-test` を同時に走らせる
- 変更が残っている worktree を確認せず `remove --force` する
- worktree のパスを `.worktrees/` の外に無秩序に作る（gitignore が効かず、後始末も追いにくくなる）
