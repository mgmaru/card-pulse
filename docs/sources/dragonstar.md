# ドラゴンスター ネット買取

> source slug: `dragonstar`
>
> 状態: 見送り
>
> 最終確認日: 2026-09-11
>
> 調査者: Codex

## 概要

ドラゴンスターはポケモンカードを含む複数TCGのネット買取価格を公開している。公開表示から商品ID、シリーズ、カード番号、レアリティ、状態Aの参考買取価格を確認できるが、2026-09-11の`CP-0071`再確認では通常のHTTP clientによる一覧、詳細、robots.txtの取得がすべてCloudflare challengeになった。ネット買取価格は実店舗価格と異なり、価格データの自動取得、保存、再利用に関する許諾も確認できない。

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
| 公開・非公開の別 | 公開表示は確認できるが、2026-09-11の通常GETはCloudflare challengeになった。ログイン要求とは区別する |
| JavaScript実行の必要性 | 先行確認ではserver-rendered HTMLから解析できた。再確認時はchallengeとなり、JavaScriptまたはchallenge Cookieへの依存と正規な自動取得方法は未確認 |
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

先行確認でHTMLを読めたことと、`CP-0071`再確認で通常GETがchallengeになったことは取得環境またはCloudflare判定の差を示す。許諾済みの安定した取得経路を確認できるまで、先行確認だけをCollection Workerの成立根拠にしない。

## 取得と利用上の制約

