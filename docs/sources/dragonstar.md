# ドラゴンスター ネット買取

> source slug: `dragonstar`
>
> 状態: 保留
>
> 最終確認日: 2026-09-09
>
> 調査者: Codex

## 概要

ドラゴンスターはポケモンカードを含む複数TCGのネット買取価格を公開している。ポケモンカードの価格ページは未認証のHTMLとして閲覧でき、商品ID、シリーズ、カード番号、レアリティ、状態Aの参考買取価格を抽出できる。ただし、ネット買取価格は実店舗価格と異なり、価格データの自動取得、保存、再利用に関する許諾は確認できない。

ネット買取サイトのフッターは[株式会社ジェイフード](https://jfood.co.jp/)を運営会社として案内し、同社もドラゴンスターとECサイトの運営を事業として記載する。一方、総合サイトの[特定商取引法に関する表記](https://dorasuta.jp/commerce)は販売業者を株式会社エイアイツーとする。ネット買取価格データの権利者と許諾窓口がどちらかは未確認である。

- 運営主体: 株式会社ジェイフードと株式会社エイアイツーの役割分担は未確認
- 店舗・支店: ネット買取。実店舗価格とは区別する
- 対象TCG: ポケモンカードゲーム。ほかのTCGも扱う
- 主なURL: [ポケモンカード買取トップ](https://buy.dorasuta.jp/pokemon-card/)、[商品一覧](https://buy.dorasuta.jp/pokemon-card/product-list)、[商品詳細](https://buy.dorasuta.jp/pokemon-card/product?pid=634348)
- 提供する価格種別: ネット買取限定の状態A参考価格

## データ形式

| 項目 | 確認結果 |
| --- | --- |
| 形式 | サーバー側で描画されたHTML。公開JSON、API、PDFは未確認 |
| 公開・非公開の別 | 公開。価格閲覧にログインは不要 |
| JavaScript実行の必要性 | 一覧・詳細の解析には不要。カート等の操作には使用される |
| pagination | 確認時は5,765件、1ページ40件、最大145ページ |
| source内ID | 商品詳細URLの`pid`。例: `634348` |
| カード名 | 取得可能。番号や版の補足が名称内に含まれる場合がある |
| カード番号 | 名称中の印刷番号と`PN`表記を取得可能。`PN`は異なるカードで重複する例があり、単独キーには使えない |
| セット | series IDとシリーズ表示名を取得可能 |
| レアリティ | 取得可能。「未登録」の商品がある |
| 版・言語 | 実画像、プレイ用、ホイル等の補足表示はある。言語の独立項目は未確認 |
| 価格 | 整数円へ変換可能なネット買取参考価格 |
| 状態条件 | 商品詳細で状態Aを確認。傷、へこみ、査定時相場により変動する |
| 公開日時 | 未確認 |
| 有効期限 | 未確認。表示価格は保証されない |
| 更新頻度 | 公式周期は未確認 |

[商品詳細](https://buy.dorasuta.jp/pokemon-card/product?pid=634348)は、シリーズ、カード名、カード番号、レアリティ、`PN`、状態A、価格を同じHTMLに表示する。[買取トップ](https://buy.dorasuta.jp/pokemon-card/)は、掲載価格がネット買取限定で実店舗価格と異なることを明記する。

## 取得と利用上の制約

| 確認項目 | 結果 | 確認日 | 根拠URL・箇所 |
| --- | --- | --- | --- |
| robots.txt | `buy.dorasuta.jp`と`dorasuta.jp`の両方でCloudflare challengeによるHTTP 403となり、規則を確認できない | 2026-09-09 | [ネット買取robots.txt](https://buy.dorasuta.jp/robots.txt)、[総合サイトrobots.txt](https://dorasuta.jp/robots.txt) |
| 利用規約 | ネット買取固有の規約は確認できない。総合サイトの会員規約は不正アクセス、運営妨害、知的財産権侵害等を禁止し、スクレイピングの明示条項はない | 2026-09-09 | [会員規約](https://dorasuta.jp/member/agreement) |
| 自動アクセス | 許可・禁止の明文とrate limitを確認できず不明。Cloudflare challengeを回避しない | 2026-09-09 | [会員規約](https://dorasuta.jp/member/agreement)、両hostのrobots.txt |
| 取得データの保存 | raw HTML、抽出価格、価格履歴の内部保存を許可・禁止する明文を確認できず不明 | 2026-09-09 | [会員規約](https://dorasuta.jp/member/agreement)、[利用ガイド](https://dorasuta.jp/guideline) |
| fixtureの保存・共有 | 非公開・公開fixtureとも許諾を確認できない。書面承諾なしに保存・共有しない | 2026-09-09 | [会員規約](https://dorasuta.jp/member/agreement) |
| 推奨取得間隔 | 公式値なし。許諾を得るまで自動取得しない。許諾後も一覧を日次以下、逐次取得する案を先方と合意する | 2026-09-09 | robots.txt取得結果、[商品一覧](https://buy.dorasuta.jp/pokemon-card/product-list) |
| 認証・Cookie | 公開価格の閲覧に認証は不要。買取申込みには会員登録と本人確認が必要。Cookie利用を明記 | 2026-09-09 | [商品一覧](https://buy.dorasuta.jp/pokemon-card/product-list)、[プライバシーポリシー](https://dorasuta.jp/privacy) |

robots.txtを確認できない状態とCloudflare challengeは、取得禁止の規約そのものとは断定しない。一方、技術的な回避を行う根拠にもならない。自動取得、raw artifact、抽出価格の履歴、fixture、第三者提供について、ネット買取の正式な運営・権利主体から書面回答を得るまでCollection Workerによる取得を開始しない。

## 代表サンプル

- 確認したURLまたはローカルartifact ID: [メガゲンガーex](https://buy.dorasuta.jp/pokemon-card/product?pid=634348)
- 確認日: 2026-09-09
- 保存可否: 不明。ローカルartifactとfixtureは作成していない
- 必須項目の取得可否: TCG、カード名、カード番号、シリーズ、価格種別、金額、通貨、状態、source内IDを取得可能。公開日時は取得不可
- 同じカードを他店舗と照合できるか: `series + printed card number + rarity + title qualifier`を主軸に照合できる見込み。`PN`だけでは自動確定しない
- 想定されるparser変更リスク: 中。HTML構造、ページング、名称中の版表現、「未登録」レアリティに依存する

## 取得設計案

- fetch方法: 書面許諾後、シリーズ別一覧を低頻度で取得し、必要な項目が一覧で欠ける場合だけ商品詳細を取得する。全商品への詳細アクセスを前提にしない
- 差分取得方法: 一覧と詳細のcontent hash、取得日時、`pid`、状態、表示価格を比較する
- timeout・再試行: 許諾条件に従う。challenge、403、429では再試行せず停止する
- 0件の意味: HTTP成功、シリーズ存在、一覧container、paginationの整合を確認し、空一覧だけを正常な0件候補とする
- 構造変更の検知: `pid`、series、印刷番号、価格、状態の欠損率と件数急変を検査する
- 重複防止に使える値: `source slug + pid + condition + amount + artifact`を候補とする
- source固有の注意事項: `network_buy`として実店舗価格と分ける。参考価格であることと取得日時を保持する。`PN`をカード同定キーにしない

## 判断

- 推奨状態: 保留
- 理由: 技術的には有力だが、robots.txtを確認できず、自動取得、原本保存、fixture利用の許諾と契約窓口も未確定
- 再検討条件: 権利主体を確認し、対象URL、User-Agent、頻度、raw artifact、抽出値の履歴、fixture、第三者提供について書面承諾を得る
- 関連ADR: 未作成
