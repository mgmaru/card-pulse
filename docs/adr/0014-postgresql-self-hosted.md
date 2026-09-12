# ADR-0014: 構造化データのDBにPostgreSQL 18を採用し、self-hostで運用する

- 状態: Accepted
- 日付: 2026-09-12
- 決定者: プロジェクトオーナー
- 置換するADR: なし
- 置換されたADR: なし

## Context

[ADR-0004](0004-server-database-selection.md)は、構造化データのsystem of recordをサーバー側DBへ置くことだけを決め、DB製品とhosting providerを未決のまま残した。この未決事項は、schema、migration、query最適化、backup手順、role設計を確定できない原因になっていた。

未決を解消するために3段階の作業を行った。`CP-0007`で[DB要件](../architecture/database-requirements.md)として容量、同時実行、整合性、backup・復旧、security、費用の基準を定義し、`CP-0008`の[候補比較](../research/database-candidate-comparison-2026-09.md)でPostgreSQL 18.6とMariaDB 12.3.3をPoC対象に絞り、`CP-0009`の[PoC](../research/database-poc-2026-09.md)で同じschema、同じ生成データ、同じquery、同じ障害と復元手順を両候補へ適用した。

PoCでは両候補ともPoC合格条件10項目を1倍（約540万行）と10倍（約4,430万行）で満たした。代表queryのp95、1日分の取込時間、28日分の再解析時間、復元時間、費用のいずれも基準に対して余裕があり、性能はどちらかを落とす理由にならなかった。差が出たのは次の4点で、最初の2つは外部keyの扱いに関するものである。

- 外部key検査を止める操作をruntime roleが実行できるかどうかが違う。**どちらのDBも既定では検査しており、DBが自分でこの設定を変えることはない。**検査が止まるのは、applicationが自分のsessionへ明示的なSQLを発行したときだけである。その操作をPostgreSQLはsuperuser専用として拒否し（SQLSTATE 42501）、MariaDBは`INSERT`権限だけのroleへ許可した。PoCではWorker roleで`SET SESSION foreign_key_checks = 0`を実行し、続けて存在しないカードを参照する観測を追記できた。
- backupの復元でも同じ差が出る。`mariadb-dump`の出力は既定で外部key検査を止めた状態で流れるため、参照の切れた行を含むbackupが警告なく復元される。`pg_dump`は検査を止めず、外部key制約を最後に作って全行を検証するため、同じbackupは復元が失敗して検出できる。backup取得時のsnapshot一貫性には差がない。
- MariaDBはDDLがtransactionではないため、失敗したmigrationとdowngradeの両方が部分適用のまま残り、手作業の修復が必要だった。PostgreSQLは同じ失敗で自動的に巻き戻り、downgradeも成功した。
- 10倍プロファイルの論理復元はPostgreSQLが247秒、MariaDBが1,295秒で約5倍の差があった。どちらも`DB-REC-02`のRTO内に収まる。

Card Pulseは[ADR-0002](0002-append-only-provenance.md)で原本と価格観測を追記型で保存し、訂正を新しい履歴として表現すると決めている。[ADR-0012](0012-private-personal-operation.md)により、運用者はプロジェクトオーナー本人だけで、runtimeはInternetへ公開しない。

## Decision

### 製品とversion

構造化データのsystem of recordにPostgreSQLを採用し、major version 18へ固定する。PoCの実測は18.6で行った。major 18のcommunity supportは2030-11-14までの予定であり（[PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)、確認日: 2026-09-12）、MVPが必要とする3年間のonline保持期間を単一majorで満たせる。

minor更新は、同じ品質検査とintegration testを通して明示的に適用する。major更新は新しいADRの対象とはせず、`DB-OPS-01`の保守作業として計画停止時間内に実施し、更新前後の検証手順をrunbookへ残す。

### Hosting方式

self-host構成を採用し、managed databaseとBaaSは採用しない。DBは[ADR-0006](0006-docker-compose-local-development.md)に従いDocker Composeのserviceとして、プロジェクトオーナー本人の端末またはprivate network内で実行する。container imageはOS variantとdigestを固定する。具体的なimage参照は`CP-0012`で確定する。

DB portはInternetへ公開しない。同一host内ではCompose内部network、hostをまたぐ場合は認証済みprivate networkとserver証明書を検証するTLSを使う（`DB-SEC-01`）。

### 接続、型、migration

[ADR-0013](0013-python-toolchain-and-migrations.md)がDB選定後へ先送りした項目を、ここで確定する。

- driverはpsycopg 3、dialectはSQLAlchemy 2のPostgreSQL dialectを使う。domainとapplicationはこれらをimportせず、依存をpersistence adapterに閉じる方針は[ADR-0001](0001-modular-monolith.md)のまま変えない。
- カードの内部識別子はnative `uuid`、日時はtimezoneを保持する`timestamptz`、source metadataは`jsonb`、金額は最小通貨単位の`BIGINT`で保存する。PoCでこれらの往復一致を確認した。
- PostgreSQLはDDLをtransactionで実行するため、Alembicの1 revisionを1 transactionとして扱う。revisionの途中で失敗した変更は自動で巻き戻り、`alembic_version`と実schemaが食い違わない。
- migrationは専用roleと明示した保守時間で実行し、`lock_timeout`を設定する。APIやWorkerの起動時に暗黙実行しない。
- 後方互換な変更はdowngradeで戻す。データを失う変更、および長時間のindex再構築を伴う変更は、直前のbackup取得を前提にする。

