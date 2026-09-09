# カードラッシュ

> source slug: `cardrush`
>
> 状態: 見送り
>
> 最終確認日: 2026-09-09
>
> 調査者: Codex

## 概要

カードラッシュは株式会社RUSHが運営するポケモンカード専門店で、公式買取案内からRUSH Media上の買取表へ案内している。買取表はNext.jsの初期HTMLに構造化JSONを含み、カード番号、価格、更新日時、source内IDを取得できる。一方、運営会社のデータ利用方針は正式提携を除く価格情報の自動取得を明示的に禁止している。

- 運営主体: 株式会社RUSH
- 店舗・支店: 通販および実店舗。公開買取価格は全店舗共通と記載
- 対象TCG: ポケモンカードゲーム
- 主なURL: [公式買取案内](https://www.cardrush-pokemon.jp/page/40)、[買取表](https://cardrush.media/pokemon/buying_prices)
- 提供する価格種別: 買取価格

運営主体は[運営会社情報](https://cardrush.media/corporation)と[特定商取引法に基づく表記](https://www.cardrush-pokemon.jp/info)で確認した。

## データ形式

| 項目 | 確認結果 |
| --- | --- |
| 形式 | Next.jsのSSR HTML内にJSONを埋め込む |
| 公開・非公開の別 | 公開表示。ただし自動取得は禁止 |
| JavaScript実行の必要性 | 初回100件の抽出には不要。画面内の検索・sort・paginationには使用される |
| pagination | `limit=100&page=<n>`。確認時の画面は122ページ |
| source内ID | `id`、`pokemon_ocha_product_id`、`ocha_product.id` |
| カード名 | `name` |
| カード番号 | `model_number` |
| セット | `pack_code`と`pack_name`。欠損する行がある |
| レアリティ | `rarity`。欠損を示す値がある |
| 版・言語 | `extra_difference`に未開封、1ED、アンリミ等が混在。言語の専用項目は未確認 |
| 価格 | `amount`に整数円 |
| 状態条件 | レコード別の状態項目はない。査定時の在庫と状態で価格が変わる |
| 公開日時 | `updated_at`と画面上の時点表示がある |
| 有効期限 | 未確認 |
| 更新頻度 | 公式買取案内に「毎日更新中」と記載 |

カード番号だけでは版違いを誤結合するため、`model_number + rarity + extra_difference + pack_code`を最低限の照合候補とする。

## 取得と利用上の制約

| 確認項目 | 結果 | 確認日 | 根拠URL・箇所 |
| --- | --- | --- | --- |
| robots.txt | `cardrush.media`では買取表pathを明示禁止していない。通販ドメインは一般UAを許可するが一部botを個別禁止 | 2026-09-09 | [RUSH Media robots.txt](https://cardrush.media/robots.txt)、[通販robots.txt](https://www.cardrush-pokemon.jp/robots.txt) |
| 利用規約 | サービスから得た情報の商業利用などを禁止 | 2026-09-09 | [RUSH Media利用規約 第4条](https://cardrush.media/terms#第4条（禁止事項）) |
| 自動アクセス | 正式提携を除き、プログラム等によるアクセス、価格・コンテンツ取得、提供インターフェイス以外からのアクセスを禁止 | 2026-09-09 | [データ利用方針「価格情報等について」](https://cardrush.media/data_policy#価格情報等について) |
| 取得データの保存 | 提携なしの取得自体が禁止。保存期間と内部利用の許諾も明文がなく、個別合意が必要 | 2026-09-09 | [データ利用方針](https://cardrush.media/data_policy) |
| fixtureの保存・共有 | 独自コンテンツの無断使用を禁止。rawまたは縮約fixtureの許可範囲は個別合意が必要 | 2026-09-09 | [データ利用方針「コンテンツの取り扱い」](https://cardrush.media/data_policy#コンテンツの取り扱い) |
| 推奨取得間隔 | 設定不可。提携なしの自動取得は頻度によらず禁止。提携時に個別合意が必要 | 2026-09-09 | [データ利用方針](https://cardrush.media/data_policy) |
| 認証・Cookie | 買取表の表示は未認証で可能。自動取得の例外にはならない | 2026-09-09 | [買取表](https://cardrush.media/pokemon/buying_prices)、[データ利用方針](https://cardrush.media/data_policy) |

データ利用方針は株式会社RUSHが運営する全Webサイトを対象とし、通販ドメインも対象サイトとして列挙している。robots.txtの許可状態よりデータ利用方針を優先し、正式提携なしでは自動取得、raw artifact保存、fixture作成を行わない。価格情報の連携は[問い合わせフォーム](https://cardrush.media/contact?subject=%E4%BE%A1%E6%A0%BC%E6%83%85%E5%A0%B1%E7%AD%89%E3%81%AE%E9%80%A3%E6%90%BA%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6)から相談するよう案内されている。

## 代表サンプル

- 確認したURLまたはローカルartifact ID: [ポケモンカード買取表](https://cardrush.media/pokemon/buying_prices)
- 確認日: 2026-09-09
- 保存可否: 正式提携なしでは保存しない。ローカルartifactとfixtureは作成していない
- 必須項目の取得可否: TCG、カード名、カード番号、価格種別、金額、通貨、更新日時、source内IDを取得可能。セット・レアリティには欠損がある
- 同じカードを他店舗と照合できるか: `026/PLAY`は未開封と通常、`067/082`と`047/048`は1EDとアンリミが各2候補になった。`model_number + rarity + pack + extra_difference`を揃えれば比較候補になるが、状態条件の等価性は別途確認する
- 欠損可能な値: pack、レアリティ、言語、レコード別状態、有効期限。TCG、価格種別、通貨、取得日時、原本URL、parser versionはsource metadataまたは取込設定から補う
- 想定されるparser変更リスク: 中。Next.jsのbuild、埋込JSONの配置・key、欠損値に依存する

## 取得設計案

- fetch方法: 正式提携後、合意されたAPI、file、または画面インターフェイスだけを使用する
- 差分取得方法: 提携条件と提供仕様に従う
- timeout・再試行: 提携条件とrate limitに従う
- 0件の意味: 提供仕様を確認して定義する
- 構造変更の検知: schema、必須key、件数、更新日時を検査する
- 重複防止に使える値: `source item id + amount + updated_at + artifact`を候補とする
- source固有の注意事項: 現在閲覧できるSSR内JSONを、提携前の実装対象にしない

## 判断

- 推奨状態: 見送り
- 理由: 技術的には必要項目を取得しやすいが、正式提携なしの自動取得が明示的に禁止されている
- 再検討条件: 正式提携により、取得方式、用途、保存期間、raw artifact、fixture、rate limit、表示・再利用条件を文書で合意する
- 関連ADR: [ADR-0009](../adr/0009-pokemon-mvp-sources.md)
