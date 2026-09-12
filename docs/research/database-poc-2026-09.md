# CP-0009 DB PoC結果

> 状態: 調査完了
>
> 基準日: 2026-09-12
>
> 対象: [CP-0008](database-candidate-comparison-2026-09.md)で絞ったPostgreSQL 18.6とMariaDB 12.3.3

## 結論

PostgreSQL 18.6とMariaDB 12.3.3の両方が、[DB要件のPoC合格条件](../architecture/database-requirements.md#cp-0009のpoc合格条件)10項目を1倍（約540万行）と10倍（約4,430万行）の両方で満たした。応答時間、取込時間、復旧時間、費用のいずれも基準に対して余裕があり、性能を理由にどちらかを落とす結果にはならなかった。

差が出たのは性能ではなく、追記型保存をDBの権限で守れるか、migrationが失敗したときに何が残るか、復元にどれだけ時間がかかるかである。

| 候補 | PoC合格条件 | 測定で確認した弱点 | CP-0010への申し送り |
| --- | --- | --- | --- |
| PostgreSQL 18.6 | 10項目すべて充足 | 書込みの最大値が外れる（10倍で29.6秒）。checkpointとautovacuumの調整が要る | 実データでの書込みtail調整を前提に採用可否を判断する |
| MariaDB 12.3.3 | 10項目すべて充足 | applicationが外部key検査を止める実装を書いた場合、追記専用roleでも実行できてしまう。DDLがtransactionでないため、失敗したmigrationもdowngradeも部分適用のまま残る。10倍の論理復元がPostgreSQLの約5倍 | 上記3点を運用手順とapplication側で埋める費用を評価する |

MariaDBの外部key検査は、[CP-0008の共通検証事項](database-candidate-comparison-2026-09.md#cp-0009の共通検証事項)4が求める「runtime roleがconstraint検査を無効化できないこと、または防止策」を満たさない。どちらのDBも既定では検査しており、MariaDBが自動で無効化するわけではないが、applicationが無効化するSQLを発行した場合にDB側で止める手段がない。実装規約とreview、または定期検査で補う必要がある。[ADR-0002](../adr/0002-append-only-provenance.md)の追記型保存をDB権限で強制する設計方針との適合度は、この点でPostgreSQLが上回る。

この文書はDB製品の採用決定ではない。製品とhosting方式は`CP-0010`のADRで決定し、[ADR-0004](../adr/0004-server-database-selection.md)の未決事項を解消する。

## 測定環境

PoCはプロジェクトオーナーのローカル環境で実施した。両候補は同じhostで順に、常に片方だけを起動して測定した。

| 項目 | 内容 |
| --- | --- |
| Host | macOS 26.5、arm64（Apple Silicon）、10 core、24 GiB memory、内蔵SSD |
| DB | PostgreSQL 18.6（Homebrew `postgresql@18`）、MariaDB 12.3.3（Homebrew `mariadb`） |
| 実行方法 | PoC専用のdata directoryとportを持つlocal instance。`127.0.0.1`のみを待ち受ける |
| Python | CPython 3.14.5 |
| library | SQLAlchemy 2.0.52、Alembic 1.20.0、psycopg 3.3.5（binary）、PyMySQL 1.2.0 |
| harness | [`scripts/db_poc/`](../../scripts/db_poc/README.md)。`uv run python -m dbpoc.run_all <engine> --scale <1\|10>` |
| 生成物 | `var/db-poc/`（生成データ、DB、backup、測定結果JSON）。Git管理外 |

測定条件として固定したserver設定は次のとおりである。両者にbuffer 2 GiBと`max_connections` 50を与え、commit時のdurabilityを有効にした。

| 設定 | PostgreSQL 18.6 | MariaDB 12.3.3 |
| --- | --- | --- |
| buffer | `shared_buffers=2GB`、`effective_cache_size=6GB`、`work_mem=64MB` | `innodb_buffer_pool_size=2G` |
| 書込み耐久性 | `synchronous_commit=on`、`max_wal_size=8GB` | `innodb_flush_log_at_trx_commit=1`、`innodb_log_file_size=2G` |
| 接続 | `max_connections=50` | `max_connections=50` |
| 既定isolation | `read committed` | `REPEATABLE-READ` |
| 文字set | UTF8 / `locale=C` | `utf8mb4` / `utf8mb4_unicode_ci` |
| その他 | `pg_stat_statements`有効、`log_min_duration_statement=1000`、`log_lock_waits=on` | `sql_mode=STRICT_TRANS_TABLES,...`、`slow_query_log=1`、`long_query_time=1`、`innodb_lock_wait_timeout=10` |

### 計画からの逸脱

[CP-0008の共通検証事項](database-candidate-comparison-2026-09.md#cp-0009の共通検証事項)に対して、次の3点は今回測定していない。いずれも候補間の比較ではなく実行基盤に関する条件であり、`CP-0012`と`CP-0060`の環境整備で確認する。

- container imageではなくHomebrewのlocal instanceで実行した。測定host上にcontainer runtimeが無く、engine間の比較に必要な同一条件はport・data directory・設定の固定で確保できるためである。image digestの固定とComposeでの起動は`CP-0012`で確認する。
- CIのamd64環境では実行していない。Apple Silicon（arm64）のみの結果である。
- CPython 3.14.5で測定した。[ADR-0013](../adr/0013-python-toolchain-and-migrations.md)は3.14.7を固定する方針だが、測定時点でuvが配布するbuildは3.14.5だった。driverとAlembicの適合確認が目的であり、patch差は測定結果へ影響しないと判断した。

## 検証したデータと負荷

[DB要件の初期負荷プロファイル](../architecture/database-requirements.md#初期負荷プロファイル)の件数をそのまま生成し、1倍と10倍で同じ手順を実行した。同じ生成ファイルを両候補へ投入するため、投入時間と容量の差はDBの差だけを表す。

| 生成対象 | 1倍 | 10倍 | 備考 |
| --- | ---: | ---: | --- |
| `card_identity` | 12,000 | 120,000 | 同定対象のカード |
| `ingest_run` | 1,207 | 2,215 | 28日分と履歴分 |
| `raw_artifact` | 15,095 | 141,095 | 原本本体は別storage |
| `processing_run` | 15,095 | 141,095 | |
| `extracted_record` | 1,059,000 | 8,619,000 | 28日分840,000×倍率＋履歴219,000 |
| `observation_candidate` | 1,059,000 | 8,619,000 | |
| `identity_resolution_attempt` | 2,118,000 | 17,238,000 | 1候補につき確定1件と棄却1件 |
| `price_observation` | 1,059,000 | 8,619,000 | |
| `review_item` | 84,000 | 840,000 | 70%がpending |
| 合計 | 5,422,397 | 44,339,405 | 生成時間9秒 / 84秒 |

10倍プロファイルはカード件数も10倍にするため、1カードあたりの観測数は1倍とほぼ同じ（約70〜90件）になる。10倍は総量に対する余裕を見る条件であり、1カードの履歴の深さを増やす条件ではない。queryの応答時間が1倍と10倍で単調に悪化しないのはこのためである。

28日分の広い分布に加えて、代表カード200件へ1年分（365日×3店舗、219,000件）の履歴を生成し、`DB-QRY-03`の対象にした。`raw_artifact`が参照する原本fileは実体を作成し、復元検証で存在とhashを確認できるようにした。

PoC schemaは[データモデル](../architecture/data-model.md)の部分集合で、原本、処理実行、抽出結果、観測候補、同定試行、確定観測、review、訂正履歴を分けて持つ。確定観測の訂正は`price_observation`を更新せず`price_observation_correction`へ追記し、queryは最新の訂正だけを見て有効・無効を判定する。これは[ADR-0002](../adr/0002-append-only-provenance.md)の追記型保存をrole権限で強制できるようにするためで、runtime roleは確定観測へ`UPDATE`も`DELETE`もできない。

一括投入だけは両候補とも外部keyの検査を止めて実行し、投入後に検査を戻して参照整合を確認した（両候補とも不整合0件）。runtimeの取込、再解析、同時実行測定はすべての制約を有効にしたまま実行している。

```mermaid
flowchart LR
    G[決定的なデータ生成<br/>TSV + 原本file] --> M[Alembic migration<br/>空DB]
    M --> L[一括投入<br/>容量・時間]
    L --> D[1日分の取込<br/>制約有効]
    D --> Q[8 reader + 2 writer<br/>query p95]
    Q --> I[冪等性・制約・障害]
    I --> R[28日分の再解析]
    R --> C[後方互換migration<br/>失敗migration]
    C --> B[暗号化backup]
    B --> V[空環境へ復元して検証]
```

## 結果

[PoC合格条件](../architecture/database-requirements.md#cp-0009のpoc合格条件)の順に記録する。数値はすべて`var/db-poc/results/`のJSONから引用している。

### 1. Migrationと失敗時の識別

空DBへの`alembic upgrade`、既存schemaへの追加、offline SQL生成は両候補で成功した。差が出たのは複数DDLを含むmigrationが途中で失敗した場合である。

| 項目 | PostgreSQL 18.6 | MariaDB 12.3.3 |
| --- | --- | --- |
| 空DBへのupgrade (秒) | 0.2 | 0.9 |
| offline SQL文数 | 37 | 35 |
| 後方互換migration (秒) | 2.1 | 7.7 |
| migration中の旧query p95 (ms) | 0.42 | 0.45 |
| migration中の旧query最大 (ms) | 1,923.58 | 70.53 |
| 失敗migrationの部分適用 | なし | あり |

PostgreSQLはDDLをtransactionで実行するため、3文目のunique index作成が失敗した時点で先行する`ADD COLUMN`と`CREATE TABLE`も巻き戻り、schemaは失敗前と同じだった。MariaDBはDDLごとに暗黙commitが起きるため、失敗時に`review_item.triage_note`列と`migration_probe` tableが残った。どちらも`alembic_version`は前のrevisionのままなので、revisionだけでは部分適用を判別できない。MariaDBでは失敗したmigrationが作ったobjectを個別に削除する回復手順が必要で、PoCでは2つのobjectを削除して整合させた。

### 2. 容量と投入時間

**1倍プロファイル**

| 項目 | PostgreSQL 18.6 | MariaDB 12.3.3 |
| --- | ---: | ---: |
| 投入行数 | 5,422,405 | 5,422,405 |
| 投入時間 (秒) | 23.4 | 20.7 |
| 統計更新 (秒) | 0.6 | 0.0 |
| table (MB) | 938 | 838 |
| index (MB) | 494 | 622 |
| table+index (MB) | 1,432 | 1,460 |
| data directory (MB) | 10,056 | 4,283 |
| WAL・redo log (MB) | 8,590 | 2,147 |

**10倍プロファイル**

| 項目 | PostgreSQL 18.6 | MariaDB 12.3.3 |
| --- | ---: | ---: |
| 投入行数 | 44,339,413 | 44,339,413 |
| 投入時間 (秒) | 177.5 | 322.8 |
| 統計更新 (秒) | 2.3 | 0.1 |
| table (MB) | 7,661 | 6,848 |
| index (MB) | 4,028 | 5,027 |
| table+index (MB) | 11,688 | 11,875 |
| data directory (MB) | 20,312 | 14,846 |
| WAL・redo log (MB) | 8,590 | 2,147 |

table+indexの合計は両候補ともほぼ同じで、行あたり264 B（PostgreSQL）と268 B（MariaDB）だった。内訳は異なり、MariaDBはtableが小さくindexが大きい。MariaDBが外部key列へindexを自動生成するためで、PoC schemaでは`price_observation`だけで3つの追加indexが作られた。

この行あたりbyte数から、1倍プロファイルを3年間保持した場合の構造化データは約44〜45 GB、`DB-CAP-03`が求める50%の空きを加えて約67 GBになる。1倍と10倍で行あたりbyte数がほぼ変わらないため、この推定は件数に対して線形とみなせる。

data directoryの実サイズはWAL・redo logを含むため、table+indexより大きい。PostgreSQLは`max_wal_size=8GB`の設定どおりWALを確保・再利用しており、空き容量の計画では上限を見込む必要がある。

### 3. 同時実行とqueryの応答時間

8 readerと2 writerを同時に動かした状態で、5つの代表queryは両候補とも目標p95を大きく下回った。

**1倍プロファイル（単位: ms）**

| Query | 目標p95 | PG cold | PG warm単独 | PG 同時実行p95 | Maria cold | Maria warm単独 | Maria 同時実行p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DB-QRY-01 | 200 ms | 1.50 | 0.44 | 2.30 | 2.09 | 0.35 | 1.92 |
| DB-QRY-02 | 1000 ms | 14.58 | 8.73 | 134.63 | 16.28 | 10.78 | 60.51 |
| DB-QRY-03 | 500 ms | 3.79 | 2.32 | 13.01 | 3.78 | 3.31 | 10.04 |
| DB-QRY-04 | 200 ms | 1.46 | 0.48 | 1.40 | 1.19 | 0.26 | 1.39 |
| DB-QRY-05 | 200 ms | 0.36 | 0.18 | 0.99 | 0.59 | 0.42 | 1.53 |

**10倍プロファイル（単位: ms）**

| Query | 目標p95 | PG cold | PG warm単独 | PG 同時実行p95 | Maria cold | Maria warm単独 | Maria 同時実行p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DB-QRY-01 | 200 ms | 3.50 | 0.41 | 1.30 | 12.12 | 0.69 | 2.85 |
| DB-QRY-02 | 1000 ms | 19.96 | 9.36 | 62.05 | 561.62 | 11.48 | 74.27 |
| DB-QRY-03 | 500 ms | 4.45 | 2.03 | 12.13 | 72.82 | 3.73 | 15.70 |
| DB-QRY-04 | 200 ms | 4.55 | 1.30 | 3.52 | 2.22 | 0.36 | 3.89 |
| DB-QRY-05 | 200 ms | 0.75 | 0.18 | 0.89 | 0.71 | 0.45 | 2.55 |

**1倍プロファイルの同時実行**

| 項目 | PostgreSQL 18.6 | MariaDB 12.3.3 |
| --- | ---: | ---: |
| 測定時間 (秒) | 181.3 | 182.1 |
| reader / writer | 8 / 2 | 8 / 2 |
| writer batch p95 (ms) | 23.21 | 32.12 |
| writer batch 最大 (ms) | 2,565.31 | 98.05 |
| 追記した観測数 | 1,070,580 | 995,160 |
| query実行数 | 81,101 | 125,740 |
| 失敗数 | 0 | 0 |
| 最大接続数 | 12 | 11 |
| deadlock | 0 | 0 |

**10倍プロファイルの同時実行**

| 項目 | PostgreSQL 18.6 | MariaDB 12.3.3 |
| --- | ---: | ---: |
| 測定時間 (秒) | 187.2 | 180.8 |
| reader / writer | 8 / 2 | 8 / 2 |
| writer batch p95 (ms) | 36.85 | 90.74 |
| writer batch 最大 (ms) | 29,637.50 | 194.02 |
| 追記した観測数 | 496,920 | 452,460 |
| query実行数 | 74,276 | 108,562 |
| 失敗数 | 0 | 0 |
| 最大接続数 | 12 | 11 |
| deadlock | 0 | 0 |

実行計画は両候補とも意図したindexを使った。`DB-QRY-01`から`DB-QRY-03`は`ix_observation_card_observed`、`DB-QRY-04`は主keyの連鎖、`DB-QRY-05`は`ix_review_state_priority`である。有効・無効の判定に使う訂正履歴の参照も`ix_correction_observation`でindex参照になった。

writer側の挙動には差がある。PostgreSQLはbatchの中央値とp95が小さい一方で、最大値が1倍で2.6秒、10倍で29.6秒に達した。checkpointとautovacuumの影響とみられる。MariaDBはp95が大きい代わりに最大値が10倍でも194 msに収まった。1日分の取込は両候補とも基準の10分に対して十分速いため採否を分けないが、1回の書込みの最悪値を重視する場合、PostgreSQLではcheckpointとautovacuumの設定を実データで調整する必要がある。

cold cacheの値は10倍で差が開いた。MariaDBの`DB-QRY-02`は再起動直後の初回実行で561 ms、`DB-QRY-03`は73 msとなり、PostgreSQLの20 msと4 msより大きい。いずれも一度実行した後のwarm cacheでは同等で、合格判定に使うwarm値では目標を大きく下回る。

### 4. 冪等性と取込・再解析の時間

同じ冪等keyの観測を、逐次で2回、および2 writerから同時に投入した場合、どちらの候補でも確定観測は1件だけになった。28日分の再解析でも、同じ原本から同じ冪等keyを再生成して投入し、確定観測は1件も増えず、重複した冪等keyは0件だった。

**1倍プロファイル**

| 項目 | 基準 | PostgreSQL 18.6 | MariaDB 12.3.3 |
| --- | --- | ---: | ---: |
| 1日分の取込時間 (秒) | 600以内 | 3.6 | 5.5 |
| 1日分の追記行数 | - | 154,500 | 154,500 |
| 取込中のread p95 (ms) | - | 0.59 | 0.65 |
| 28日分の再解析 (秒) | 28,800以内 | 68.5 | 216.8 |
| 再解析で増えた確定観測 | 0 | 0 | 0 |
| 重複した冪等key | 0 | 0 | 0 |

**10倍プロファイル**

| 項目 | 基準 | PostgreSQL 18.6 | MariaDB 12.3.3 |
| --- | --- | ---: | ---: |
| 1日分の取込時間 (秒) | 600以内 | 75.2 | 137.7 |
| 1日分の追記行数 | - | 1,545,000 | 1,545,000 |
| 取込中のread p95 (ms) | - | 0.70 | 14.70 |
| 28日分の再解析 (秒) | 28,800以内 | 769.6 | 2,381.4 |
| 再解析で増えた確定観測 | 0 | 0 | 0 |
| 重複した冪等key | 0 | 0 | 0 |

冪等追記の書き方は候補で異なる。PostgreSQLは`INSERT ... ON CONFLICT (idempotency_key) DO NOTHING`で、`INSERT`権限だけで実行できる。MariaDBの`INSERT ... ON DUPLICATE KEY UPDATE`は更新が実質no-opでも`UPDATE`権限を要求するため、確定観測を更新できないWorker roleでは使えない。`INSERT IGNORE`は重複key以外のerrorも警告へ降格させるので採用しない。PoCでは通常の`INSERT`を実行し、重複key error（PostgreSQL: SQLSTATE 23505、MariaDB: errno 1062）だけを冪等な成功として扱う方式にした。この方式は両候補で同じ結果になった。

### 5. 障害時の原子性と再起動

- transaction途中でconstraint違反を起こすと、同じtransactionで先に投入した正常行も残らなかった（`NOT NULL`、`CHECK`、外部key、複合uniqueの5ケース）。applicationはSQLSTATEまたはerrnoで違反の種類を判別できる。価格0は欠損と区別して保存できた。
- 未commitのtransactionを持つclient processを`SIGKILL`した場合、投入中の行は残らなかった。
- commit済みの行とuncommitの行がある状態でDB processを`SIGKILL`し、再起動した場合、commit済みの行はすべて残り、uncommitの行は残らなかった。強制終了から接続を受け付けるまでは4.1〜10.8秒（4回の測定）で、この値には起動commandの実行時間を含む。

### 6. 一貫性、集計、provenance、review競合

- `REPEATABLE READ`のtransaction内で2回読んだ件数と最新時刻は一致し、同じtransactionの外では後から確定した観測が見えた。1つのAPI応答を構成する複数queryは同じ`as_of`を読める。
- 最新価格、中央値、最高値、最低値、店舗数、鮮度は`DB-QRY-01`と`DB-QRY-02`で計算できた。中央値の構文は異なり、PostgreSQLは`percentile_cont(0.5) WITHIN GROUP`、MariaDBは`MEDIAN() OVER ()`を使う。
- 確定観測から候補、抽出結果、processing run、原本metadata、取込runまでを1 queryで追跡できた（`DB-QRY-04`）。
- 同じreview itemを2 sessionが同時に確定した場合、成功するのは1 sessionだけだった。PostgreSQLでは敗者の条件付き`UPDATE`が0件更新になり、MariaDBではerrno 1020が返る。どちらもapplicationが再読込みへ分岐できる。
- deadlock、lock待ちtimeoutは意図的に発生させ、どちらも区別できるerrorとして返った（PostgreSQL: SQLSTATE 40P01 / 55P03、MariaDB: errno 1213 / 1205）。

### 7. 後方互換なschema変更

列追加、大きなtableへのindex追加、table追加を含むmigrationを、旧queryと書込みを実行したまま適用した。旧queryはどちらの候補でも失敗せず、適用後に新しい列を使うqueryが成功した。所要時間と旧queryへの影響は[Migrationの表](#1-migrationと失敗時の識別)に示す。

migration中の旧queryへの影響は候補で異なった。PostgreSQLは`ALTER TABLE`とindex作成の間にlockを取るため旧queryの最大が1.9秒まで伸び、MariaDBのInnoDB online DDLでは70 msにとどまった。p95はどちらも1 ms以下で、待たされるのは一部のqueryだけである。

rollbackとbackup復元の境界も候補で異なる。PostgreSQLでは同じ変更のAlembic downgradeが0.2秒で成功し、追加した列とindexとtableが消えた。MariaDBでは同じdowngradeが失敗した。`price_observation`の外部key（`shop_id`）を支えるindexが、0002で追加した`ix_observation_shop_observed`に置き換わっており、これを削除しようとしてerrno 1553（`Cannot drop index ... needed in a foreign key constraint`）になる。しかもdowngradeは先に`price_alert_rule`を削除した後で止まるため、`alembic_version`は0002のまま、schemaだけが中途半端な状態で残った。PoCでは削除されたtableを手動で作り直して整合させた。

つまり後方互換な変更でも、MariaDBではdowngradeが必ず成功するとは限らず、失敗した場合は手作業の修復かbackup復元が必要になる。MariaDBを採用する場合、downgradeをstaging相当の環境で先に検証し、外部keyを支えるindexを削除・置換するmigrationはbackup取得を前提にする必要がある。

### 8. Backupと復元

暗号化した論理backup、global object、migration revision、原本manifest、file別checksumを1つのbackup setとして取得し、一度も同じデータを持ったことがない空instanceへ復元した。復元後に件数、constraint数、代表1,000行のhash、DBが参照する全原本の存在を検証した。

**1倍プロファイル**

| 項目 | PostgreSQL 18.6 | MariaDB 12.3.3 |
| --- | ---: | ---: |
| backup取得 (秒) | 37.3 | 44.4 |
| 暗号化 (秒) | 0.4 | 0.4 |
| backup容量 (MB) | 329 | 328 |
| 空環境の準備 (秒) | 1.1 | 6.3 |
| 復元 (秒) | 11.4 | 204.3 |
| 検証 (秒) | 0.5 | 1.5 |
| 復元+検証 合計 (秒) | 13.0 | 212.2 |
| 件数一致 | はい | はい |
| 代表行hash一致 | はい | はい |
| constraint一致 | はい | はい |
| 欠落artifact | 0 | 0 |

**10倍プロファイル**

| 項目 | PostgreSQL 18.6 | MariaDB 12.3.3 |
| --- | ---: | ---: |
| backup取得 (秒) | 218.4 | 299.7 |
| 暗号化 (秒) | 2.3 | 2.3 |
| backup容量 (MB) | 1,841 | 1,880 |
| 空環境の準備 (秒) | 0.7 | 6.1 |
| 復元 (秒) | 242.0 | 1,276.8 |
| 検証 (秒) | 4.2 | 12.0 |
| 復元+検証 合計 (秒) | 247.0 | 1,294.8 |
| 件数一致 | はい | はい |
| 代表行hash一致 | はい | はい |
| constraint一致 | はい | はい |
| 欠落artifact | 0 | 0 |

復元時間には大きな差がある。PostgreSQLのcustom形式は`pg_restore --jobs`で並列に復元でき、MariaDBの論理dumpはSQL文の逐次replayになる。10倍プロファイルでもどちらも`DB-REC-02`の「空環境へのrestoreと整合検証は2時間以内」を満たしたが、余裕は大きく異なる。

#### 取得時の一貫性と復元時の検証

backupの取得では差がない。どちらも更新が続くDBから一貫したsnapshotを取れる。PostgreSQLの`pg_dump`は常に1 transactionのsnapshotから読み、MariaDBはPoCで使った`--single-transaction`がInnoDBのsnapshotから読む。取得中の更新によって参照の切れた行が生まれることはない。

差は復元時の検証にある。生成したbackup setを復号して内容を確認した。

- `mariadb-dump`の出力は先頭に`SET FOREIGN_KEY_CHECKS=0`と`SET UNIQUE_CHECKS=0`を含み、末尾で元の値へ戻す。**復元中は外部key検査が働かない。**これはtoolが既定で出力するもので、利用者が書いたものではない。
- `pg_dump`のcustom形式は検査を止めず、順序で解決する。復元計画はtable、table data、index、foreign key constraintの順で、24個の外部key制約がすべて最後に作られる。**制約を作る時点で既存の全行が検証される**ため、参照の切れた行が含まれていれば復元が失敗する。

したがって、backup元のDBに参照の切れた行があった場合、PostgreSQLは復元の失敗として検出でき、MariaDBは警告なく復元する。

PoCの復元検証（件数、代表1,000行のhash、constraint数、原本fileの存在）は、参照整合そのものをscanしていない。件数もhashも一致するため、この検証では参照の切れた行を検出できない。MariaDBを採用する場合、復元手順へ参照整合の検査を追加する必要がある。PostgreSQLではDBが復元時に検証するため追加不要である。

### 9. Role分離とnetwork

API、Worker、migration、backup、管理者のroleを分け、14通りの操作で期待どおりに許可・拒否されることを確認した。両候補とも、APIは追記も更新もできず、Workerは追記とreview判断の記録はできるが確定観測の`UPDATE`・`DELETE`とDDLはできない。

DB portは`127.0.0.1`だけを待ち受け、同一LANのIPアドレスからの接続は拒否された。

1点だけ差がある。ただし「MariaDBが外部key検査を勝手に外す」という意味ではないため、条件を明確にしておく。

**両候補とも既定で外部key検査を行い、DBが自分でこの設定を書き換えることはない。**検査が止まるのは、applicationが自分のsessionに対して明示的なSQLを発行したときだけで、接続を張り直せば既定へ戻る。したがってこの差は、applicationが検査を外す実装を書いてしまったときに、**DBがそれを拒否できるかどうか**の差である。

| | 検査を止める操作 | Worker roleでの結果 |
| --- | --- | --- |
| PostgreSQL | `SET session_replication_role = 'replica'` | 拒否。`permission denied`（SQLSTATE 42501） |
| MariaDB | `SET SESSION foreign_key_checks = 0` | 成功。`INSERT`権限だけで通る |

PoCではWorker roleでこの操作を実行し、続けて存在しないカードを参照する観測を追記した。MariaDBでは追記に成功し、PostgreSQLは設定変更の時点で拒否されたため追記へ進めなかった。

この構文には正当な用途がある。大量データの一括投入では1行ごとの検査を省く方が速く、PoCの一括投入でも両候補で同等の操作を使った（実行はadmin roleで行い、投入後に検査を戻して参照整合が0件であることを確認している）。正当な用途があるぶん誤用と区別しにくく、runtime roleがこれを実行できるかどうかが運用上の差になる。

MariaDBを採用する場合、DB側に無効化を防ぐ手段がない。実装規約とcode reviewで担保し、参照整合を定期的に検査する運用が必要になる。

### 補: 監視項目（DB-OPS-02）

PoC合格条件とは別に、`DB-OPS-02`が求める観測項目を1倍プロファイルで確認した。両候補とも次を検出できた。

| 観測対象 | 閾値 | PostgreSQLの取得元 | MariaDBの取得元 |
| --- | --- | --- | --- |
| 接続使用率 | 70%で警告 | `pg_stat_activity`、`max_connections` | `Threads_connected`、`max_connections` |
| storage使用率 | 70%警告 / 85%critical | data directoryとvolume空き容量 | 同左 |
| 5秒を超えるlock待ち | 5秒 | `pg_stat_activity.wait_event_type='Lock'` | `information_schema.innodb_trx.trx_state='LOCK WAIT'` |
| 60秒を超えるtransaction | 60秒 | `pg_stat_activity.xact_start` | `information_schema.innodb_trx.trx_started` |
| slow query | 1秒 | `pg_stat_statements`、server log | `performance_schema`のdigest、slow query log |
| DB再起動 | - | `pg_postmaster_start_time()` | `Uptime` |
| backupの経過時間 | 26時間で警告 | backup manifestの基準時刻 | 同左 |

lock待ちと長時間transactionは、意図的に8秒のlock待ちと65秒のtransactionを発生させて検出を確認した。

### 10. 費用と運用時間

| 項目 | 基準 | PostgreSQL 18.6 | MariaDB 12.3.3 |
| --- | --- | ---: | ---: |
| 3年分の構造化データ (GB) | - | 44 | 45 |
| 50%余裕を加えた計画容量 (GB) | `DB-CAP-03` | 66 | 68 |
| backup 1世代 (1倍実測, MB) | - | 329 | 328 |
| backup 1世代 (10倍実測, GB) | - | 1.8 | 1.9 |
| backup/DB容量比 | - | 0.16 | 0.16 |
| 3年時点のbackup 11世代 (GB) | `DB-REC-03` | 77 | 78 |
| 日次backupの所要 (1倍, 秒) | - | 38 | 45 |
| 復元訓練 (1倍, 秒) | `DB-REC-02` 7,200以内 | 13 | 212 |
| 復元訓練 (10倍, 秒) | `DB-REC-02` 7,200以内 | 247 | 1295 |
| 空DBへのmigration (秒) | - | 0.2 | 0.9 |
| 電力5W仮定の月額 (円) | `DB-COST-01` 5,000以下 | 100 | 100 |
| 電力10W仮定の月額 (円) | `DB-COST-01` 5,000以下 | 201 | 201 |
| 電力20W仮定の月額 (円) | `DB-COST-01` 5,000以下 | 401 | 401 |

self-host構成では月額のservice費用が発生しないため、`DB-COST-01`の月額3,000円目標と5,000円上限に対する余裕は大きい。既存hardwareを使う場合の増分は電力と保存先容量である。電力は測定していないため、DB常時稼働による増分を平均5W、10W、20Wと仮定した感度で示す。低圧の平均単価は27.85円/kWh（2026年5月、[新電力ネット](https://pps-net.org/unit)、確認日: 2026-09-12）を使う。仮定が20Wでも月額約400円で、上限に対して十分小さい。

運用時間は測定した自動処理の所要時間で、人手の確認時間を含まない。`DB-OPS-03`の「定常DB保守は月1時間以内」に対しては、日次backupが自動で完了する前提なら両候補とも余裕がある。ただし10倍規模でMariaDBの復元訓練を行う場合、1回あたりの所要時間がPostgreSQLの数倍になる。

## 候補間の差

測定で確認した候補差のうち、Card Pulseの設計に影響するものを示す。性能差ではなく、実装方法または運用手順が変わる項目である。

| 観点 | PostgreSQL 18.6 | MariaDB 12.3.3 | Card Pulseへの影響 |
| --- | --- | --- | --- |
| UUID | native `uuid`型。reflectionも`UUID` | native `uuid`型。reflectionも`UUID` | どちらでも内部UUIDをそのまま保存できる。ただしSQLAlchemyの汎用`Uuid`型はMariaDBで`CHAR(32)`になるため、dialect固有の型指定が必要 |
| JSON | `jsonb`。型として保持 | `longtext` + `json_valid()` CHECK | source metadataの保存は両方可能。MariaDBではJSON内の値でindexを作る場合にgenerated columnが要る |
| timezone付き日時 | `timestamptz` | `datetime(6)`のみ。timezoneを保持しない | MariaDBではsessionをUTCに固定し、applicationがUTCで書く規約が必須。今回はこの規約で往復一致を確認した |
| DDLのtransaction | あり。失敗したmigrationは巻き戻る | なし。DDLごとに暗黙commit | MariaDBでは部分適用の検出と回復手順をrunbookに持つ必要がある |
| 外部key列のindex | 自動作成しない | 自動作成する | MariaDBはindex容量が増える。不要なindexを消す判断が要る |
| 外部key制約名 | table名から自動生成 | 連番（`1`、`2`...） | MariaDBではmigrationで制約名を明示しないと運用時に識別しにくい |
| 冪等な追記 | `ON CONFLICT DO NOTHING`。`INSERT`権限のみ | 相当構文が`UPDATE`権限を要求。`INSERT IGNORE`は全errorを警告化 | 追記専用roleを保つには、重複key errorを成功として扱う実装に統一する |
| 制約検査の無効化 | superuser専用。runtime roleでは拒否される | `INSERT`権限だけのroleでも実行できる。どちらもDBが自動で外すことはなく、applicationが明示的に発行した場合だけ止まる | applicationが検査を外す実装を書いた場合、MariaDBではDBで止められない |
| 復元時の参照整合 | 外部key制約を最後に作り全行を検証する | dump先頭で検査を外すため検証されない | 参照の切れた行を含むbackupを、PostgreSQLは復元失敗として検出できる |
| 失敗の識別 | SQLSTATE（23505、23503、23514、40P01、55P03） | errno（1062、1452、4025、1213、1205） | どちらも機械判別できる。共通の失敗分類はapplication側で対応表を持つ |
| review競合の敗者 | 条件付き`UPDATE`が0件 | errno 1020 | 再読込みへの分岐条件が候補で変わる |
| migrationのdowngrade | 後方互換な変更を0.2秒で戻せた | 外部keyを支えるindexを削除できずerrno 1553で失敗。部分適用が残った | MariaDBではdowngradeの事前検証とbackupが前提になる |
| 論理復元 | 並列復元が可能 | SQL文の逐次replay | 10倍規模でRTOの余裕が変わる |
| 既定isolation | `read committed` | `repeatable read` | `as_of`の一貫性はいずれも明示指定で満たす |

## 運用上の注意

PoCの過程で、DB製品によらず運用へ反映すべき挙動を確認した。

- transactionを開いたまま放置する読取りは、後続のDDLを止め、DDLの背後で書込みを止める。PostgreSQLでこの状態を再現し、`ALTER TABLE`が6分以上待ち続けた。APIの単文読取りはtransactionを持たない接続で実行し、migrationには`lock_timeout`を設定する。MariaDBも開いたままのtransactionがmetadata lockを保持するため同じ規約が要るが、今回はMariaDBでこの状態を再現していない。
- MariaDBでuserを`CREATE OR REPLACE USER`で作り直すと、そのuserのgrantがすべて消える。roleの作成とpassword更新は`CREATE USER IF NOT EXISTS`と`ALTER USER`へ分ける。
- backup roleは`mariadb-dump --events`が要求する`EVENT`権限を持たない。読取り専用のbackup roleを保つなら、events・routinesを使わないか、backup手順で使う機能を明示する。
- PostgreSQLのWAL容量は`max_wal_size`まで確保される。data volumeの空き容量計画にはtable+indexだけでなくWAL上限を含める。
- MariaDBでsessionの`time_zone`をUTCへ固定すると、`NOW()`はUTCを返す一方で`information_schema.innodb_trx`はserver localの時刻で記録されるため、両者を比較する監視queryが常に空になる。PoCの監視queryは当初この誤りで長時間transactionとlock待ちを検出できず、監視用の接続をserver localの時刻へ合わせて修正した。MariaDBを採用する場合、UTC固定の運用規約と、server localで記録されるmetadataの扱いを分けて決める必要がある。

## 未解決事項とCP-0010への申し送り

- PoCはApple Siliconのlocal instanceで測定した。固定image digestでのDocker Compose起動とCI amd64での再現は`CP-0012`と`CP-0060`で確認する。
- 電力は実測していない。`DB-COST-02`の記録としては仮定値にとどまるため、運用開始後に実測へ置き換える。
- 冪等keyの具体的な構成は`CP-0019`、取込・再解析・review確定のtransaction boundaryは`CP-0020`で決める。PoCでは1つの原本単位を1 transactionとして測定した。
- role別の具体的なgrantは`CP-0022`で確定する。PoCのgrantは検証用の最小構成である。
- MariaDBを採用する場合、部分適用したmigrationの回復手順と、外部key検査の無効化を検出する方法をrunbookに持つ必要がある。PostgreSQLを採用する場合、書込みの最悪値に影響するcheckpointとautovacuumの設定を実データで再評価する。
- PoC schemaは[データモデル](../architecture/data-model.md)の部分集合であり、確定schemaではない。`CP-0016`で実データに合わせて確定する。

## 関連文書

- [DB要件](../architecture/database-requirements.md)
- [CP-0008 DB候補比較](database-candidate-comparison-2026-09.md)
- [DB選定の判断軸](../learning/database-selection.md)
- [データモデル](../architecture/data-model.md)
- [ADR-0004: server型DBと製品選定](../adr/0004-server-database-selection.md)
- [ADR-0013: Python toolchainとmigration](../adr/0013-python-toolchain-and-migrations.md)
- [PoC harness](../../scripts/db_poc/README.md)