### 権限と追記型保存

API、Worker、migration、backup、管理者をそれぞれ別roleと別credentialに分ける。確定した証拠（原本metadata、抽出結果、観測候補、同定試行、確定観測）に対して、runtime roleへ`UPDATE`と`DELETE`を与えない。訂正と再解析は新しい行の追記として表現する。具体的なgrantは`CP-0022`で確定する。

PostgreSQLではconstraint検査の無効化がsuperuser専用であるため、追記型保存と参照整合をDBの権限で強制できる。この性質を設計の前提として使い、runtime roleには検査を止める権限を与えない。検査を止める必要がある一括投入や移送作業は、管理者roleの明示的な作業として実行し、直後に参照整合を確認する。

この判断の背景と、外部key検査がいつ・誰の操作で止まるのかは[外部keyの強制とDB権限](../learning/foreign-key-enforcement.md)に整理した。

### Backupと復元

論理backupを復元の正とする。一つのbackup setに、`pg_dump`のcustom形式によるDB dump、role等のglobal object、migration revision、artifact manifest、各fileのchecksumを含め、暗号化して本人が管理する非公開の保存先へ置く。世代数、RPO、RTO、復元訓練の頻度は[DB要件](../architecture/database-requirements.md#backup復旧可用性)を正とし、ここでは重複して定義しない。

MVPではsingle primaryで開始し、replica、自動failover、point-in-time recoveryを必須にしない。

## Consequences

- schema、migration、query、index、role、backup手順をPostgreSQL固有の機能を前提に設計できる。`CP-0011`以降のpackage構成、Compose環境、data model確定が具体的なdialect上で進む。
- 追記型保存と参照整合をDB権限で強制でき、applicationの実装誤りが証拠を壊す経路を減らせる。
- 冪等な追記は`INSERT ... ON CONFLICT DO NOTHING`で書ける。追記専用roleのまま重複を無視できる。
- 書込みのtail latencyを受け入れる。PoCの10倍プロファイルでは1 batchの最大が29.6秒になった。checkpointとautovacuumの設定は実データで調整し、`DB-OPS-02`の観測対象に含める。
- WAL容量は`max_wal_size`まで確保される。data volumeの空き容量計画にtable、index、WALの上限を含める。
- PostgreSQL固有の型と機能へ依存するため、他製品への移行時には型変換と権限設計の再検討が必要になる。domainとapplicationは引き続き特定のDB製品へ依存させず、依存はpersistence adapterに閉じる。
- self-host構成のため、可用性、監視、更新、backupの実行責任は本人が持つ。月額のservice費用は発生せず、増分費用は電力と保存先容量にとどまる。

## Alternatives considered

- **MariaDB 12.3.3 + InnoDB**: PoC合格条件10項目を満たし、応答時間は同等だった。採用しなかったのは次の3点による。第一に、applicationが外部key検査を止める実装を書いた場合、MariaDBはruntime roleにもそれを許すため、追記型保存と参照整合をDBの権限で守れない。第二に、DDLがtransactionではなく、失敗したmigrationとdowngradeが部分適用のまま残る。第三に、10倍規模の論理復元がPostgreSQLの約5倍かかり、復元時に参照整合も検証されない。いずれも実装規約、code review、定期検査で補えるが、補う作業と抜けの余地を増やす。MariaDBが自動的に検査を外すわけではなく、差は「誤った実装をDBが拒否できるか」にある。
- **BaaSまたはmanaged database（Supabase、Neon等）**: 運用の手間を減らせるが、Internet経由の接続経路が`DB-SEC-01`と[ADR-0012](0012-private-personal-operation.md)の非公開運用に適合せず、3年分のデータを保持する構成の費用も`DB-COST-01`の暫定上限を超える。詳細は[CP-0008のhosting方式とBaaSの検討](../research/database-candidate-comparison-2026-09.md#hosting方式とbaasの検討)に記録した。
- **MongoDB**: DBが参照整合性を強制せず、採用済みのAlembic migrationにも合わないため、`CP-0008`の必須条件で除外した。
- **SQLite**: 独立したDB service、private network経由のserver接続、DB role分離を満たさないため、`CP-0008`の必須条件で除外した。[ADR-0003](0003-mvp-local-storage.md)から[ADR-0004](0004-server-database-selection.md)で置き換えた判断を戻さない。
- **PostgreSQL 17へのversion固定**: 保守期間が18より短く、18を選べない理由が見つからなかった。

## Validation

この判断は`CP-0009`の実測を根拠とする。次のいずれかが起きた場合に再評価する。

- [DB要件の再評価条件](../architecture/database-requirements.md#再評価条件)のいずれかに該当する。特に、実測の段階別日次件数、query p95、backup・復元時間、月額増分費用、定常保守時間が基準を超える場合。
- PoCで測定していない条件で不適合が判明する。固定image digestでのDocker Compose起動とCI amd64での再現は`CP-0012`と`CP-0060`で確認する。
- 利用者、API instance、Worker、対象TCG、情報源を増やす、Internetへ公開する、または第三者へデータを提供する。
- PostgreSQL 18のcommunity supportが終了する前に、major更新の計画を立てられない。

再評価の結果として製品を変更する場合は、このADRを置き換える新しいADRで決定する。
