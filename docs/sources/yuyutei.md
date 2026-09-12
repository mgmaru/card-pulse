# 遊々亭

> source slug: `yuyutei`
>
> 状態: MVP採用
>
> 最終確認日: 2026-09-11
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
| robots.txt | 一般user agent向けの`Disallow`と`Crawl-delay`はない。特定botだけに1〜20秒のdelay指定がある | 2026-09-11 | [yuyu-tei.jp/robots.txt](https://yuyu-tei.jp/robots.txt)、[img.yuyu-tei.jp/robots.txt](https://img.yuyu-tei.jp/robots.txt) |
| 利用規約 | サイトの画像・文章・コンテンツの権利帰属と無断転載禁止を明記 | 2026-09-11 | [利用規約「著作権について」](https://yuyu-tei.jp/info/rule) |
| 自動アクセス | 許可・禁止の明文を確認できず不明。robots.txtを利用許諾とは扱わない | 2026-09-11 | [利用規約](https://yuyu-tei.jp/info/rule)、[robots.txt](https://yuyu-tei.jp/robots.txt) |
| 取得データの保存 | 抽出した価格・識別子の内部保存は許可・禁止とも明文なし。生HTML、画像、説明文の無断利用は行わない | 2026-09-11 | [利用規約「著作権について」](https://yuyu-tei.jp/info/rule) |
| fixtureの保存・共有 | 公開条件上の許諾範囲は不明。[ADR-0012](../adr/0012-private-personal-operation.md)により、生HTMLとsource由来fixtureは本人のGit管理外領域だけに保存し、共有しない | 2026-09-11 | [利用規約「著作権について」](https://yuyu-tei.jp/info/rule) |
| 推奨取得間隔 | 公式値なし。MVPでは対象ページを日次1回以下、逐次かつrequest間隔60秒以上とする | 2026-09-11 | [robots.txt](https://yuyu-tei.jp/robots.txt)、[買取価格について](https://yuyu-tei.jp/info/buy_10.php) |
| 認証・Cookie | 公開価格の閲覧に認証は不要。Cookie利用自体は明記されている | 2026-09-11 | [Cookieポリシー](https://yuyu-tei.jp/info/cookie) |

自動取得、抽出値の内部保存、raw artifactの保持、fixtureの非公開・公開共有を許可する公開条件は確認できていない。[ADR-0012](../adr/0012-private-personal-operation.md)の個人・非公開境界で、本人のローカル環境からだけ取得、raw artifact保存、再解析を行う。

2026-09-11に識別可能な調査用User-Agentと通常のUser-Agentでカード詳細を各1回確認し、いずれも未認証の通常GETで`200`を返した。応答はsessionとXSRF用Cookieを設定し、`Cache-Control: no-cache, private`を返すが、条件付きGETに使えるvalidatorと公開rate limitは確認できなかった。この少数確認は継続取得の許諾または安定性保証には使わない。

## 個人・非公開MVPの判断

- 対象HTMLの未認証取得とカード識別項目の抽出は技術的に可能である
- User-Agent、取得頻度、raw artifactと抽出履歴の保持、sanitized fixture、Card Diggerへの派生集計、停止・削除条件は公開条件で確認できない
- [ADR-0012](../adr/0012-private-personal-operation.md)により、許諾済みとは扱わず、本人のローカル環境だけで使う2番目のMVP情報源として採用する

API、取得原本、source由来fixture、抽出値、価格履歴は第三者へ公開または提供しない。利用者の追加、公開、共有、第三者向け提供または販売へ範囲を変える場合は、新しいADRで利用条件を再判断する。

## 代表サンプル

- 確認したURLまたはローカルartifact ID: [UR ピカチュウex](https://yuyu-tei.jp/buy/poc/card/sv08a/10481)、[SAR メガレックウザex](https://yuyu-tei.jp/buy/poc/card/m06/10110)
- 確認日: 2026-09-11
- 保存可否: 公開条件上は不明。MVPでは本人のGit管理外領域だけに保存し、共有しない
- 必須項目の取得可否: TCG、カード名、カード番号、セット、レアリティ、価格種別、金額、通貨、source内ID候補を取得可能。公開日時は取得不可
- 同じカードを他店舗と照合できるか: `メガレックウザex`は同じセットに4候補あったが、`M6 + 110/076 + SAR`では1候補になった。2026-09-11の現行買取価格32,000円は、フルコンプ池袋店35,000円、晴れる屋2とドラゴンスター各25,000円の同一属性と比較できる。状態条件の等価性は確認できないため、掲載条件を保持して別観測として扱う
- 欠損可能な値: 公開日時、有効期限、カード別状態、カード別言語。TCG、店舗、通貨、取得日時、原本URL、parser versionはsource metadataまたは取込設定から補う
- 想定されるparser変更リスク: 中。DOM構造、class、URL、hidden inputに依存する

## 取得設計案

- fetch方法: セット一覧HTMLを日次1回以下、逐次かつrequest間隔60秒以上で取得する。本人の端末またはprivate network内のWorkerだけから実行する
- 差分取得方法: 応答bodyのcontent hashと取得日時を保存し、set code・card ID・表示価格の差を検出する
- timeout・再試行: 逐次実行し、403、429、challengeでは再試行せず停止する。その他の失敗も即時再試行しない
- 0件の意味: HTTP成功、対象セットの存在、一覧コンテナの存在を分け、空一覧だけを正常な0件候補とする
- 構造変更の検知: URL、hidden input、カード番号、名称、価格の相互整合と件数の急変を検査する
- 重複防止に使える値: `source slug + set code + card ID + price + artifact`を候補とする
- source固有の注意事項: 旧価格の打消し表示を現行価格として読まない。Cookieやログイン状態に依存させない

## 判断

- 推奨状態: MVP採用
- 理由: 未認証HTMLからset code、source card ID、カード番号、レアリティ、価格を抽出でき、晴れる屋2と異なる形式の2番目のadapterとして共通契約を検証できる。個人・非公開のローカル利用に限定し、許諾済みとは扱わない
- 停止条件: 403、429、challenge、認証要求、明示的な自動取得拒否、一覧構造の破壊を検出した場合
- 関連ADR: [ADR-0012](../adr/0012-private-personal-operation.md)
