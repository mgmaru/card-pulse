# フルコンプ

> source slug: `fullcomp`
>
> 状態: MVP選定
>
> 最終確認日: 2026-09-11
>
> 調査者: Codex

## 概要

フルコンプは複数店舗の店頭買取参考価格を公開している。価格表は店舗ごとのHTML記事で、確認したページではJavaScript変数`tableData`に全行が埋め込まれていた。カード番号、set code、レアリティ、価格を抽出できる一方、カード単位のsource内IDがなく、列の意味もHTML上で明示されていない。

フルコンプは店舗群で運営主体と情報公開hostが分かれる。MVP候補は株式会社イントゥ運営の池袋店と`www.fullcomp.jp/ikebukuro/`配下の対象買取表に限定する。株式会社インスパイア運営店舗、別host、他店舗のadapterと利用許諾を同一とみなさない。

- 運営主体: 株式会社イントゥ。MVP候補とする池袋店について確認
- 店舗・支店: 池袋店。価格は他店舗と異なる可能性がある
- 対象TCG: ポケモンカードゲーム。ほかのTCGも扱う
- 主なURL: [買取情報](https://www.fullcomp.jp/kaitori/)、[池袋店の買取情報](https://www.fullcomp.jp/ikebukuro/kaitori/)、[池袋店の価格表](https://www.fullcomp.jp/ikebukuro/kaitori/18872)、[問い合わせ](https://www.fullcomp.jp/contact/)
- 提供する価格種別: 店舗別の店頭買取参考価格

[問い合わせ](https://www.fullcomp.jp/contact/)は池袋店を株式会社イントゥ運営店舗として表示する。`www.fullcomp.jp`側の8店舗が同社運営であることは[フルコンプ秋葉原EC店の会社概要](https://www.fullcomp-akihabara-ec.com/html/company.html)でも確認した。[プライバシーポリシー](https://www.fullcomp.jp/privacypolicy/)は株式会社イントゥと株式会社インスパイアの双方を個人情報の共同利用管理者として列挙するが、価格データの許諾主体を示す根拠には使わない。

## データ形式

| 項目 | 確認結果 |
| --- | --- |
| 形式 | HTML内のJavaScript変数`tableData`。公開APIや独立JSON endpointは未確認 |
| 公開・非公開の別 | 公開。価格表の閲覧にログインは不要 |
| JavaScript実行の必要性 | 画面表示にはDataTablesを使用。データは初回HTML内にあり、解析時のJavaScript実行は不要 |
| pagination | 確認ページでは`tableData`に全行を含み、画面側でページングする |
| source内ID | 記事URLの数値IDはあるがカード単位IDは未確認。行番号はページ内連番 |
| カード名 | 取得可能。カード番号とset codeを同じ文字列に含む |
| カード番号 | 取得可能 |
| セット | set codeを名称中から取得可能。正式セット名は未確認 |
| レアリティ | 取得可能 |
| 版・言語 | 独立項目は未確認。日本語の店頭買取表として扱う |
| 価格 | 整数円へ変換可能な店舗別参考価格 |
| 状態条件 | 完品・美品の満額査定。状態、在庫、相場により減額、変更、停止、返却がある |
| 公開日時 | 記事の更新日と価格表の基準日を取得可能。時刻は未確認 |
| 有効期限 | 有効期限があると案内するが、具体的な期限は未確認 |
| 更新頻度 | 店舗・価格表ごとに更新履歴がある。固定周期は未確認 |

[池袋店の価格表](https://www.fullcomp.jp/ikebukuro/kaitori/18872)は更新日、カード種別、属性、レアリティ、カード名、カード番号、set code、価格を含む配列を持つ。ただし表の列見出しが空であり、列の意味は値と画面表示からの推定を含むため、別店舗・旧弾ページを使ったschema比較が必要である。

## 取得と利用上の制約

| 確認項目 | 結果 | 確認日 | 根拠URL・箇所 |
| --- | --- | --- | --- |
| robots.txt | `Disallow: /wp/wp-admin/`とsitemapを記載し、池袋店の買取表pathを禁止していない。利用許諾とは扱わない | 2026-09-11 | [robots.txt](https://www.fullcomp.jp/robots.txt) |
| 利用規約 | 買取ページから参照できるコンテンツ利用規約、転載条件、データ利用条件を確認できず不明。著作権表示はある | 2026-09-11 | [買取情報](https://www.fullcomp.jp/kaitori/)、[プライバシーポリシー](https://www.fullcomp.jp/privacypolicy/) |
| 自動アクセス | 許可・禁止、User-Agent、rate limitの明文を確認できず不明 | 2026-09-11 | [robots.txt](https://www.fullcomp.jp/robots.txt)、[買取情報](https://www.fullcomp.jp/kaitori/) |
| 取得データの保存 | raw HTML、抽出価格、履歴の内部保存を許可・禁止する明文を確認できず不明 | 2026-09-11 | [買取情報](https://www.fullcomp.jp/kaitori/)、[プライバシーポリシー](https://www.fullcomp.jp/privacypolicy/) |
| fixtureの保存・共有 | 非公開・公開fixtureの利用許諾を確認できない。書面承諾なしに保存・共有しない | 2026-09-11 | [買取情報](https://www.fullcomp.jp/kaitori/) |
| 推奨取得間隔 | 公式値なし。許諾を得るまで自動取得しない。許諾後は更新索引を日次以下で確認し、更新された価格表だけを逐次取得する案 | 2026-09-11 | [買取情報](https://www.fullcomp.jp/kaitori/)、[池袋店の価格表](https://www.fullcomp.jp/ikebukuro/kaitori/18872) |
| 認証・Cookie | 公開価格表の閲覧に認証は不要。サイトはCookieを使い、無効時に一部サービスが制限され得る | 2026-09-11 | [プライバシーポリシー](https://www.fullcomp.jp/privacypolicy/) |

robots.txtで対象pathが禁止されていないことと利用条件が公開されていないことを、保存・再利用の許諾とは扱わない。池袋店と`www.fullcomp.jp/ikebukuro/`配下の対象URLを明示し、自動取得、raw artifact、抽出価格履歴、fixture、第三者提供を株式会社イントゥへ確認する。

## 代表サンプル

- 確認したURLまたはローカルartifact ID: [池袋店 ポケモンカード最新弾買取表](https://www.fullcomp.jp/ikebukuro/kaitori/18872)、[横浜店 ポケモンカード最新弾買取表](https://www.fullcomp.jp/yokohama/kaitori/19645)、[横浜店 ポケモンカード旧弾買取表](https://www.fullcomp.jp/yokohama/kaitori/19596)
- 確認日: 2026-09-11
- 保存可否: 不明。ローカルartifactとfixtureは作成していない
- 必須項目の取得可否: TCG、店舗、カード名、カード番号、set code、レアリティ、価格種別、金額、通貨、基準日を取得可能。カード単位IDと公開時刻は取得不可
- 同じカードを他店舗と照合できるか: `ゾロア + 020/019 + MEZ`は同じ基準日に池袋店と横浜店で各1候補、いずれも1,000円だった。一方、`200/SV-P + P`は通常品と未開封品の2候補になり、名称中の封入状態まで必要になる
- 欠損可能な値: カード単位ID、独立した番号・set code、公式セット名、言語、版、状態ランク、公開時刻、有効期限。TCG、host、店舗slug、価格条件、通貨、取得日時、parser versionはsource metadataまたは取込設定から補う
- 想定されるparser変更リスク: 中〜高。無名配列の列順、名称中の番号とset code、CMSとDataTablesのtemplateに依存する

## 取得設計案

- fetch方法: 書面許諾後、対象運営会社・host・店舗を限定し、店舗の更新索引から変更された価格表だけを取得する
- 差分取得方法: 記事ID、表示基準日、content hash、店舗slug、正規化した行hashを比較する
- timeout・再試行: 許諾条件に従い逐次実行する。429または5xxでは停止し、即時再試行しない
- 0件の意味: HTTP成功、`tableData`の存在、更新日、列数を検査し、空配列だけを正常な0件候補とする
- 構造変更の検知: 列数、価格型、カード番号解析率、件数、更新日の後退を店舗・記事種別ごとに検査する
- 重複防止に使える値: `source slug + shop slug + article ID + displayed date + normalized row hash + artifact`を候補とする
- source固有の注意事項: 店舗別価格として保存する。記事更新で旧値が消えるため取得日時と原本が重要。記事IDや行番号をカードIDにしない

## 判断

- 推奨状態: MVP選定
- 理由: 池袋店と`www.fullcomp.jp`へ範囲を限定すれば許諾主体と対象URLを明示して照会でき、店舗別の基準日付き価格を既存2候補へ追加できる。カード単位ID欠損とparser変更リスクを受け入れ、自動取得、保存、fixture利用は許諾まで開始しない
- 再検討条件: `CP-0070`で株式会社イントゥから取得頻度、raw artifact、抽出履歴、fixture、第三者提供の書面回答を得て、許諾済みfixtureで名称解析と記事間schemaを検証する
- 関連ADR: [ADR-0010](../adr/0010-pokemon-mvp-source-candidates.md)
