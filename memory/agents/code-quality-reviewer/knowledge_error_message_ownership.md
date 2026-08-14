---
name: error-message-ownership
description: 例外メッセージは core が自己完結して持ち、operators 層は str(exc) をそのまま report する（オブジェクト名を二重に付けない）
metadata:
  type: feedback
---

このコードベースでは **例外メッセージの所有者は `core/`** とする。`core` 側が `f"{obj.name!r} has no ..."` のようにオブジェクト名を含んだ自己完結メッセージを送出し、`operators/` 層は `self.report({"WARNING"}, str(exc))` と **そのまま流す**。オペレータ側で `f"{obj.name}: {exc}"` のような prefix を付けない。

**Why:** Solidify 実装（`b85f0e0` / `f7e4e4e`）で実際に `A: the mesh of 'A' is shared with...` と名前が二重に出た。ユーザーからの明示的な指摘で、「core のメッセージ文言は維持し、オペレータ層の prefix を落とす」方向に決まった。core の文言はテスト（`pytest.raises(match=...)`）で固定されていないので変更自体は安全だが、core を薄くする方向ではなく **core を自己完結させる** 方向が選ばれた点が本質。

**How to apply:** operators 層のレビューで `self.report(..., f"{obj.name}: {exc}")` 系を見たら、core 側の文言を読んで名前が既に入っているか確認する。入っていれば prefix を落とす。逆に新しい core 関数を足すレビューでは、送出する `ValueError` に対象オブジェクト名が入っているかを確認する。

変更前に `git grep -n "match=" tests/` でメッセージの完全一致検証が無いことを確認する習慣をつける（この時点では 0 件）。
