# フルコンプ

> source slug: `fullcomp`
>
> 状態: MVP採用
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
| robots.txt | `Sitemap`だけを記載し、池袋店の買取表pathに対する`Disallow`、`Crawl-delay`、User-Agent指定はない。利用許諾とは扱わない | 2026-09-11 | [robots.txt](https://www.fullcomp.jp/robots.txt) |
| 利用規約 | 買取ページから参照できるコンテンツ利用規約、転載条件、データ利用条件を確認できず不明。著作権表示はある | 2026-09-11 | [買取情報](https://www.fullcomp.jp/kaitori/)、[プライバシーポリシー](https://www.fullcomp.jp/privacypolicy/) |
| 自動アクセス | 許可・禁止、User-Agent、rate limitの明文を確認できず不明 | 2026-09-11 | [robots.txt](https://www.fullcomp.jp/robots.txt)、[買取情報](https://www.fullcomp.jp/kaitori/) |
| 取得データの保存 | raw HTML、抽出価格、履歴の内部保存を許可・禁止する明文を確認できず不明 | 2026-09-11 | [買取情報](https://www.fullcomp.jp/kaitori/)、[プライバシーポリシー](https://www.fullcomp.jp/privacypolicy/) |
| fixtureの保存・共有 | 公開条件上の許諾範囲は不明。[ADR-0012](../adr/0012-private-personal-operation.md)により、生HTMLとsource由来fixtureは本人のGit管理外領域だけに保存し、共有しない | 2026-09-11 | [買取情報](https://www.fullcomp.jp/kaitori/) |
| 推奨取得間隔 | 公式値なし。MVPでは更新索引を日次1回以下で確認し、更新された池袋店の価格表だけを逐次取得する | 2026-09-11 | [買取情報](https://www.fullcomp.jp/kaitori/)、[池袋店の価格表](https://www.fullcomp.jp/ikebukuro/kaitori/18872) |
| 認証・Cookie | 公開価格表の閲覧に認証は不要。サイトはCookieを使い、無効時に一部サービスが制限され得る | 2026-09-11 | [プライバシーポリシー](https://www.fullcomp.jp/privacypolicy/) |

robots.txtで対象pathが禁止されていないことと利用条件が公開されていないことを、保存・再利用の許諾とは扱わない。[ADR-0012](../adr/0012-private-personal-operation.md)の個人・非公開境界で、池袋店の対象pathだけを本人のローカル環境から取得し、raw artifactとsource由来fixtureはGit管理外領域だけに保存する。

2026-09-11に固定の調査用User-Agentで池袋店の価格表を1回確認し、認証challenge、Cookie、JavaScript実行なしの通常GETで`200`を返した。現行のrobots.txtは、同日の先行確認で記録した`/wp/wp-admin/`の禁止を含まず`Sitemap`だけを返したため、現在の応答に訂正した。この応答差を継続取得の許諾または安定性保証には使わない。

## 個人・非公開MVPの判断

- 対象HTMLの未認証取得と既存候補との属性照合は技術的に可能である
- User-Agent、取得頻度、raw artifactと抽出履歴の保持、sanitized fixture、Card Diggerへの派生集計、停止・削除条件は公開条件で確認できない
- [ADR-0012](../adr/0012-private-personal-operation.md)により、許諾済みとは扱わず、本人のローカル環境だけで使う3番目のMVP情報源として採用する

API、取得原本、source由来fixture、抽出値、価格履歴は第三者へ公開または提供しない。利用者の追加、公開、共有、第三者向け提供または販売へ範囲を変える場合は、新しいADRで利用条件を再判断する。

## 代表サンプル

- 確認したURLまたはローカルartifact ID: [池袋店 ポケモンカード最新弾買取表](https://www.fullcomp.jp/ikebukuro/kaitori/18872)、[横浜店 ポケモンカード最新弾買取表](https://www.fullcomp.jp/yokohama/kaitori/19645)、[横浜店 ポケモンカード旧弾買取表](https://www.fullcomp.jp/yokohama/kaitori/19596)
- 確認日: 2026-09-11
- 保存可否: 公開条件上は不明。MVPでは本人のGit管理外領域だけに保存し、共有しない
- 必須項目の取得可否: TCG、店舗、カード名、カード番号、set code、レアリティ、価格種別、金額、通貨、基準日を取得可能。カード単位IDと公開時刻は取得不可
- 同じカードを他店舗と照合できるか: `メガレックウザex + M6 + 110/076 + SAR`は池袋店、晴れる屋2、遊々亭で各1候補になった。2026-09-11確認時は池袋店35,000円、晴れる屋2 25,000円、遊々亭32,000円だったが、状態と価格保証の等価性は確認できないため別条件の観測として扱う。`200/SV-P + P`のように通常品と未開封品が同じ番号になる場合は、名称中の封入状態まで必要になる

### 既存候補との価格条件比較

共通キーを`ポケモンカードゲーム / 拡張パック「ストームエメラルダ」 / M6 / 110/076 / SAR / メガレックウザex / 日本語`とした。カード名だけで確定せず、セット、カード番号、レアリティをすべて照合した。

| 情報源 | source内候補 | 2026-09-11の掲載買取価格 | 原本にある価格条件 | 比較判断 |
| --- | --- | ---: | --- | --- |
| フルコンプ池袋店 | 記事`18872`内の1行 | 35,000円 | 池袋店の店頭、完品・美品の満額査定参考価格。基準日は2026-09-10。在庫、状態、相場で変更・停止あり | 印刷仕様は照合可能。店舗と査定条件を保持する |
| 晴れる屋2 | `id=54583`の1件 | 25,000円 | JSONの`buy_price`。状態、言語、公開日時、有効期限なし | 印刷仕様は照合可能。欠損条件を保持する |
| 遊々亭 | `m06/10110`の1件 | 32,000円 | 日本語版の現行表示価格。旧価格14,000円は打消し表示。カード共通の状態減額規則あり | 印刷仕様は照合可能。状態条件をフルコンプと同一視しない |

3件は同じ印刷仕様の価格差を比較できるが、同条件価格としては統合しない。観測ごとに店舗またはチャネル、価格種別、状態条件、価格保証、取得日時、原本URLを保持する。
- 欠損可能な値: カード単位ID、独立した番号・set code、公式セット名、言語、版、状態ランク、公開時刻、有効期限。TCG、host、店舗slug、価格条件、通貨、取得日時、parser versionはsource metadataまたは取込設定から補う
- 想定されるparser変更リスク: 中〜高。無名配列の列順、名称中の番号とset code、CMSとDataTablesのtemplateに依存する

## 取得設計案

- fetch方法: 対象運営会社・host・店舗を池袋店に限定し、日次1回以下で更新索引を確認して変更された価格表だけを逐次取得する
- 差分取得方法: 記事ID、表示基準日、content hash、店舗slug、正規化した行hashを比較する
- timeout・再試行: 逐次実行し、403、429、challengeでは再試行せず停止する。5xxも即時再試行しない
- 0件の意味: HTTP成功、`tableData`の存在、更新日、列数を検査し、空配列だけを正常な0件候補とする
- 構造変更の検知: 列数、価格型、カード番号解析率、件数、更新日の後退を店舗・記事種別ごとに検査する
- 重複防止に使える値: `source slug + shop slug + article ID + displayed date + normalized row hash + artifact`を候補とする
- source固有の注意事項: 店舗別価格として保存する。記事更新で旧値が消えるため取得日時と原本が重要。記事IDや行番号をカードIDにしない

## 判断

- 推奨状態: MVP採用
- 理由: 池袋店の基準日付き価格を既存2情報源と照合でき、店舗別HTMLとして3番目のadapterと価格条件差を検証できる。個人・非公開のローカル利用に限定し、許諾済みとは扱わない
- 停止条件: 403、429、challenge、認証要求、明示的な自動取得拒否、価格表schemaの破壊を検出した場合
- 関連ADR: [ADR-0012](../adr/0012-private-personal-operation.md)
