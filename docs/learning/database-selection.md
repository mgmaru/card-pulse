# DB選定の判断軸

> 対象: Card Pulseの構造化データを保存する主DB
>
> 最終更新: 2026-09-06

## 1. DB選定の基本的な考え方

DBは、知名度や一般的な性能比較だけでは選ばない。アプリケーションが守るべきデータ、実行するquery、障害時に失ってよい範囲、運用できる人と費用から選ぶ。

基本的な順序は次のとおりである。

```text
アプリケーション要件
    ↓
必須条件と比較項目
    ↓
候補の絞り込み
    ↓
代表的な処理によるPoC
    ↓
運用・費用を含めた評価
    ↓
ADRで採用理由と再評価条件を記録
```

Card Pulseの主DBは一時的なcacheではない。カード、店舗、取得原本のメタデータ、価格観測、同定結果、review履歴を持つsystem of recordである。このため、最大処理件数だけでなく、間違った価格や誤ったカード結合を防ぎ、根拠をたどれることを重視する。

HTML、JSON、PDF、画像等の原本本体は別のartifact storageへ保存する。大きなbinaryの保存要件を主DBの比較へ混ぜない。

## 2. 最初に整理する要件

候補製品を見る前に、分からないものを含めて次を記録する。不明な値は推測で確定せず、「初期想定」「計測後に更新」と区別する。

### データ

- 主要entityとrelationは何か。
- 一意性や参照整合性をDBでどこまで強制するか。
- 価格観測を何年間保持するか。
- 一日あたりの観測数、原本数、review数はどれくらいか。
- source固有の可変metadataをどの程度持つか。
- 訂正、再解析、失効をどのような履歴で表現するか。

### 書込み

- Collection Workerは何台あり、同時に何件書き込むか。
- 一つの原本から何件の観測値が生成されるか。
- 同一原本を再実行したとき、どのkeyで重複を防ぐか。
- 途中失敗時に、どの単位までまとめてrollbackするか。
- reviewの同時更新をどう検知するか。

### 読取り

- カードごとの最新価格をどう取得するか。
- 期間別履歴、店舗比較、中央値、店舗数をどの頻度で計算するか。
- Card Diggerから一回の操作で何カード照会するか。
- 許容するAPI応答時間はどれくらいか。
- 古い価格や欠損をどの時点のsnapshotとして返すか。

### 運用

- 許容停止時間はどれくらいか。
- 障害時に失ってよいデータ時間、つまりRPOはどれくらいか。
- 何時間以内に復旧したいか、つまりRTOはどれくらいか。
- backupを誰が取得し、誰が復元を確認するか。
- 夜間・休日の障害対応をどこまで行うか。
- 月額費用と人間の運用時間をどこまで許容するか。

## 3. 主な判断軸

### 3.1 データモデルへの適合

Card Pulseには、カード、店舗、原本、観測値、reviewという関係がある。DBがrelation、unique constraint、foreign key、check constraintを自然に表現できるか確認する。

「柔軟なschema」は常に利点ではない。source固有metadataには柔軟性が役立つが、金額、通貨、店舗、TCG、取得日時などの必須値まで自由にすると、不完全なデータを確定しやすくなる。固定すべきcore fieldと可変metadataを分けて評価する。

### 3.2 整合性とtransaction

次を確認する。

- ACID transactionを必要な単位で利用できるか。
- isolation levelを選び、同時実行時の挙動を説明できるか。
- unique constraintによる冪等性を実現できるか。
- constraint違反をapplicationから判別できるか。
- deadlockやserialization failureを検知して安全に再試行できるか。

Card Pulseでは、誤った重複排除やカード同定の混入は後から判断を壊すため、整合性を最優先にする。

### 3.3 Queryへの適合

一般的なbenchmarkではなく、実際に必要なqueryで比較する。

- カード・店舗ごとの最新観測
- 指定期間の価格履歴
- 同じ条件にそろえた中央値、最高値、最低値
- 観測のある店舗数
- source、鮮度、状態条件による絞り込み
- 集計値から原本までの追跡
- 未処理review itemの取得

