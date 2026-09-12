# CP-0008 DB候補比較

> 状態: 調査完了
>
> 基準日: 2026-09-12
>
> 対象: Card Pulse MVPの構造化データを保存する主DB

## 結論

`CP-0009`のPoC対象をPostgreSQL 18.6とMariaDB 12.3.3に絞る。机上評価ではPostgreSQLを第1候補、MariaDBを比較候補とする。MongoDBとSQLiteは性能測定で解消できない必須条件の不適合があるため、正式なPoC対象から外す。

| 候補 | 必須条件 | 暫定点 | CP-0009での扱い |
| --- | --- | ---: | --- |
| PostgreSQL 18.6 | 書面上は適合。性能、復旧時間、費用、保守時間は未実測 | 93 / 100 | 第1候補としてPoCする |
| MariaDB 12.3.3 LTS + InnoDB | 条件付き適合。型、制約、DDL、driverに追加検証が必要 | 76 / 100 | 比較候補としてPoCする |
| MongoDB | 不適合。DBが参照整合性を強制せず、採用済みのAlembic migrationを満たさない | 採点対象外 | 正式PoCを行わない |
| SQLite | 不適合。独立DB service、private network経由のserver接続、DB role分離を満たさない | 採点対象外 | 正式PoCを行わない |

この結果はDB製品の採用決定ではない。[DB要件](../architecture/database-requirements.md)の同一schema、負荷、query、障害、復元条件で両候補を測り、`CP-0010`のADRで製品とhosting方式を決定する。[ADR-0004](../adr/0004-server-database-selection.md)の未決事項はそれまで維持する。

## 比較方法

[DB選定の判断軸](../learning/database-selection.md)に従い、先に必須条件を判定し、通過できる候補だけを8軸で採点した。候補群はrelational databaseからPostgreSQLとMariaDB、document databaseからMongoDB、embedded databaseの比較基準としてSQLiteを選んだ。分析専用DBは主DBの候補に含めない。

点数は5を「標準機能で直接適合し、既知の差が小さい」、4を「標準的な設定または明示した規約で適合」、3を「適合可能だがPoCまたは運用設計への依存が大きい」、2を「大きな補完が必要」、1を「不適合」とする。点数は機能資料による暫定値であり、PoC実測値ではない。

