# ADR-0016: ローカル環境のartifact storageをDocker volume上のfilesystemにする

- 状態: Accepted
- 日付: 2026-09-13
- 決定者: プロジェクトオーナー
- 置換するADR: なし
- 置換されたADR: なし

## Context

[ADR-0006](0006-docker-compose-local-development.md)は、ローカル開発環境をDocker Composeで構成し、API、Worker、選定DB、artifact storageを別containerまたは明示的なserviceとして定義すると決めた。DB製品は[ADR-0014](0014-postgresql-self-hosted.md)でself-hostのPostgreSQL 18に確定し、具体的なimage参照を`CP-0012`へ残した。artifact storageは[アーキテクチャ概要](../architecture/overview.md#raw-artifact-storage)が「本人が管理するfilesystem、volume、またはprivate storage service」と書いたままで、どれを使うかは決まっていない。

原本本体に必要な性質は多くない。[ADR-0002](0002-append-only-provenance.md)と[ADR-0007](0007-layered-ingestion-data.md)が求めるのは、取得したbyte列をそのまま保存し、content hashと取得日時をDB側のmetadataとして持ち、保存済み原本から何度でも再解析できることである。検索、集計、参照整合はDBが担い、artifact storageは担わない。

運用条件も限られている。[ADR-0012](0012-private-personal-operation.md)により利用者はプロジェクトオーナー本人だけで、runtimeはInternetへ公開せず、raw artifactは`var/`配下または同等のGit管理外領域に置く。ローカル環境を起動するのは本人の開発機と、`CP-0061`が使うGitHub-hosted runnerの2種類である。

`CP-0012`で選べるのは次の3つだった。MinIO等のS3互換serviceをComposeへ足す、repositoryの`var/raw`をbind mountする、Composeが宣言するnamed volume上のfilesystemを使う。

## Decision

### Artifact storage

ローカル環境のartifact storageは、Composeが宣言するnamed volume `artifacts` 上のfilesystemとし、Worker containerの`/srv/card-pulse/artifacts`へmountする。S3互換serviceをComposeへ足さない。**原本に必要なのはbyte列の保存と再解析だけであり、S3互換serviceを足して増えるのは、署名付きURL、bucket policy、credential rotationという、本人の端末の中では検証対象にならない運用面である。**

host側のbind mountも採らない。container内の非root userとhost側uidの対応が環境ごとに変わり、macOSの開発機とLinuxのCI runnerで同じ手順にならないためである。named volumeはimage側のmount pointの所有者を引き継ぐため、両方で同じ結果になる。原本をhostへ取り出す必要がある場合は`docker compose cp`を使う。

APIはこのvolumeをmountしない。APIが返すのはDBに確定した観測であり、原本本体を読む経路を持たせない。

将来の移行余地は物理配置ではなくコードの境界で保つ。原本の保存と読出しはapplicationが定義するartifact portの後ろに置き、object storageへ移す判断が必要になった時点で、adapterの差し替えとして扱う。

### Service構成

APIとWorkerは同じapplication imageを別commandで起動する。[ADR-0001](0001-modular-monolith.md)のとおりdomainとapplicationを共有し、[ADR-0005](0005-separate-runtime-services.md)のとおりruntimeを分けるという関係を、image 1つとentrypoint 2つでそのまま表す。

image参照はOS variantとdigestで固定する（[ADR-0014](0014-postgresql-self-hosted.md)）。確認日は2026-09-13で、いずれもofficial registryのtagから取得した。

| 用途 | image |
| --- | --- |
| DB | `postgres:18.6-trixie@sha256:4ef4dbc939d61acea57712655ddb4b4ab27419c913f94cca0cd57cb3ea3c2280` |
| applicationのbuild stage | `ghcr.io/astral-sh/uv:0.12.13-trixie-slim@sha256:4298dc3494124b50792f7abbdfe2cae7139c41f4e098f52573f4f6d912cf8bd7` |
| applicationのruntime stage | `debian:trixie-slim@sha256:d7e12182ce18b85b93007c1dedf31f2d29e01ccf3182cc4017c709b6259bc132` |

CPythonのversionは`.python-version`、uvのversionは`pyproject.toml`の`required-version`、Python依存は`uv.lock`を正とし、Dockerfileへ書き写さない。uvはbuild時に自身のversionが`required-version`を満たすか検査するため、image tagとpyproject.tomlの食い違いはbuildの失敗として現れる。

APIとWorkerはDBへsuperuserで接続しない。初期化scriptが`card_pulse_api`と`card_pulse_worker`をlogin roleとして作る。この時点ではschemaが無いためobject権限は与えず、role別のgrantは`CP-0022`で決める。

hostへ公開するのは、loopbackへbindしたDB portとAPI portだけとする。DB portを公開するのは、migrationとhost側のintegration testが同じ端末から接続するためであり、Compose内部networkの外へ出す意図ではない。

### Health check

各serviceのhealth checkはlivenessだけを表し、依存の状態は別経路で報告する。APIは`GET /health`をliveness、`GET /health/dependencies`を依存の状態とし、後者はDBが落ちていてもHTTP 200で`degraded`を返す。Workerはheartbeat fileの新しさをlivenessとし、依存の失敗はheartbeatの内容に記録する。

依存の失敗をhealth checkの失敗として扱うと、DBを止めた瞬間にAPIとWorkerのcontainerがunhealthyになり、[ADR-0005](0005-separate-runtime-services.md)が求める「Collectorの障害をAPIへ波及させない」性質をローカルで観察できなくなる。

### Migrationとschema

このCompose環境はschemaを作らない。[ADR-0013](0013-python-toolchain-and-migrations.md)がDB選定後へ残したAlembic環境は、対象schemaが決まるPhase 2で追加する。追加後もmigrationはAPIとWorkerの起動時に暗黙実行せず、専用roleと明示した手順で実行する（[ADR-0014](0014-postgresql-self-hosted.md)）。

## Consequences

- 新しい開発機で、Docker、`.env`の作成、`docker compose up`の3手順からAPI、Worker、DB、artifact storageを起動できる。手順は[ローカル開発環境](../runbooks/local-development.md)を正とする。
- 原本はDockerが管理する領域に入り、repositoryのworking treeへ現れない。Git、CI artifact、公開backupへ混ざる経路が構成上なくなる一方、原本を直接見るには`docker compose cp`または`docker compose exec`が要る。
- volumeを残した再起動と、全データを捨てる初期化が別のコマンドになる。`docker compose down`はvolumeを残し、`--volumes`を付けたときだけDBと原本を消す。
- backupは、DB dumpとartifact volumeを別の操作で取得し、同じ時点として扱う手順が必要になる。`CP-0021`と`backup-restore` Runbookで決める。
- artifact storageがobject storageではないため、署名付きURL、bucket policy、object lockのような機能は今後も使えない。必要になった時点でartifact adapterの差し替えと新しいADRで判断する。
- health checkがlivenessだけを表すため、「containerはhealthyだがDBが落ちている」状態が起こり得る。状態の確認はAPIの`/health/dependencies`とWorkerのheartbeatが担う。

## Alternatives considered

- **MinIO等のS3互換serviceをComposeへ足す**: 将来object storageへ移す場合に近い形で開発できる。採らなかったのは、原本の保存と再解析にobject storage固有の機能が要らないのに対し、bucket、access key、policyをローカルで保守する必要が増えるためである。移行時に差が出るのはartifact adapterの内部であり、その差し替え余地はport境界で確保できる。
- **repositoryの`var/raw`をbind mountする**: 原本をhostのfile managerやeditorから直接見られる。採らなかったのは、container内の非root userとhost側uidの対応が開発機とCI runnerで異なり、同じ手順が両方で成立しないためである。`var/raw`はhostで直接Workerを動かす場合の既定値としては残す。
- **APIとWorkerで別imageをbuildする**: runtime依存を将来分けやすい。採らなかったのは、現在の依存が完全に同じで、image 2つを保守しても分離されるのは名前だけになるためである。依存が実際に分かれた時点で分割する。
- **依存の状態をhealth checkの結果に含める**: `docker compose ps`だけで異常に気付ける。採らなかったのは、DBを止めた瞬間にAPIとWorkerもunhealthyとなり、service単位の障害分離をローカルで確認できなくなるためである。

## Validation

- `CP-0061`で、空のGitHub-hosted runnerからimage build、起動、各serviceのhealth checkが成功することを検査する。
- `CP-0092`で、`db`を止めた状態で`api`と`worker`がhealthyのままであること、`/health/dependencies`がHTTP 200で`degraded`を返すこと、Worker heartbeatが`degraded`で書かれ続けること、DBの復帰後に両方が`ok`へ戻ることを検査する。health checkを依存の状態まで見る形へ変えると、この検査が失敗する。上のDecisionが選んだ「livenessだけを表す」構成は、正常系の起動検査だけでは壊れても気付けないため、依存を落とした状態の検査を分けて置く。
- 構成の不変条件（pullするimageのdigest固定、公開portのloopback bind、`.env.example`の網羅、artifact volumeのmount先）は`tests/unit/test_local_environment.py`が検査する。
- 次のいずれかが起きた場合にartifact storageの判断を再評価する。
  - 原本の容量が開発機のdiskまたはDocker volumeに収まらなくなる。
  - 本人の複数hostから同じ原本を参照する必要が生じる（[ADR-0012](0012-private-personal-operation.md)の範囲変更を伴う）。
  - `CP-0021`または`backup-restore` Runbookで、volumeのままではDBと原本を同じ時点へ復元できないと判明する。
