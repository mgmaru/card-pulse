# 晴れる屋2

> source slug: `hareruya2`
>
> 状態: MVP採用
>
> 最終確認日: 2026-09-11
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
| 形式 | 公開JSON。2026-09-11の応答は8,791,014 bytes。レコード数は原本を保存しない再確認では数えていない |
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

2026-09-11のJSON応答は`ETag`、`Last-Modified`、`Accept-Ranges`、`Access-Control-Allow-Origin: *`、`X-Robots-Tag: noindex, nofollow, noarchive`を返し、同じvalidatorを使う条件付きrequestには`304`を返した。これらは技術的な応答仕様であり、取得・保存・再利用の許可を示さない。画面は一部の低価格・高販売価格レコードを除外するため、JSON全件と画面表示対象は一致しない。

## 取得と利用上の制約

| 確認項目 | 結果 | 確認日 | 根拠URL・箇所 |
| --- | --- | --- | --- |
| robots.txt | API hostでは`/wp-admin/`のみ禁止され、JSON pathは明示禁止されていない。晴れる屋2 hostでも買取リストは一般UAの禁止対象ではない。一般の取得許諾とは扱わない | 2026-09-11 | [API host robots.txt](https://api.corp.hareruyamtg.com/robots.txt)、[晴れる屋2 robots.txt](https://www.hareruya2.com/robots.txt) |
| 利用規約 | 晴れる屋2サイトのコンテンツを同サイトでの使用以外に複写・利用すること、第三者提供のための複製・送信、無断転載・再配布を禁止 | 2026-09-11 | [利用規約「4. 知的財産権」「6. 禁止事項」](https://www.hareruya2.com/pages/terms-of-use) |
| 自動アクセス | 明示的な許可・禁止、API利用条件、rate limitを確認できず不明。運営妨害は禁止 | 2026-09-11 | [利用規約](https://www.hareruya2.com/pages/terms-of-use)、[API host robots.txt](https://api.corp.hareruyamtg.com/robots.txt) |
| 取得データの保存 | Webサイト掲載コンテンツのサイト外利用は禁止。別hostのJSONへの規約適用と内部保存の許諾は不明 | 2026-09-11 | [利用規約「4. 知的財産権」](https://www.hareruya2.com/pages/terms-of-use) |
| fixtureの保存・共有 | 公開条件上の許諾範囲は不明。[ADR-0012](../adr/0012-private-personal-operation.md)により、rawとsource由来fixtureは本人のGit管理外領域だけに保存し、共有しない | 2026-09-11 | [利用規約「4. 知的財産権」「6. 禁止事項」](https://www.hareruya2.com/pages/terms-of-use) |
| 推奨取得間隔 | 公式値なし。MVPでは日次1回以下の条件付きGETとし、304では原本本体を重複保存しない | 2026-09-11 | [商品価格JSON](https://api.corp.hareruyamtg.com/user_data/hareruya2/json/products_all.json)、[API host robots.txt](https://api.corp.hareruyamtg.com/robots.txt) |
| 認証・Cookie | JSONは認証challengeとCookieなしで取得可能。将来の提供保証ではない | 2026-09-11 | [商品価格JSON](https://api.corp.hareruyamtg.com/user_data/hareruya2/json/products_all.json) |

API hostから晴れる屋2の利用規約へのリンクや専用API規約を確認できず、Web利用規約がJSONに直接適用されるかは不明である。CORSとrobots.txtを許諾と解釈しない。[ADR-0012](../adr/0012-private-personal-operation.md)の個人・非公開境界で、本人のローカル環境からだけ取得、raw artifact保存、再解析を行う。

## 個人・非公開MVPの判断

- 対象URLの存在と条件付きGETの技術的成立性は確認した
- User-Agent、取得頻度、raw artifactと抽出履歴の保持、sanitized fixture、Card Diggerへの派生集計、停止・削除条件は公開条件で確認できない
- [ADR-0012](../adr/0012-private-personal-operation.md)により、許諾済みとは扱わず、本人のローカル環境だけで使う最初のMVP情報源として採用する

API、取得原本、source由来fixture、抽出値、価格履歴は第三者へ公開または提供しない。利用者の追加、公開、共有、第三者向け提供または販売へ範囲を変える場合は、新しいADRで利用条件を再判断する。

## 代表サンプル

- 確認したURLまたはローカルartifact ID: [商品価格JSON](https://api.corp.hareruyamtg.com/user_data/hareruya2/json/products_all.json)
- 確認日: 2026-09-11
- 保存可否: 公開条件上は不明。MVPでは本人のGit管理外領域だけに保存し、共有しない
- 必須項目の取得可否: TCG、カード名、カード番号、セット、価格種別、金額、通貨、source内IDを取得可能。レコード別の公開日時はない
- 同じカードを他店舗と照合できるか: `メガレックウザex`は同じセットに4候補あったが、`M6 + 110/076 + SAR`では`id=54583`の1候補になり、2026-09-11の買取価格は25,000円だった。フルコンプ池袋店35,000円、遊々亭32,000円、ドラゴンスター25,000円の同一属性と比較できるが、JSONに状態条件がないため同条件とは確定しない
- 欠損可能な値: `collection_number`が`-`のレコード、set、レアリティ、版、言語、状態、レコード別公開日時、有効期限。TCG、価格種別、通貨、取得日時、原本URL、parser versionはsource metadataまたは取込設定から補う
- 想定されるparser変更リスク: 低〜中。JSON schemaは単純だが公開契約がなく、`title`の分解が必要

## 取得設計案

- fetch方法: JSONを日次1回以下で条件付きGETする。本人の端末またはprivate network内のWorkerだけから実行する
- 差分取得方法: `ETag`、`Last-Modified`、content hashを使う
- timeout・再試行: 逐次実行し、403、429、challengeでは再試行せず停止する。5xxは上限付き指数backoffとする
- 0件の意味: HTTP成功、JSON schema、`count`、`products`の整合を確認し、空配列だけを正常な0件候補とする
- 構造変更の検知: 必須key、型、`count`との一致、件数急変、`title`解析失敗率を検査する
- 重複防止に使える値: `source item id + buy_price + artifact`を候補とし、IDの安定性を確認後に確定する
- source固有の注意事項: 約8.79MBの全件取得を繰り返さず、条件付きGETを優先する。画面表示とJSON全件の対象差を仕様化する

## 判断

- 推奨状態: MVP採用
- 理由: 未認証の構造化JSON、条件付きGET、source内ID、カード番号を利用でき、3候補の中で最初の縦実装に適する。個人・非公開のローカル利用に限定し、許諾済みとは扱わない
- 停止条件: 403、429、challenge、認証要求、明示的な自動取得拒否、必須schemaの破壊を検出した場合
- 関連ADR: [ADR-0012](../adr/0012-private-personal-operation.md)