比較対象versionは基準日時点の保守状態で選んだ。PostgreSQL 18.6は現行の安定major 18の保守版であり、major 18は2030-11-14までのsupport予定である。[PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)（確認日: 2026-09-12）を根拠とする。MariaDBは年次LTSの12.3.3を使うが、Community保守期限は2029-06-12であり、3年間の保持期間中に後続LTSへの更新が必要になる。[MariaDB maintenance policy](https://mariadb.org/about/#maintenance-policy)と[2026年第3四半期の保守release](https://mariadb.org/mariadb-server-12-3-11-8-11-4-and-10-11-q3-2026-maintenance-releases-and-goodbye-10-6/)（確認日: 2026-09-12）を根拠とする。PoCでは固定tagに加えてcontainer image digestも記録する。

## 必須条件

「書面通過」は製品機能と現実的なsingle-primary構成を提示できることを表す。容量、性能、RTO、費用、保守時間の数値は、書面だけで合格とせずPoCで確認する。

| 必須条件 | PostgreSQL | MariaDB | MongoDB | SQLite |
| --- | --- | --- | --- | --- |
| API・Workerからserver接続 | 書面通過 | 書面通過 | 書面通過 | 不適合。DB serverがない |
| ACID、参照整合性、必須値、複合一意性 | 書面通過 | 書面通過。InnoDBとconstraint検査を固定する | 不適合。collection間参照はapplicationが整合させる | 機能はあるがFKを接続ごとに有効化する |
| 1倍・10倍負荷と代表query | PoC確認 | PoC確認 | gate不通過のため未評価 | 2 writerは直列化される。gate不通過のため未評価 |
| RPO・RTO、世代保持、空環境restore | 手段あり。PoC確認 | 手段あり。PoC確認 | 手段はある | 手段はある |
| 非公開network、role分離、credential rotation、保存時暗号化 | 書面通過。OS・volumeと外部jobを併用 | 書面通過。OS・volumeと外部jobを併用 | roleはあるがCommunity監査に未解決点がある | 不適合。DB user、role、credentialがない |
| Docker、SQLAlchemy dialect、Alembic | 書面通過 | 条件付き通過 | 不適合。Alembicの公式DDL実装がない | dialectはあるが独立DB serviceにならない |
| 3年費用が月額上限内の構成 | self-host前提で条件付き通過 | self-host前提で条件付き通過 | 必須条件不適合のため適合構成を算定しない | 必須条件不適合のため適合構成を算定しない |
| 総合判定 | CP-0009対象 | CP-0009対象 | 除外 | 除外 |

MongoDBは複数document transaction、schema validation、複合unique index、roleを持つ。しかし、公式資料はdocument間のreferenceをapplicationが解決し、参照整合性が必要な場合もapplication logicで維持する方法を示している。[MongoDB data consistency](https://www.mongodb.com/docs/manual/data-modeling/data-consistency/)と[database references](https://www.mongodb.com/docs/manual/reference/database-references/)（確認日: 2026-09-12）を根拠とする。`shop`、`raw_artifact`、`card_identity`への参照をDB constraintで保証する`DB-INT-01`と`DB-INT-02`を満たさない。また、Alembicの公式DDL実装にはPostgreSQL、MySQL/MariaDB、SQLite等が含まれるがMongoDBは含まれない。[Alembic DDL internals](https://alembic.sqlalchemy.org/en/latest/api/ddl.html)（確認日: 2026-09-12）を根拠とする。

SQLiteはACID、constraint、WAL snapshot、Alembic dialectを持つ。一方、application processがdatabase fileを直接扱うserverless DBであり、別serviceからnetwork経由で接続するDB serverを持たない。DB userやroleによるAPI、Worker、migration、backupの権限分離もできない。[SQLite serverless architecture](https://www.sqlite.org/serverless.html)、[適切な利用場面](https://www.sqlite.org/whentouse.html)、[zero-configuration](https://www.sqlite.org/zeroconf.html)（確認日: 2026-09-12）を根拠とする。共有volumeで複数containerからfileを開く構成は、このserver・権限要件の代替にしない。

## 通過候補の比較

### 暫定採点

| 判断軸 | 重み | PostgreSQL | MariaDB |
| --- | ---: | ---: | ---: |
| データ整合性・transaction | 25 | 5 | 4 |
| Queryへの適合 | 15 | 5 | 4 |
| Backup・復元・可用性 | 15 | 5 | 4 |
| 運用・maintenance | 15 | 4 | 3 |
| 同時実行・接続管理 | 10 | 5 | 4 |
| Security | 10 | 4 | 4 |
| 開発・test環境 | 5 | 5 | 4 |
| 費用・可搬性・拡張性 | 5 | 3 | 3 |
| 加重合計 | 100 | **93** | **76** |

### PostgreSQL

PostgreSQLはCard Pulseのrelationと型を直接表現しやすい。foreign key、`NOT NULL`、`CHECK`、複合`UNIQUE`に加え、native `uuid`、`timestamptz`、`jsonb`を持つ。`jsonb`は原文保存用ではなくsource固有metadata用とし、原文証拠はartifactへ残す。[PostgreSQL constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)、[data types](https://www.postgresql.org/docs/18/datatype.html)、[JSON types](https://www.postgresql.org/docs/18/datatype-json.html)（確認日: 2026-09-12）を根拠とする。

MVCCでは通常のreaderとwriterが互いを止めず、`Repeatable Read`で複数queryが同じsnapshotを読める。複合unique constraintと`ON CONFLICT`、行lockまたはversion条件付きupdateにより、冪等取込とreview競合をDBで防げる。constraint、serialization、deadlock、lock、接続のerror codeも区別できる。[Transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html)、[error codes](https://www.postgresql.org/docs/18/errcodes-appendix.html)、[SQLAlchemy PostgreSQL dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)（確認日: 2026-09-12）を根拠とする。

最新値と履歴にはB-treeとwindow function、中央値には`percentile_disc`または`percentile_cont`を使える。論理backupは`pg_dump`、global objectは`pg_dumpall`、物理backupとPITRはbase backupとWAL archiveを使える。[Aggregate functions](https://www.postgresql.org/docs/18/functions-aggregate.html)、[pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html)、[backup and restore](https://www.postgresql.org/docs/18/backup.html)（確認日: 2026-09-12）を根拠とする。

roleとtable privilegeを分け、`pg_hba.conf`で接続元、DB、role、認証方式を制限できる。hostをまたぐ場合はTLSの`verify-full`を使う。接続、transaction、query、lockは`pg_stat_activity`と`pg_locks`等で観測できるが、volume、backup job、通知、30日間のlog保持は外部の運用で補う。[PostgreSQL roles](https://www.postgresql.org/docs/18/user-manag.html)、[pg_hba.conf](https://www.postgresql.org/docs/18/auth-pg-hba-conf.html)、[TLS](https://www.postgresql.org/docs/18/libpq-ssl.html)、[monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)（確認日: 2026-09-12）を根拠とする。

SQLAlchemyはPostgreSQL dialectを同梱し、psycopg 3はPython 3.14とPostgreSQL 18を対象に含める。[SQLAlchemy dialects](https://docs.sqlalchemy.org/en/20/dialects/index.html)と[Psycopg](https://www.psycopg.org/)（確認日: 2026-09-12）を根拠とする。PoC baselineはPostgreSQL 18.6、SQLAlchemy 2.0.52、psycopg 3.3.5、Alembic 1.19.2とし、lockfileとimage digestで再現する。各versionは[SQLAlchemy changelog](https://www.sqlalchemy.org/changelog/)、[Psycopg release notes](https://www.psycopg.org/psycopg3/docs/news.html)、[Alembic changelog](https://alembic.sqlalchemy.org/en/latest/changelog.html)（確認日: 2026-09-12）で確認した。

残る主なリスクは、`ALTER TABLE`やindex作成時のlock、WAL・index・backup容量、autovacuumの保守、外部監視、保存時暗号化、監査とbackup jobの運用である。機能の存在を性能、RTO、保守時間の合格とみなさない。

### MariaDB

MariaDBはInnoDBを使えばACID、foreign key、`NOT NULL`、`CHECK`、複合`UNIQUE`、MVCC、行lockを利用できる。window function、`MEDIAN`、`PERCENTILE_CONT`もあり、Card Pulseの代表queryをSQLで表現できる。[InnoDB](https://mariadb.com/docs/server/server-usage/storage-engines/innodb/innodb-storage-engine-introduction)、[constraints](https://mariadb.com/docs/server/reference/sql-statements/data-definition/constraint)、[window functions](https://mariadb.com/docs/server/reference/sql-functions/special-functions/window-functions/window-functions-overview)（確認日: 2026-09-12）を根拠とする。

型と制約には明示的な規約が要る。native `UUID`は利用できるがSQLAlchemyのreflectionとautogenerateを確認する。`TIMESTAMP`はUTCの時点を保持するが元のtimezone識別子を保持せず、SQLAlchemyのMySQL/MariaDB型の`timezone`引数も利用されない。接続timezoneをUTCへ固定し、必要な元offsetは別値として持つ。`JSON`はvalidity check付き`LONGTEXT`のaliasであり、重複keyやindex方法を検証する。[MariaDB UUID](https://mariadb.com/docs/server/reference/data-types/string-data-types/uuid-data-type)、[TIMESTAMP](https://mariadb.com/docs/server/reference/data-types/date-and-time-data-types/timestamp)、[JSON](https://mariadb.com/docs/server/reference/data-types/string-data-types/json)、[SQLAlchemy MySQL/MariaDB dialect](https://docs.sqlalchemy.org/en/20/dialects/mysql.html)（確認日: 2026-09-12）を根拠とする。

MariaDBのDDLは暗黙commitを起こすため、一つのAlembic revisionに複数DDLがある場合の途中失敗をtransaction全体のrollbackでは回復できない。`foreign_key_checks`、`unique_checks`、`check_constraint_checks`をsessionで無効化できるため、runtime roleから変更できるかを検査し、証拠履歴のconstraintを迂回できない構成を確認する。[Implicit commit](https://mariadb.com/docs/server/reference/sql-statements/transactions/sql-statements-that-cause-an-implicit-commit)と[server variables](https://mariadb.com/docs/server/server-management/variables-and-modes/server-system-variables)（確認日: 2026-09-12）を根拠とする。

roleとtable privilegeを分け、接続元を`user@host`で制限し、TLSを要求できる。接続、slow query、InnoDB transaction、lock waitをserver statusとsystem viewから取得でき、接続・DDL・DCLはAudit Pluginで記録できる。volume、backup job、通知、30日間のlog保持は外部の運用で補う。[MariaDB roles](https://mariadb.com/docs/server/reference/sql-statements/account-management-sql-statements/create-role)、[GRANT](https://mariadb.com/docs/server/reference/sql-statements/account-management-sql-statements/grant)、[secure connections](https://mariadb.com/docs/server/security/encryption/data-in-transit-encryption/securing-connections-for-client-and-server)、[Audit Plugin](https://mariadb.com/docs/server/reference/plugins/mariadb-audit-plugin/mariadb-audit-plugin-configuration)（確認日: 2026-09-12）を根拠とする。

論理backupには`mariadb-dump --single-transaction`、物理backupとPITRには`mariadb-backup`とbinlogを利用できる。[Backup overview](https://mariadb.com/docs/server/server-usage/backing-up-and-restoring-databases/backup-and-restore-overview)と[full backup and restore](https://mariadb.com/docs/server/server-usage/backup-and-restore/mariadb-backup/full-backup-and-restore-with-mariadb-backup)（確認日: 2026-09-12）を根拠とする。PoC baselineはMariaDB 12.3.3、SQLAlchemy 2.0.52、Connector/Python 1.1.14、Alembic 1.19.2とする。Python 3.14のLinux・macOS環境ではConnector/Cを含むsource buildが必要になる可能性があるため、Apple SiliconとCI amd64の両方でbuildを確認する。[MariaDB Connector/Python 1.1.14](https://mariadb.com/docs/release-notes/connectors/python/1.1/1.1.14)（確認日: 2026-09-12）を根拠とする。

## 費用と運用時間の事前見積もり

DB engineとhosting方式を混同しないため、両候補を同じself-host構成で比較する。本人の既存host上でsingle-primary containerを動かし、暗号化volumeへDBを置き、日次backupを別障害領域の非公開保存先へ送る。replicaと有料monitoringは初期構成に含めない。

実容量、追加消費電力、backup保存先の実請求がまだないため、次の金額は価格情報ではなく`DB-COST-01`内に収めるための予算配分である。CP-0009では実測したtable、index、log、backup容量とhost条件から差し替える。

| 費用項目 | 初年度の月額配分 | 3年目の月額配分 | CP-0009で置き換える値 |
| --- | ---: | ---: | --- |
| host compute・電力 | 600〜1,000円 | 600〜1,000円 | idle時との差分電力量と料金 |
| DB用storage | 300〜600円 | 600〜1,200円 | 3年予測容量、50%余裕、媒体費 |
| 別障害領域のbackup | 300〜700円 | 600〜1,500円 | dump容量、世代数、転送・保存費 |
| network・monitoring | 100〜300円 | 100〜300円 | private networkと通知の増分費 |
| 合計 | **1,300〜2,600円** | **1,900〜4,000円** | 3,000円目標、5,000円上限と比較 |

現時点ではengine間の実容量差を測っていないため、PostgreSQLとMariaDBへ同じ金額範囲を置く。上限側でも暫定上限5,000円内に収まる構成を提示できるため両候補を条件付き通過とするが、3年目の上限側は目標3,000円を超える。PoC後の実見積もりが5,000円を超える場合は、製品を採用せず負荷、hosting、費用上限のどれを変えるか判断する。

| 候補 | 初期構築の作業枠 | 月次保守の作業枠 | 復元訓練の作業枠 | 主な不確実性 |
| --- | ---: | ---: | ---: | --- |
| PostgreSQL | 4〜6時間 | 0.5〜1時間 | 1〜2時間 | WAL、autovacuum、監査設定、major更新 |
| MariaDB | 5〜8時間 | 0.75〜1時間 | 1〜2時間 | driver build、DDL回復、constraint設定、LTS更新 |

これらは実績ではなくPoCの作業計画である。構築、backup確認、patch更新、監視確認、空環境restoreを実施して実時間へ置き換える。MongoDBとSQLiteは要件を満たす構成がないため、低い費用を採用理由にしない。

## CP-0009の共通検証事項

両候補へ同じgenerator、schema、query、同時実行数、障害、測定方法を適用する。[DB要件](../architecture/database-requirements.md#cp-0009のpoc合格条件)に加え、候補差が出る次を明示的に記録する。

1. PostgreSQL 18.6とMariaDB 12.3.3の固定imageをApple Siliconのlocal環境とCI amd64で起動し、CPython 3.14.7からdriver接続できること。
2. Alembicの空DBへの`upgrade head`、既存schemaのupgrade、offline SQL、複数DDLの途中失敗、部分適用の識別と回復を確認する。PostgreSQLではDDLとindex作成のlock、MariaDBでは暗黙commitを個別に記録する。
3. native UUID、UTC日時、source metadata JSONをSQLAlchemy、driver、Alembic、dump・restoreまで往復させる。MariaDBではnative UUIDのreflection、session timezone、JSONの重複keyとgenerated-column indexを追加確認する。
4. `NOT NULL`、foreign key、`CHECK`、複合`UNIQUE`を破る入力を拒否し、driverとapplicationがerrorを分類できること。MariaDBではruntime roleがconstraint検査を無効化できないこと、または防止策を確認する。
5. 2 writerによる同一冪等keyの競合、8 readerと2 writerの同時実行、reviewの二重確定、deadlock、serialization failure、lock timeout、接続断、process停止を再現する。
6. 1倍約430万行と10倍約4,300万行で、投入、28日分の再解析、代表queryのcold・warm p95、実行計画、table・index・内部log・backup容量を測る。
7. API、Worker、migration、backup、admin roleを分け、API書込み、Worker DDL、証拠履歴のUPDATE・DELETE、外部network接続が拒否されることを確認する。
8. logical backup、global objectまたはrole、暗号化、checksum、migration revision、artifact manifestを一つのbackup setとして空環境へ復元し、DB復元と整合検証を2時間以内、全体を8時間以内に終えられるか測る。
9. storage、connection、5秒超のlock、60秒超のtransaction、slow query、DB再起動、backup ageを観測し、閾値超過時の通知を確認する。
10. 初年度と3年目の月額、初期構築、月次保守、復元訓練、patch・LTSまたはmajor更新の実時間を記録する。

どちらかが必須条件を満たさない場合は、その候補を`CP-0010`へ進めない。両方が不合格の場合は、整合性や復旧要件を黙って弱めず、負荷プロファイル、hosting方式、費用上限を再検討する。

## 根拠資料

外部資料はすべて2026-09-12に確認した。主要な根拠は本文中に直接リンクした。共通のdriver・migration対応は[SQLAlchemy included dialects](https://docs.sqlalchemy.org/en/20/dialects/index.html)と[Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)を参照した。MongoDBのtransaction機能は[MongoDB transactions](https://www.mongodb.com/docs/manual/core/transactions/)、SQLiteのwriter制約は[SQLite isolation](https://www.sqlite.org/isolation.html)も確認した。

現在の要求は[DB要件](../architecture/database-requirements.md)、entityと不変条件は[データモデル](../architecture/data-model.md)、開発toolchainとmigration方針は[ADR-0013](../adr/0013-python-toolchain-and-migrations.md)を正とする。この調査資料のversion、点数、見積もりは基準日時点の比較であり、現在仕様や採用判断の代わりにはしない。