index、window function、aggregation、JSON field、partitioning等が、実際のqueryとデータ量に対して使いやすいかを見る。

### 3.4 同時実行と接続管理

APIが読取りを行っている間にWorkerが書き込む。migrationや複数Workerが加わる可能性もある。

- 同時reader・writerをどの程度扱えるか。
- connection数の上限とconnection poolの必要性は何か。
- 長い集計queryが書込みやAPIを妨げないか。
- 複数API instanceから接続できるか。
- lock待ちや遅いqueryを観測できるか。

### 3.5 Backup、復元、可用性

backup機能の有無だけでなく、復元できることを評価する。

- 自動backupと保持期間
- point-in-time recoveryの可否
- 誤削除や誤migrationから戻れる範囲
- 別環境へのexport・restore
- replicationとfailoverの選択肢
- backup中と復元中の停止時間
- 実際の復元手順と所要時間

RPOとRTOを先に決めないと、高可用性機能が必要なのか、費用に見合うのか判断できない。

### 3.6 運用とmaintenance

DB本体の機能だけでなく、継続して扱えるかを確認する。

- managed serviceが利用できるか。
- version upgradeとsecurity updateをどう行うか。
- monitoring、slow query、容量、接続数、lockを確認できるか。
- schema migration toolと相性がよいか。
- 障害時に参照できるdocumentと知見があるか。
- チームが運用方法を学習・維持できるか。

ライセンス費用が無料でも、毎月の保守時間が大きければ安価とは言えない。人間の作業時間も費用として比較する。

### 3.7 Security

- private networkだけに公開できるか。
- TLSと保存時暗号化を使えるか。
- API、Worker、migrationに異なるroleを割り当てられるか。
- credentialを安全に更新できるか。
- 接続と管理操作のaudit logを取得できるか。
- 個人情報や秘密情報を保存しない設計を維持できるか。

スマートフォンやCard DiggerにはDB credentialを配布しない。端末数が増える問題はAPIの認証として扱う。

### 3.8 Schema変更と可搬性

- migrationをtransaction内で実行できる範囲はどこか。
- 大きなtableへの列追加やindex作成時に何がlockされるか。
- rolling deploymentで旧APIと新APIを同時に動かせるか。
- 標準的な形式でexportできるか。
- 特定cloudだけの機能にどの程度依存するか。

可搬性を最大化するために有用な機能をすべて避ける必要はない。依存する機能と移行時の代替方法を把握して選択する。

### 3.9 開発・test環境

- 同じdatabase engineと主要versionをDockerで実行できるか。
- migrationを空DBから繰り返し検証できるか。
- CIでintegration testを実行できるか。
- testごとのデータ分離と初期化を行いやすいか。
- 本番と開発でSQLや型の意味が変わらないか。

本番と異なる軽量DBをtestだけに使う場合、dialect、日時、JSON、constraint、transactionの差を受け入れる必要がある。

### 3.10 費用と拡張性

費用には次を含める。

- 最小instanceの固定費
- storage、backup、replica
- network転送
- monitoring
- 開発・保守・障害対応時間
- 将来の移行費用

拡張性では、現時点の最大性能より、想定の10倍程度までどの方法で伸ばせるかを確認する。垂直scale、read replica、partitioning、archiveの選択肢を調べる。最初から世界規模の分散DBを必要条件にはしない。

## 4. Card Pulseでの優先順位

### 必須条件

候補が一つでも満たさない場合、点数評価へ進めない。

1. server上でAPIとWorkerから安全に接続できる。
2. transactionと一意性制約で冪等な取込を実装できる。
3. 観測値からsource、artifact、parser versionへrelationを保てる。
4. backupと空環境への復元方法を持つ。
5. private接続とrole別権限を持つ。
6. ローカルまたはCIで同じengineを使ったintegration testができる。

### 比較時の優先度