| 確認項目 | 結果 | 確認日 | 根拠URL・箇所 |
| --- | --- | --- | --- |
| robots.txt | `buy.dorasuta.jp`と`dorasuta.jp`の両方で通常の未認証GETが`HTTP 403`、`cf-mitigated: challenge`となり、規則本文を確認できない | 2026-09-11 | [ネット買取robots.txt](https://buy.dorasuta.jp/robots.txt)、[総合サイトrobots.txt](https://dorasuta.jp/robots.txt) |
| 利用規約 | ネット買取固有の規約は確認できない。総合サイトの会員規約は不正アクセス、運営妨害、知的財産権侵害等を禁止し、スクレイピングの明示条項はない | 2026-09-11 | [会員規約](https://dorasuta.jp/member/agreement) |
| 自動アクセス | 許可・禁止の明文とrate limitを確認できず不明。Cloudflare challengeを回避しない | 2026-09-11 | [会員規約](https://dorasuta.jp/member/agreement)、両hostのrobots.txt |
| 取得データの保存 | raw HTML、抽出価格、価格履歴の内部保存を許可・禁止する明文を確認できず不明 | 2026-09-11 | [会員規約](https://dorasuta.jp/member/agreement)、[利用ガイド](https://dorasuta.jp/guideline) |
| fixtureの保存・共有 | 非公開・公開fixtureとも許諾を確認できないため保存・共有しない | 2026-09-11 | [会員規約](https://dorasuta.jp/member/agreement) |
| 推奨取得間隔 | 公式値なし。通常GETもchallengeとなるため自動取得しない | 2026-09-11 | robots.txt取得結果、[商品一覧](https://buy.dorasuta.jp/pokemon-card/product-list) |
| 認証・Cookie | 公開価格の閲覧に認証は不要。買取申込みには会員登録と本人確認が必要。Cookie利用を明記 | 2026-09-11 | [商品一覧](https://buy.dorasuta.jp/pokemon-card/product-list)、[プライバシーポリシー](https://dorasuta.jp/privacy) |

robots.txtを確認できない状態とCloudflare challengeは、取得禁止の規約そのものとは断定しない。一方、技術的な回避を行う根拠にもならない。自動取得、raw artifact、抽出価格の履歴、fixture、第三者提供を許可する公開条件を確認できないため、Collection Workerによる取得を開始しない。

## CP-0071の検証

### 取得安定性

2026-09-11に少数の通常GETで独立再確認した結果、次の対象はすべて`HTTP 403`、`server: cloudflare`、`cf-mitigated: challenge`を返した。通常User-Agentと識別可能な調査用User-Agentのどちらでも詳細ページはchallengeとなった。再試行、JavaScript実行、Cookie取得、challenge回避は行っていない。

| 対象 | 結果 | 判断 |
| --- | --- | --- |
| [ネット買取robots.txt](https://buy.dorasuta.jp/robots.txt) | 403 challenge | 規則本文を確認できず、取得可否をrobotsから判断できない |
| [総合サイトrobots.txt](https://dorasuta.jp/robots.txt) | 403 challenge | 規則本文を確認できない |
| [商品一覧](https://buy.dorasuta.jp/pokemon-card/product-list) | 403 challenge | 通常HTTP clientによる一覧取得の安定性を確認できない |
| [商品詳細](https://buy.dorasuta.jp/pokemon-card/product?pid=634348) | 403 challenge | 通常HTTP clientによる詳細取得の安定性を確認できない |

### 許諾主体と公開窓口

- [利用ガイド](https://dorasuta.jp/guideline)と[特定商取引法に関する表記](https://dorasuta.jp/commerce)は、ドラゴンスターと販売業者を株式会社エイアイツーとして表示する
- [株式会社ジェイフード](https://jfood.co.jp/)はドラゴンスターとECサイトの運営を事業として掲げ、[店舗・ECサイト運営](https://jfood.co.jp/site-operation)で`dorasuta.jp`を掲載する。ネット買取ページからも同社の運営会社ページへリンクする
- ネット買取価格データの権利者、利用許諾者、Cloudflare設定の管理者という両社の役割は、公開書面だけでは確定できない
- 公開窓口は[ドラゴンスター問い合わせ](https://dorasuta.jp/inquiry)と[ジェイフード問い合わせ](https://jfood.co.jp/contact)に分かれるが、[ADR-0012](../adr/0012-private-personal-operation.md)により外部照会は行わない

[特定商取引法に関する表記](https://dorasuta.jp/commerce)は、運営者との通信内容の公開を控えるよう案内している。外部照会は行わないため、この条件を前提とした連絡経路は採用しない。

### 判断

- 推奨状態: 見送り
- 確認済み: `M6 + 110/076 + SAR + メガレックウザex`は既存候補とカード名以外の属性で各1候補に絞れる。状態Aのネット買取参考価格として別条件の観測にできる
- 見送り理由: robots.txtを読めず、一覧・詳細の通常GETも安定しない。価格データとCloudflare設定の許諾主体、User-Agent、頻度、raw、抽出履歴、fixture、Card Diggerへの派生集計、停止・削除条件も公開情報から確認できず、外部照会を行わない
- ADR判断: [ADR-0011](../adr/0011-no-external-source-inquiries.md)でMVP候補に加えないことを決定した
- 再検討条件: MVPの3情報源だけでは比較仮説を検証できず、robots.txt、一覧、詳細を通常GETで安定取得できる場合

## 代表サンプル

- 確認したURLまたはローカルartifact ID: [SAR メガレックウザex](https://buy.dorasuta.jp/pokemon-card/product?pid=703744)、[メガゲンガーex](https://buy.dorasuta.jp/pokemon-card/product?pid=634348)
- 確認日: 2026-09-11
- 保存可否: 不明。ローカルartifactとfixtureは作成していない
- 必須項目の取得可否: TCG、カード名、カード番号、シリーズ、価格種別、金額、通貨、状態、source内IDを取得可能。公開日時は取得不可
- 同じカードを他店舗と照合できるか: `メガレックウザex`はM6に4候補あったが、`M6 + 110/076 + SAR`では1候補になり、先行確認の状態Aネット買取参考価格は25,000円だった。2026-09-11の既存候補では遊々亭32,000円、晴れる屋2 25,000円、フルコンプ池袋店35,000円と属性上は比較できる。チャネルと状態条件を観測ごとに保持し、challenge中の値を最新観測として更新しない
- 欠損可能な値: レアリティが未登録の商品、言語、公開日時、有効期限、更新頻度。TCG、ネット買取チャネル、通貨、取得日時、原本URL、parser versionはsource metadataまたは取込設定から補う
- 想定されるparser変更リスク: 中。HTML構造、ページング、名称中の版表現、「未登録」レアリティに依存する

## 取得設計案

- fetch方法: 現在は実施しない。将来公開条件を満たして再選定する場合は、シリーズ別一覧を低頻度で取得し、必要な項目が一覧で欠ける場合だけ商品詳細を取得する
- 差分取得方法: 一覧と詳細のcontent hash、取得日時、`pid`、状態、表示価格を比較する
- timeout・再試行: 再選定時もchallenge、403、429では再試行せず停止する
- 0件の意味: HTTP成功、シリーズ存在、一覧container、paginationの整合を確認し、空一覧だけを正常な0件候補とする
- 構造変更の検知: `pid`、series、印刷番号、価格、状態の欠損率と件数急変を検査する
- 重複防止に使える値: `source slug + pid + condition + amount + artifact`を候補とする
- source固有の注意事項: `network_buy`として実店舗価格と分ける。参考価格であることと取得日時を保持する。`PN`をカード同定キーにしない

## 判断

- 推奨状態: 見送り
- 理由: カード識別項目は有力だが、robots.txt、一覧、詳細の通常GETがCloudflare challengeとなり、必要な利用条件と許諾主体も公開情報から確認できず、外部照会を行わないため
- 再検討条件: MVPの3情報源だけでは比較仮説を検証できず、robots.txt、一覧、詳細を通常GETで安定取得できる場合
- 関連ADR: [ADR-0012](../adr/0012-private-personal-operation.md)
