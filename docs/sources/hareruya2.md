# 晴れる屋2

> source slug: `hareruya2`
>
> 状態: MVP選定
>
> 最終確認日: 2026-09-09
>
> 調査者: Codex

## 概要

晴れる屋2は株式会社晴れる屋が運営するポケモンカードゲーム専門店で、買取リストを公開している。画面は運営会社ドメイン上のJSONを読み込み、カード番号、セット、価格、source内IDを表示する。JSONは未認証で取得できるが、自動取得、保存、fixture利用に関する公式の許諾と、晴れる屋2の利用規約がAPI hostへ直接適用されるかは確認できない。

- 運営主体: 株式会社晴れる屋
- 店舗・支店: 通販および実店舗。今回確認したデータは公開買取リスト
- 対象TCG: ポケモンカードゲーム
- 主なURL: [買取リスト](https://www.hareruya2.com/pages/buying-list)、[商品価格JSON](https://api.corp.hareruyamtg.com/user_data/hareruya2/json/products_all.json)、[買取案内](https://www.hareruya2.com/pages/buying-service)
- 提供する価格種別: 買取価格。JSONには販売価格も含む

運営主体と事業内容は[会社概要](https://corp.hareruyamtg.com/company)と[事業情報](https://corp.hareruyamtg.com/business)で確認した。

## データ形式

| 項目 | 確認結果 |
| --- | --- |
| 形式 | 公開JSON。確認時は約8.77MB、22,650件 |
| 公開・非公開の別 | 未認証でHTTP 200。公開APIとしての保証と利用許諾は未確認 |
| JavaScript実行の必要性 | JSON取得には不要。買取リスト画面はJavaScriptでJSONを描画する |
| pagination | JSONは全件一括。画面側で50件ずつ表示 |
| source内ID | `id`。確認時の全件で重複なし。将来の安定性は未確認 |
| カード名 | `title`にレアリティ、カード種別、カード番号、set codeと混在 |
| カード番号 | `collection_number` |
| セット | `series_name`と`set_name` |
| レアリティ | 独立項目はなく`title`から解析する |
| 版・言語 | 独立項目はない。英語版は`title`内に表示される例がある |
| 価格 | `buy_price`と`sell_price`に整数円 |
| 状態条件 | レコード別項目はない。画面は在庫とカード状態により変動すると記載 |
| 公開日時 | レコード別にはない。HTTPの`Last-Modified`は原本更新の手掛かりにできる |
| 有効期限 | 未確認 |
| 更新頻度 | 公式周期は未確認。画面の09:00表示は閲覧端末の日付から生成され、更新実績の証拠にできない |

確認時のJSON応答は`ETag`、`Last-Modified`、`Accept-Ranges`、`Access-Control-Allow-Origin: *`を返した。これらは技術的な応答仕様であり、取得・保存・再利用の許可を示さない。画面は一部の低価格・高販売価格レコードを除外するため、JSON全件と画面表示対象は一致しない。

## 取得と利用上の制約

| 確認項目 | 結果 | 確認日 | 根拠URL・箇所 |
| --- | --- | --- | --- |
| robots.txt | API hostでは`/wp-admin/`のみ禁止され、JSON pathは明示禁止されていない。一般の取得許諾とは扱わない | 2026-09-09 | [API host robots.txt](https://api.corp.hareruyamtg.com/robots.txt) |
| 利用規約 | 晴れる屋2サイトのコンテンツを同サイトでの使用以外に複写・利用すること、第三者提供のための複製・送信、無断転載・再配布を禁止 | 2026-09-09 | [利用規約 第4条・第6条](https://www.hareruya2.com/pages/terms-of-use) |
| 自動アクセス | 明示的な許可・禁止、API利用条件、rate limitを確認できず不明。運営妨害は禁止 | 2026-09-09 | [利用規約](https://www.hareruya2.com/pages/terms-of-use)、[API host robots.txt](https://api.corp.hareruyamtg.com/robots.txt) |
| 取得データの保存 | Webサイト掲載コンテンツのサイト外利用は禁止。別hostのJSONへの規約適用と内部保存の許諾は不明 | 2026-09-09 | [利用規約 第4条](https://www.hareruya2.com/pages/terms-of-use) |
| fixtureの保存・共有 | Web掲載コンテンツは許可できない。JSONのraw・縮約fixtureも適用関係が不明なため、書面承諾なしに保存・共有しない | 2026-09-09 | [利用規約 第4条・第6条](https://www.hareruya2.com/pages/terms-of-use) |
| 推奨取得間隔 | 公式値なし。書面承諾を得るまで自動取得しない。承諾後の初期案は日次1回以下の条件付きGET | 2026-09-09 | [商品価格JSON](https://api.corp.hareruyamtg.com/user_data/hareruya2/json/products_all.json)、[API host robots.txt](https://api.corp.hareruyamtg.com/robots.txt) |
| 認証・Cookie | JSONは認証challengeとCookieなしで取得可能。将来の提供保証ではない | 2026-09-09 | [商品価格JSON](https://api.corp.hareruyamtg.com/user_data/hareruya2/json/products_all.json) |

API hostから晴れる屋2の利用規約へのリンクや専用API規約を確認できず、Web利用規約がJSONに直接適用されるかは不明である。CORSとrobots.txtを許諾と解釈せず、運営から書面で条件を得るまでCollection Workerによる取得、raw artifact保存、fixture作成を行わない。

## 代表サンプル

- 確認したURLまたはローカルartifact ID: [商品価格JSON](https://api.corp.hareruyamtg.com/user_data/hareruya2/json/products_all.json)
- 確認日: 2026-09-09
- 保存可否: 不明。ローカルartifactとfixtureは作成していない
- 必須項目の取得可否: TCG、カード名、カード番号、セット、価格種別、金額、通貨、source内IDを取得可能。レコード別の公開日時はない
- 同じカードを他店舗と照合できるか: `メガレックウザex`は同じセットに4候補あったが、`M6 + 110/076 + SAR`では`id=54583`の1候補になり、買取価格は33,000円だった。遊々亭とドラゴンスターの同一属性25,000円と比較できるが、JSONに状態条件がないため同条件とは確定しない
- 欠損可能な値: `collection_number`が`-`のレコード、set、レアリティ、版、言語、状態、レコード別公開日時、有効期限。TCG、価格種別、通貨、取得日時、原本URL、parser versionはsource metadataまたは取込設定から補う
- 想定されるparser変更リスク: 低〜中。JSON schemaは単純だが公開契約がなく、`title`の分解が必要

## 取得設計案

- fetch方法: 書面承諾後、JSONを日次以下で条件付きGETする
- 差分取得方法: `ETag`、`Last-Modified`、content hashを使い、条件付きGETの利用可否は承諾内容と小規模検証で確定する
- timeout・再試行: 逐次実行し、429または5xxでは停止して指数backoffする案。正式値は承諾時に確認する
- 0件の意味: HTTP成功、JSON schema、`count`、`products`の整合を確認し、空配列だけを正常な0件候補とする
- 構造変更の検知: 必須key、型、`count`との一致、件数急変、`title`解析失敗率を検査する
- 重複防止に使える値: `source item id + buy_price + artifact`を候補とし、IDの安定性を確認後に確定する
- source固有の注意事項: 8.77MBの全件取得を繰り返さず、条件付きGETを優先する。画面表示とJSON全件の対象差を仕様化する

## 判断

- 推奨状態: MVP選定
- 理由: 構造化JSONは候補中で最も扱いやすく、遊々亭と同一カードを照合できるため第一選定とした。自動取得、内部保存、fixture利用は許諾まで開始しない
- 再検討条件: 運営からAPI hostの位置づけ、取得頻度、条件付きGET、内部利用、raw artifact保持、fixture共有の書面承諾を得る
- 関連ADR: [ADR-0010](../adr/0010-pokemon-mvp-source-candidates.md)