| 判断軸 | 重みの例 |
| --- | ---: |
| データ整合性・transaction | 25 |
| Queryへの適合 | 15 |
| Backup・復元・可用性 | 15 |
| 運用・maintenance | 15 |
| 同時実行・接続管理 | 10 |
| Security | 10 |
| 開発・test環境 | 5 |
| 費用・可搬性・拡張性 | 5 |

重みは選定時の要件に合わせて更新する。合計点だけで機械的に決めず、低得点の軸がどの障害につながるか確認する。

## 5. 比較する候補の考え方

最初から全製品を比較せず、異なる特徴を持つ少数の候補へ絞る。

| 分類 | 確認すること |
| --- | --- |
| Relational database | relation、constraint、transaction、集計がCard Pulseのcore dataに適合するか |
| Document database | source固有metadataの柔軟性が、relationと整合性の複雑化を上回るか |
| Embedded database | 単一processの簡潔さが、server・複数service要件を満たせるか |
| 分析・時系列database | 主DBではなく、大規模集計用の派生storeとして将来必要か |

初回の有力比較には、PostgreSQL、MySQLまたはMariaDB、document database一種、比較基準としてSQLiteを含める。分析専用DBは、主DBから生成できる派生データの保存先として別に評価する。

## 6. PoCで確認すること

候補ごとに同じschema、データ、query、測定方法を使う。製品ごとに有利なdemoを別々に作らない。

1. 空DBへmigrationを適用する。
2. 同一原本を複数回投入し、観測が重複しないことを確認する。
3. 複数Worker相当の同時書込みを実行する。
4. 書込み中にAPI相当の最新価格・履歴queryを実行する。
5. 中央値、最高値、最低値、店舗数を計算する。
6. 原本から再解析した新旧結果を追跡する。
7. schemaを後方互換に変更し、旧queryと新queryを並行実行する。
8. backupを取得し、空環境へ復元する。
9. slow query、lock、容量、接続数を観測する。
10. 初期規模と将来想定規模で時間と費用を記録する。

performance testの件数は根拠なく決めない。Phase 0の情報源更新頻度から一日あたりの観測数を推定し、保存期間と余裕を掛けたデータ量を使う。

## 7. 比較表のテンプレート

| 判断軸 | 重み | Candidate A | Candidate B | Candidate C | 根拠・PoC結果 |
| --- | ---: | ---: | ---: | ---: | --- |
| データ整合性・transaction | 25 | | | | |
| Queryへの適合 | 15 | | | | |
| Backup・復元・可用性 | 15 | | | | |
| 運用・maintenance | 15 | | | | |
| 同時実行・接続管理 | 10 | | | | |
| Security | 10 | | | | |
| 開発・test環境 | 5 | | | | |
| 費用・可搬性・拡張性 | 5 | | | | |

点数は1〜5など同じ尺度を使い、必ず根拠URL、確認日、PoC結果を添える。主観的な点数だけを残さない。

## 8. よくある選定上の問題

- 人気があるという理由だけで決める。
- 一般benchmarkだけを使い、実際のqueryを試さない。
- 初期の月額料金だけを比較し、backup、通信、保守時間を含めない。
- 「schemaが柔軟」という理由で必須fieldの整合性までapplication任せにする。
- managed serviceで提供される機能と、DB engine自体の機能を混同する。
- backupが有効という表示だけを確認し、restoreを試さない。
- 開発では別DBを使い、本番固有の型・constraint・transaction差をtestしない。
- 将来の巨大規模だけを想定し、現在運用できない複雑な構成を選ぶ。

## 9. 選定結果に残すもの

最終結果はADRとして次を記録する。

- 要件と優先順位
- 比較した候補
- 必須条件による除外理由
- PoCのデータ量、query、結果
- 採用理由と受け入れる欠点
- hosting方式と概算費用
- backup・復元方針
- 再評価する条件

DB選定は永久決定ではない。観測量、API負荷、運用時間、費用が再評価条件を超えたとき、新しいADRで見直す。
