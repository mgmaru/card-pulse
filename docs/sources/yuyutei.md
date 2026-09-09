# 遊々亭

> source slug: `yuyutei`
>
> 状態: 保留
>
> 最終確認日: 2026-09-09
>
> 調査者: Codex

## 概要

遊々亭は株式会社スカラプレイスが運営するTCG通販サイトで、ポケモンカードゲームを含む複数TCGのシングルカード買取価格を公開している。ポケモンカードの価格ページは未認証のHTMLとして取得でき、カード番号、セット、レアリティ、カード名、価格、source内ID候補を同じ原本から抽出できる。

- 運営主体: 株式会社スカラプレイス
- 店舗・支店: オンラインショップ。支店別価格ではない
- 対象TCG: ポケモンカードゲーム。ほかのTCGも扱う
- 主なURL: [ポケモンカードトップ](https://yuyu-tei.jp/top/poc)、[セット別買取一覧](https://yuyu-tei.jp/buy/poc/s/sv08a)、[カード詳細](https://yuyu-tei.jp/buy/poc/card/sv08a/10481)
- 提供する価格種別: 日本語版シングルカードの買取価格

運営主体は[特定商取引法に基づく表記](https://yuyu-tei.jp/info/act)、買取価格の掲載方針は[FAQ](https://yuyu-tei.jp/info/faq/answer?faq_id=11)で確認した。

## データ形式

| 項目 | 確認結果 |
| --- | --- |
| 形式 | サーバー側で描画されたHTML |
| 公開・非公開の別 | 公開。価格閲覧にログインは不要 |
| JavaScript実行の必要性 | 一覧と詳細の解析には不要。買取依頼などの操作には使用される |
| pagination | 確認したセット一覧と検索結果では未検出。全セットで存在しないことは未確認 |
| source内ID | URLとhidden inputに含まれるset codeとcard ID。例: `sv08a/10481` |
| カード名 | 取得可能 |
| カード番号 | 取得可能。例: `236/187` |
| セット | set codeと表示名を取得可能 |
| レアリティ | 取得可能。例: `UR` |
| 版・言語 | 日本語版のみ買取との全体条件はある。カード別の版フィールドは未確認 |
| 価格 | 整数円へ変換可能な表示価格。旧価格が打消し表示される場合がある |
| 状態条件 | プレイ用カードの基準と、状態による減額・買取不可条件がある。カード別状態はない |
| 公開日時 | 未確認 |
| 有効期限 | 公開価格には未確認。価格は常に変動し、依頼完了時点の価格が適用される |
| 更新頻度 | 公式の周期は未確認。「常に変動」と記載 |

カードの状態条件は[カードの状態について](https://yuyu-tei.jp/info/buy_50.php)、価格の確定時点は[買取価格について](https://yuyu-tei.jp/info/buy_10.php)で確認した。HTTP応答ではsessionとXSRF用Cookieが設定されるが、調査した公開価格ページはCookieを返送しない通常のGETでも閲覧できた。

## 取得と利用上の制約

| 確認項目 | 結果 | 確認日 | 根拠URL・箇所 |
| --- | --- | --- | --- |
| robots.txt | 一般user agent向けの`Disallow`と`Crawl-delay`はない。特定botだけに1〜20秒のdelay指定がある | 2026-09-09 | [yuyu-tei.jp/robots.txt](https://yuyu-tei.jp/robots.txt)、[img.yuyu-tei.jp/robots.txt](https://img.yuyu-tei.jp/robots.txt) |
| 利用規約 | サイトの画像・文章・コンテンツの権利帰属と無断転載禁止を明記 | 2026-09-09 | [利用規約「著作権について」](https://yuyu-tei.jp/info/rule) |
| 自動アクセス | 許可・禁止の明文を確認できず不明。robots.txtを利用許諾とは扱わない | 2026-09-09 | [利用規約](https://yuyu-tei.jp/info/rule)、[robots.txt](https://yuyu-tei.jp/robots.txt) |
| 取得データの保存 | 抽出した価格・識別子の内部保存は許可・禁止とも明文なし。生HTML、画像、説明文の無断利用は行わない | 2026-09-09 | [利用規約「著作権について」](https://yuyu-tei.jp/info/rule) |
| fixtureの保存・共有 | 生HTML・画像・本文を含むfixtureは書面許諾なしに保存・共有しない。縮約した構造化fixtureも許諾範囲が不明 | 2026-09-09 | [利用規約「著作権について」](https://yuyu-tei.jp/info/rule) |
| 推奨取得間隔 | 公式値なし。書面許諾を得るまで自動取得しない。許諾後の初期案は対象ページを日次以下、逐次かつ60秒以上の間隔 | 2026-09-09 | [robots.txt](https://yuyu-tei.jp/robots.txt)、[買取価格について](https://yuyu-tei.jp/info/buy_10.php) |
| 認証・Cookie | 公開価格の閲覧に認証は不要。Cookie利用自体は明記されている | 2026-09-09 | [Cookieポリシー](https://yuyu-tei.jp/info/cookie) |

自動取得、抽出値の内部保存、raw artifactの保持、fixtureの非公開・公開共有について、運営から書面で条件を得るまでCollection Workerによる取得を開始しない。

## 代表サンプル

- 確認したURLまたはローカルartifact ID: [UR ピカチュウex](https://yuyu-tei.jp/buy/poc/card/sv08a/10481)
- 確認日: 2026-09-09
- 保存可否: 不明。ローカルartifactとfixtureは作成していない
- 必須項目の取得可否: TCG、カード名、カード番号、セット、レアリティ、価格種別、金額、通貨、source内ID候補を取得可能。公開日時は取得不可
- 同じカードを他店舗と照合できるか: `set code + card number + rarity`を主軸に照合できる見込み。Phase 0のサンプル比較は未実施
- 想定されるparser変更リスク: 中。DOM構造、class、URL、hidden inputに依存する

## 取得設計案

- fetch方法: 許諾を得た後、セット一覧HTMLを低頻度のGETで取得する
- 差分取得方法: 応答bodyのcontent hashと取得日時を保存し、set code・card ID・表示価格の差を検出する
- timeout・再試行: 許諾条件に従う。明示がなければ逐次実行し、失敗時は即時再試行しない
- 0件の意味: HTTP成功、対象セットの存在、一覧コンテナの存在を分け、空一覧だけを正常な0件候補とする
- 構造変更の検知: URL、hidden input、カード番号、名称、価格の相互整合と件数の急変を検査する
- 重複防止に使える値: `source slug + set code + card ID + price + artifact`を候補とする
- source固有の注意事項: 旧価格の打消し表示を現行価格として読まない。Cookieやログイン状態に依存させない

## 判断

- 推奨状態: 保留
- 理由: HTMLから必要な識別項目と価格を取得できるが、自動取得、抽出値の保存、fixture利用の許諾が確認できない
- 再検討条件: 運営から対象path、頻度、保存項目、raw artifact保持、fixture共有を含む書面許諾を得る
- 関連ADR: 未作成
