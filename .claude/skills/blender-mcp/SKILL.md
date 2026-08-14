---
name: blender-mcp
description: "Blender MCP 経由で実 Blender を触りながら機能を確かめる手順。MCP のセットアップ (.mcp.json / BlenderMCP アドオン / Connect to Claude)、開発中の実機確認ループ (コード変更 → build → install → MCP で操作 → スクショ確認)、同時 1 インスタンス制約、自動テストとの使い分け。Triggers: 'blender mcp', 'Blender で確認', '実機で見たい', '実際に動かして', 'スクリーンショット', 'ビューポート', '目視で確認', 'UI を確認'."
version: 0.1.0
---

# Blender MCP で実機を触る

自動テスト（[/testing-strategy](../testing-strategy/SKILL.md)）が担保できないもの — **UI の見た目、操作感、生成ジオメトリの視覚的な妥当性** — を確かめるための手順。

______________________________________________________________________

## 自動テストとの使い分け

| 確かめたいこと                                     | 手段                                                       |
| -------------------------------------------------- | ---------------------------------------------------------- |
| ジオメトリが仕様どおりか                           | tier 1 (`just test`)。数値で assert できるものは必ずこちら |
| install / 登録 / 実 Blender 上の動作               | tier 2 (`just blender-test`)                               |
| **パネルの配置・ラベル・並び順が意図どおりか**     | **MCP**                                                    |
| **生成された型が「造形として妥当」に見えるか**     | **MCP**                                                    |
| **操作の流れが自然か（選択 → パラメータ → 実行）** | **MCP**                                                    |
| **想定外の形状が出たときの原因調査**               | **MCP**                                                    |

MCP で見つけた問題は、**再現する自動テストに落としてから直す**。MCP での目視確認は探索と最終確認のためのもので、回帰検出の手段にはならない。

______________________________________________________________________

## セットアップ

### 1. MCP サーバー（repo 側）

[.mcp.json](../../../.mcp.json) にコミット済み:

```json
{ "mcpServers": { "blender": { "type": "stdio", "command": "uvx", "args": ["blender-mcp"], "env": {} } } }
```

`.claude/settings.json` の `enableAllProjectMcpServers: true` により承認プロンプトなしで有効になる。`uvx` が PATH に必要（`uv` を入れてあれば入っている）。

### 2. BlenderMCP アドオン（Blender 側 / マシンごとに 1 回）

1. <https://github.com/ahujasid/blender-mcp> から `addon.py` を取得
2. Blender: **Edit → Preferences → Add-ons → Install** で `addon.py` を選択
3. **Interface: Blender MCP** を有効化

このアドオンは開発対象の `silicone_molding` とは無関係な別物。`blender --command extension` の出力に `BlenderMCP addon registered` が混ざるのはこれが原因で、無害。

### 3. 接続

1. Blender を **GUI で** 起動する（MCP は background モードでは使えない）
2. 3D ビューポートで **N** キー → **BlenderMCP** タブ
3. **Connect to Claude** を押す

接続後、Claude Code を再起動していれば `blender` MCP のツールが使えるようになる。

______________________________________________________________________

## 開発中の実機確認ループ

コードを変えてから実機で確かめるまでの最短経路:

```bash
just build                                                    # dist/silicone_molding-<ver>.zip
blender --command extension install-file --repo user_default --enable dist/silicone_molding-$(just version).zip
```

**その後 Blender を再起動する**。Blender は起動中に差し替えた extension のモジュールを再読込しないため、再起動しないと古いコードのまま動く。ここを飛ばして「変更が反映されない」と悩むのが最も多い失敗。

再起動したら **Connect to Claude** を押し直してから MCP で操作する。

### 確認の流れ

1. シーンをリセットして既知の状態から始める（既存オブジェクトが残っていると原因の切り分けができない）
2. マスターとなるメッシュを 1 つ置く
3. サイドバーの **Silicone Molding** タブからパラメータを設定してオペレータを実行する
4. 結果を **スクリーンショットで確認** する。ワイヤーフレーム表示にすると内部構造が見える
5. 数値も取る（頂点数・寸法・体積）。目視だけだと「それらしく見えるが数値が違う」を見逃す

______________________________________________________________________

## 制約と注意

- **MCP サーバーは同時 1 インスタンスのみ**。複数の Claude セッション / worktree から同時に使わない（[/do-on-worktree](../do-on-worktree/SKILL.md) の共有 state の項）
- **`just blender-test` と同時に使わない**。tier 2 は `extension install-file` で Blender のユーザー設定を書き換えるため、MCP 接続中の Blender と食い違う
- **MCP 経由でシーンを壊しても構わない前提で使う**。保存したい作業ファイルを開いた状態で実験しない
- MCP から実行した Python は **Blender のユーザー設定やシーンを永続的に変えうる**。破壊的な操作をする前に、何が起きるかを一言説明してからにする
- Blender のロケールが日本語だと、`primitive_cube_add` が作るオブジェクト名が `立方体` になる。名前でオブジェクトを引くコードを書くときは注意（tier 2 の `run.py` は `source.name` から組み立てることで回避している）

______________________________________________________________________

## うまくいかないとき

| 症状                           | 原因と対処                                                                                                          |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| MCP ツールが見えない           | Claude Code を再起動する。`.mcp.json` が repo ルートにあるか確認                                                    |
| Connect to Claude が繋がらない | 他の MCP インスタンスが動いていないか確認。Blender を再起動して押し直す                                             |
| コードを変えたのに反映されない | `just build` → `install-file` の後に **Blender を再起動**したか                                                     |
| アドオンが有効にならない       | `blender --command extension list` で入っているか確認。`just validate` でマニフェストを検証                         |
| 生成形状が tier 1 と違う       | Blender のバージョン差か、シーンのスケール / 変換行列の影響。`just blender-test` で golden と突き合わせて切り分ける |
