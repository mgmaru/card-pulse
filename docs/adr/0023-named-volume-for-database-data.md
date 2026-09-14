# ADR-0023: DBのdata directoryを開発と本番で分けず、named volumeに統一する

- 状態: Accepted
- 日付: 2026-09-14
- 決定者: プロジェクトオーナー
- 置換するADR: なし
- 置換されたADR: なし

## Context

`compose.yaml`はDBのdataをComposeが宣言するnamed volume `db-data`へ置いているが、その選択を記録した文書が無い。[ADR-0016](0016-local-compose-artifact-volume.md)がhost側のbind mountを退けたのはartifact storageについての判断で、DBのdata directoryは対象に含めていなかった。

`CP-0014`で`var/`の層を決めた際に、この空白が具体的な提案として現れた。PGDATAを`var/db/`へbind mountすれば、開発中はhostのtoolからdata fileへ直接届く。一方で本番配置ではhost pathへの依存がorchestrationの妨げになるため、そちらはnamed volumeにする。つまり開発と本番で方式を分ける案である。

判断の前提にした事実は次のとおり。いずれも確認日は2026-09-14である。

- PostgreSQLのfile system level backupは、[File System Level Backup](https://www.postgresql.org/docs/18/backup-file.html)が「The database server *must* be shut down in order to get a usable backup.」と述べるとおり、serverを停止しないと使えるcopyにならない。同じ節は、個別のtableやdatabaseだけをfileから取り出すことはできず「file system backups only work for complete backup and restoration of an entire database cluster」とも述べている。
- [Upgrading a PostgreSQL Cluster](https://www.postgresql.org/docs/18/upgrading.html)は「For *major* releases of PostgreSQL, the internal data storage format is subject to change」とし、major versionを跨ぐ移行はdumpとrestoreまたは`pg_upgrade`で行うとしている。data directoryをそのまま持ち越すことはできない。
- [公式postgres imageのREADME](https://github.com/docker-library/docs/blob/master/postgres/README.md)によれば、PGDATAはPostgreSQL 18以降version固有のpath（`/var/lib/postgresql/18/docker`）になり、`initdb`は実行userが`/etc/passwd`に存在することを要求する。PGDATAの所有者が実行uidと一致している必要があり、一致しないmount先では`chown`等の準備が要る。
- 開発機からDBの中身を読む経路はすでにある。`compose.yaml`は`127.0.0.1:5432`を公開しており、host側のpsqlやGUI clientが接続できる。この公開はmigrationとintegration testのために行ったものだが、同じ経路で中身を見られる。

## Decision

### DBのdata directoryはnamed volumeに置く

DBのdataは、Composeが宣言するnamed volume `db-data`に置く。`var/db/`を含むhost pathへのbind mountは採らない。

**bind mountが利点になるのはhostのtoolで開けるfileの場合だが、PGDATAはhostから開いても読めず、serverを停止しなければ複製もできず、cluster全体でしかやり取りできない。** 取り出せるのは「開けないfileが見える」状態だけで、その代わりに所有者の一致をOSごとに用意することになる。読めるfileであるraw artifactについて[ADR-0016](0016-local-compose-artifact-volume.md)がbind mountを退けた理由は、PGDATAではさらに強く当てはまる。

データの持ち出しと移植は論理backup（`pg_dump`）で行う。[ADR-0014](0014-postgresql-self-hosted.md)はすでに論理backupを復元の正としており、major versionを跨げる経路もこちらだけである。出力の置き場は`var/db/`とする（[ADR-0022](0022-configuration-secret-and-local-data-storage.md)）。

開発中にDBの中身を見る要求は、公開済みの`127.0.0.1:5432`へpsqlまたはGUI clientで接続して満たす。fileとして触る経路は用意しない。

### 開発と本番で方式を分けない

同じ`compose.yaml`を開発機でも将来の配置でも使い、volumeの方式を環境で切り替えない。

**方式を分けると、日常的に動かす構成とCIが検証する構成が、いちばん壊れ方の分かりにくい永続化層で食い違う。** `CP-0061`の`Compose environment` jobが毎回検証しているのは`compose.yaml`一つであり、開発機だけ別方式にすれば、その検証は本人が使う構成を通らなくなる。orchestrationへ移す際にhost pathへの依存が無いという利点も、分けずに得られる。

## Consequences

- `docker compose down --volumes`と、macOSでは`colima delete`によって、DBのデータは消える。失って困るデータが生じた時点で、それより前にdumpの手順が要る。実データが生まれるのは`CP-0024`、backupと空環境への復元は`CP-0044`が扱う。
- VM消失やdisk障害に対する保護もdumpが担う。稼働中のPGDATAをhostのfile単位backupへ含めても、serverを停止しないcopyはPostgreSQLが使えるbackupとして扱わないため、保護にならない。
- 開発機からDBへ届く手段はpsqlとGUI clientに限られる。`var/db/`に現れるのはdumpだけで、稼働中のdata fileは現れない。
- artifact storageの扱いは[ADR-0016](0016-local-compose-artifact-volume.md)のまま変えない。原本は読めるfileなので、`docker compose cp`で`var/raw/`へ取り出せる。
- 実データの量が増え、dumpと復元の所要時間がDB要件の`DB-REC-02`を満たせなくなった場合は、物理backupを含めてこのADRを置き換える。

## Alternatives considered

- **開発だけ`var/db/`へbind mountし、本番はnamed volumeにする**: hostのfile managerからdata fileが見えるが、PGDATAは読めるfileではないため見えても使えない。加えて`initdb`が要求する所有者の一致をOSごとに用意することになり、CIが検証する構成とも食い違う。
- **開発・本番ともbind mountで統一する**: 方式は一つになるが、配置先でhost pathへ依存する問題が残り、PGDATAがhostから読めないという性質も変わらない。
- **volumeのdirectoryをcopyして移植する**: 手順は短く見えるが、serverを停止したcluster全体のcopyでしか成立せず、major versionを跨げない。`pg_dump`より制約が強い。
- **開発中のデータを失ってよいものとして扱い、移植を考えない**: 現時点ではschemaも実データも無いため成立するが、`CP-0024`以降に取り込んだ原本と、人が下したreviewの判断は作り直せない。その時点で同じ判断をやり直すことになる。

## Validation

- `tests/unit/test_local_environment.py`が、host pathのbind mountが読み取り専用の初期化scriptだけであることを検査する。書き込み可能なbind mountを足すと失敗する。
- `CP-0044`で空環境への復元を実測し、`DB-REC-02`のRTOに収まるかを確認する。収まらない場合は本ADRを再検討する。
