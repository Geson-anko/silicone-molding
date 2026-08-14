---
name: ui-string-reachability
description: UI 説明文字列の点検では「その文字列がユーザーに届く経路があるか」を先に確認する。描画されないプロパティの description はツールチップにならない
metadata:
  type: project
---

`bl_description` / `description=` を点検するときは、文言の良し悪しの前に **その文字列が
画面に出る経路があるか** を確認する。

- `PropertyGroup` の `description=` がツールチップになるのは、そのプロパティを
  `layout.prop()` で描画したときだけ。`layout.label()` やオペレータボタンの `text=` で
  値を見せている場合、description は RNA イントロスペクション（Python コンソール、
  テスト）からしか読めず、**ユーザーには一切届かない**
- オペレータの `bl_description` は、`bl_description` があればそれが、無ければクラスの
  docstring がツールチップになる。両方書いてある場合 docstring は死んでいる（=
  docstring は自由に書ける、が二重管理になっていないか見る）

**Why:** 2026-08-15 の体積計測で、仕様が「スナップショットであること（最大の落とし穴）を
`volume_cm3` の description に書いてツールチップで気付けるようにする (SHOULD)」と
指示していた。実装は正しく書いたが、この機能はそのプロパティを `layout.prop()` で
描画しない設計（値は `emboss=False` のオペレータボタンのテキスト）なので、警告が
ユーザーに届く経路が存在しなかった。仕様の意図と実装が両方正しいのに UX 上の穴が
残る、という形。

**How to apply:**

- 点検対象の文字列ごとに「どの操作でこれが出るか」を `ui/panel.py` の `draw` から逆引きする
- 届かない文字列を見つけても **自分で文言を移し替えない**。どこに出すかは UX の判断で、
  仕様の未解決事項（体積計測なら OQ-1）に属することがある。報告に回す
- 逆に、`bl_label` やアイコンは公開 API 寄り・仕様指定寄りなので触らない

関連: [[comment-minimalism]] [[doc-drift-hotspots]]
