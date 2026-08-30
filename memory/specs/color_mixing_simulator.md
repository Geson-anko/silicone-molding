# シリコーン混色シミュレータ

## 目的

ベースシリコーンの色・透明度・濁りと、任意数の染料の液滴量から混色を近似し、
フラットな結果色・カラーコード・最終的な透明度と濁りを確認できるようにする。
配合は名前付きの複数プロファイルとして `.blend` に保存する。

## 混色計算

色はscene-linear RGBで扱う。ベース色と、現在のベースを使って作成した染料の
1点校正色をチャンネルごとの吸光度 `A = -ln(clamp(color, 1e-6, 1))` へ変換する。
染料の寄与は次の倍率でベース吸光度へ加算し、最後に `exp(-A)` でRGBへ戻す。

```text
concentration = Drops / (BaseVolumeMl * CalibrationDropsPerMl)
contribution = max(CalibrationAbsorbance - BaseAbsorbance, 0)
```

無効行と0滴は無視し、行順に結果が依存しない。校正色がベースより明るい
チャンネルは、染料が明るくしたものとは扱わず寄与0とする。
校正濃度の既定値は経験則の1.0滴/mLとするが、染料ごとの実測値へ変更できる。

全染料は校正濃度に対する実濃度の比を合計し、1.0で上限を取って透明度へ反映
する。したがって既定では、色にかかわらずシリコーン1mLあたり染料合計1滴程度で
不透明になる。

RGBだけでは通常染料と、他の色を薄める白色顔料を区別できないため、染料行には
`White / Lighten` を持たせる。通常染料だけを上記の吸光度混色へ入れ、白色行は
校正色を白の到達色として使う。白色濃度の比で、吸光混色後の色から白の校正色へ
scene-linear RGB上で補間する。複数の白色行があれば濃度加重平均を到達色とする。

```text
opacity = clamp(sum(concentration of all enabled dyes), 0, 1)
white = clamp(sum(concentration of enabled white dyes), 0, 1)
ResultColor = lerp(SubtractiveDyeColor, CalibratedWhiteColor, white)
ResultTransparency = BaseTransparency * (1 - opacity)
ResultCloudiness = BaseCloudiness + (1 - BaseCloudiness) * white
```

色付き染料も校正濃度で`ResultTransparency = 0`になる。白色染料はそれに加えて、
校正濃度で`ResultColor = CalibratedWhiteColor`、`ResultCloudiness = 1`になる。
それ未満は線形補間し、染料固有の差が分かった場合は校正濃度を変更する。

## 保存データとUI

`Scene.silicone_molding` にプロファイルのリストと、最後に選択したプロファイルの
アクティブ行番号を保存する。
各プロファイルは名前、基準体積mL、ベース色、ベース透明度、ベース濁り、
染料リスト、専用のマテリアルを持つ。染料行はEnabled、White / Lighten、名前、
校正色、校正濃度（滴/mL）、実際の滴数を持つ。滴数はfloatで、小数を直接入力
できる一方、スクロールでは1.0ずつ変化する。

サイドバーはMeasurementとProcessingの間にColoringを置く。ボタンから横幅の
広いポップアップを開き、プロファイル、ベース、染料、結果色を番号順に編集・確認
する。結果は材質球をレンダリングせず、減光されない通常のカラースウォッチで
表示する。Hex（sRGB）、sRGB 8-bit、Linear RGBは常時表示し、各値をクリック
するとクリップボードへコピーする。最終的なTransparencyとCloudinessも常時表示
する。入力変更は、そのプロファイルの既存マテリアルへ即時反映する。
プロファイル追加時に専用マテリアルを作り、削除時は適用済みオブジェクトを
壊さないようマテリアル自体は削除しない。

Mixture Calculatorとの連携は、現在の有効行Totalを基準体積へコピーするボタンで
行う。ライブ参照にはしない。Totalが0なら現在値を保持してキャンセルする。

## 材質

Principled BSDFのBase Colorへ計算色、Transmission Weightへ白色不透明化剤を
反映した最終透明度、Subsurface Weightへ最終濁りを設定する。IORは1.41、
Roughnessは0.2、Alphaは1.0固定とする。
選択物への適用は、選択中の全メッシュのアクティブ材質枠を、アクティブ
プロファイルの共有マテリアルで置換する。材質枠がなければ追加する。

## 対象外

スペクトル測色、Kubelka-Munk、多点校正、プロファイルの外部入出力、プロファイル
複製、染料行の並べ替えは扱わない。
