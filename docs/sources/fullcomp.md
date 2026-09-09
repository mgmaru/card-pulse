# フルコンプ

> source slug: `fullcomp`
>
> 状態: 保留
>
> 最終確認日: 2026-09-09
>
> 調査者: Codex

## 概要

フルコンプは複数店舗の店頭買取参考価格を公開している。価格表は店舗ごとのHTML記事で、確認したページではJavaScript変数`tableData`に全行が埋め込まれていた。カード番号、set code、レアリティ、価格を抽出できる一方、カード単位のsource内IDがなく、列の意味もHTML上で明示されていない。

フルコンプは店舗群で運営主体と情報公開hostが分かれる。[買取情報](https://www.fullcomp.jp/kaitori/)から、株式会社イントゥ運営と確認できる店舗は`www.fullcomp.jp`、株式会社インスパイア側の店舗は`inspire-jp.net`へ遷移する。この文書のデータ形式調査は`www.fullcomp.jp`の店舗別価格表を対象とし、別hostのadapterと利用許諾を同一とみなさない。

- 運営主体: 株式会社イントゥと株式会社インスパイア。対象店舗ごとの確認が必要
- 店舗・支店: 全国18店舗と案内。価格は店舗ごとに異なる
- 対象TCG: ポケモンカードゲーム。ほかのTCGも扱う
- 主なURL: [買取情報](https://www.fullcomp.jp/kaitori/)、[池袋店の価格表](https://www.fullcomp.jp/ikebukuro/kaitori/18872)、[横浜店の価格表](https://www.fullcomp.jp/yokohama/kaitori/19596)
- 提供する価格種別: 店舗別の店頭買取参考価格

`www.fullcomp.jp`側の8店舗が株式会社イントゥ運営であることは[フルコンプ秋葉原EC店の会社概要](https://www.fullcomp-akihabara-ec.com/html/company.html)、株式会社インスパイア側の店舗は[事業・店舗一覧](https://inspire-jp.net/business/fullcomp/)で確認した。[プライバシーポリシー](https://www.fullcomp.jp/privacypolicy/)も両社を共同利用の管理者として列挙する。

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
| robots.txt | `www.fullcomp.jp`はsitemapだけを記載し、`Disallow`と`Crawl-delay`はない。利用許諾とは扱わない | 2026-09-09 | [robots.txt](https://www.fullcomp.jp/robots.txt) |
| 利用規約 | 買取ページから参照できるコンテンツ利用規約、転載条件、データ利用条件を確認できず不明。著作権表示はある | 2026-09-09 | [買取情報](https://www.fullcomp.jp/kaitori/)、[プライバシーポリシー](https://www.fullcomp.jp/privacypolicy/) |
| 自動アクセス | 許可・禁止、User-Agent、rate limitの明文を確認できず不明 | 2026-09-09 | [robots.txt](https://www.fullcomp.jp/robots.txt)、[買取情報](https://www.fullcomp.jp/kaitori/) |
| 取得データの保存 | raw HTML、抽出価格、履歴の内部保存を許可・禁止する明文を確認できず不明 | 2026-09-09 | [買取情報](https://www.fullcomp.jp/kaitori/)、[プライバシーポリシー](https://www.fullcomp.jp/privacypolicy/) |
| fixtureの保存・共有 | 非公開・公開fixtureの利用許諾を確認できない。書面承諾なしに保存・共有しない | 2026-09-09 | [買取情報](https://www.fullcomp.jp/kaitori/) |
| 推奨取得間隔 | 公式値なし。許諾を得るまで自動取得しない。許諾後は更新索引を日次以下で確認し、更新された価格表だけを逐次取得する案 | 2026-09-09 | [買取情報](https://www.fullcomp.jp/kaitori/)、[池袋店の価格表](https://www.fullcomp.jp/ikebukuro/kaitori/18872) |
| 認証・Cookie | 公開価格表の閲覧に認証は不要。サイトはCookieを使い、無効時に一部サービスが制限され得る | 2026-09-09 | [プライバシーポリシー](https://www.fullcomp.jp/privacypolicy/) |

robots.txtに禁止がないことと利用条件が公開されていないことを、保存・再利用の許諾とは扱わない。運営会社とhostごとに、自動取得、raw artifact、抽出価格履歴、fixture、第三者提供を確認する。少なくとも`www.fullcomp.jp`と`inspire-jp.net`を一つの許諾や一つのparserで扱わない。

## 代表サンプル

- 確認したURLまたはローカルartifact ID: [池袋店 ポケモンカード最新弾買取表](https://www.fullcomp.jp/ikebukuro/kaitori/18872)
- 確認日: 2026-09-09
- 保存可否: 不明。ローカルartifactとfixtureは作成していない
- 必須項目の取得可否: TCG、店舗、カード名、カード番号、set code、レアリティ、価格種別、金額、通貨、基準日を取得可能。カード単位IDと公開時刻は取得不可
- 同じカードを他店舗と照合できるか: `set code + printed card number + rarity`を主軸に照合できる見込み。版と名称を補助確認する
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

- 推奨状態: 保留
- 理由: 店舗別価格は有用だが、カード単位IDがなくparser変更リスクが高い。運営会社ごとの自動取得、保存、fixture利用条件も未確認
- 再検討条件: 対象店舗とhostを限定し、運営会社から取得頻度、raw artifact、抽出履歴、fixture、第三者提供の書面承諾を得る
- 関連ADR: 未作成
