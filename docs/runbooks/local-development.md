# Runbook: ローカル開発環境

> 対象: プロジェクトオーナー本人
>
> 最終更新: 2026-09-14
>
> 最終確認日: macOSは2026-09-13。Windows（WSL2）は未実施。確認状況は[前提](#前提)にOSごとに記載する。

Docker ComposeでAPI、Collection Worker、PostgreSQL、artifact storageを起動し、停止・初期化するまでの手順を示す。構成の判断は[ADR-0006](../adr/0006-docker-compose-local-development.md)と[ADR-0016](../adr/0016-local-compose-artifact-volume.md)、container runtimeの選定は[ADR-0018](../adr/0018-per-os-container-runtime.md)、Dockerで再現できる範囲は[Dockerによる環境再現](../learning/docker-environment-reproduction.md)を参照する。

Python側のsetupと品質検査はcontainerを使わない。コマンドは[開発環境と品質検査](../../CONTRIBUTING.md#開発環境と品質検査)を正とする。

## 影響範囲

この手順が作るのは、開発機の中だけで動くDockerのcontainerとvolumeである。Internetへ公開されるものはなく、repositoryのworking treeへ書き込むものもない。ただし「[初期化](#初期化破壊的)」はDBと取得原本を消す。

## 前提

### 共通

repositoryは、container runtimeがmountできる領域へ置く。`compose.yaml`は`./docker/postgres/initdb`をbind mountしており、この領域を外れるとmountが空のdirectoryとして成立してしまう。初期化scriptが実行されず、runtime roleが無いままDBが起動し、APIとWorkerが接続できない。mount先のdirectoryは存在するため、原因が分かりにくい形で失敗する。OSごとの条件は下の節に書く。

その他の共通条件は次のとおり。

- imageのpullとbuildにInternet接続が必要。起動後の運用には不要。
- 使用するhost portは既定で`127.0.0.1:5432`と`127.0.0.1:8000`。他のPostgreSQLが5432を使っている場合は`.env`で変更する。
- 改行コードはcloneした時点でLFになる。`.gitattributes`が強制し、bind mount対象にCRが無いことを`tests/unit/test_local_environment.py`が検査する（[ADR-0018](../adr/0018-per-os-container-runtime.md)）。

以降の「[設定](#設定)」から「[初期化](#初期化破壊的)」までは、OSによらず同じコマンドで実行する。

### macOS

最終確認日: 2026-09-13（Colima 0.10.3、Docker 29.8.0、Docker Compose 5.5.1、Apple Silicon）。

初回だけ次を実行する。

```bash
brew install colima docker docker-compose
```

`docker-compose`はDockerのpluginとして呼び出すため、`~/.docker/config.json`へplugin pathを登録する。既存の設定がある場合はkeyを追加する。

```json
{
  "cliPluginsExtraDirs": ["/opt/homebrew/lib/docker/cli-plugins"]
}
```

Colimaは既定で`$HOME`配下だけをVMへmountする。repositoryは`$HOME`の下に置く。

開発を始めるたびにVMを起動する。停止中は`docker`コマンドがdaemonへ接続できずに失敗する。

```bash
colima start
colima status
```

`colima is running using macOS Virtualization.Framework` が表示されること。既定の割り当ては2 CPU、2GiB memory、100GiB diskで、この構成のbuildと起動はこの範囲に収まる。増やす場合は`colima start --cpu 4 --memory 8`のように指定し、変更した理由をこの節へ追記する。

### Windows（WSL2）

最終確認日: 未実施。この節は`CP-0078`で[ADR-0018](../adr/0018-per-os-container-runtime.md)の方針から書いたもので、実機で通していない。最初に使うときに手順を実行し、差分があればこの節を直したうえで確認日を記録する。

Docker Desktopは使わない。WSL2のdistribution内へDocker Engineを直接入れる（[ADR-0018](../adr/0018-per-os-container-runtime.md)）。

repositoryはWSL2のfilesystem内（`~/`配下）へcloneする。`/mnt/c`配下はdrvfs経由になり、bind mountの性能とfile modeが変わる。

Docker Engineをserviceとして起動するため、WSL2でsystemdを有効にする。`/etc/wsl.conf`へ次を書き、`wsl --shutdown`で再起動する。

```ini
[boot]
systemd=true
```

distributionのpackageからDocker Engineとcompose pluginを入れる。plugin pathはpackageが設定するため、macOSのような`cliPluginsExtraDirs`の追加は要らない。

```bash
sudo apt-get install docker.io docker-compose-v2   # Ubuntuの場合
sudo usermod -aG docker "$USER"                    # 再ログインで反映
```

VMの割り当てはWindows側の`%UserProfile%\.wslconfig`で指定する。Colimaの`--cpu`と`--memory`に相当する。

```ini
[wsl2]
memory=8GB
processors=4
```

WSL2内でloopbackへ公開したportは、Windows側の`localhost`からも到達できる。`127.0.0.1`へのbindを変える必要はない。

versionを確認する。

```bash
docker --version && docker compose version
```

## 設定

`.env`はGit管理外で、Composeが自動的に読む。値はこの開発機だけで使う。

```bash
cp .env.example .env
openssl rand -hex 32   # 3回実行し、.env の3つのpasswordへ貼る
```

`.env`はすべての`docker compose`コマンドで読まれる。値が欠けていると、起動だけでなく`docker compose ps`や`docker compose exec`も次のように失敗する。

```text
error while interpolating services.db.environment.POSTGRES_PASSWORD: required variable CARD_PULSE_POSTGRES_PASSWORD is missing a value: copy .env.example to .env first
```

`.env.example`に無い変数をcompose.yamlが読まないことは`tests/unit/test_local_environment.py`が検査する。

DBのrole作成は、data volumeが空の状態での初期化時にだけ実行される。`.env`のpasswordを後から変えた場合、既存volumeのroleは変わらない。変更を反映するには「[初期化](#初期化破壊的)」でvolumeごと作り直すか、`docker compose exec db psql`から`ALTER ROLE ... PASSWORD`を実行する。

## 起動

```bash
docker compose up --build -d
```

期待する結果:

```bash
docker compose ps
```

`db`、`api`、`worker`の3つが`running`で、`STATUS`列に`(healthy)`が付く。`db`が先にhealthyになり、その後`api`と`worker`が起動する。

APIの応答を確認する。

```bash
curl -s http://127.0.0.1:8000/health
```

```json
{"service": "api", "status": "ok"}
```

依存の状態を確認する。

```bash
curl -s http://127.0.0.1:8000/health/dependencies
```

`status`が`ok`で、`dependencies`に`database`が`healthy: true`で並ぶ。

Workerのログを確認する。

```bash
docker compose logs worker
```

`worker started:` に続けて`dependencies: database=ok, artifact-storage=ok`が周期的に出る。取込jobはまだ実装されていないため、Workerは依存を確認してheartbeatを書くだけで待機する（`CP-0024`で最初のsource adapterを追加する）。

runtime roleがsuperuserでないことを確認する。

```bash
docker compose exec db psql --username=postgres --dbname=card_pulse --command='\du card_pulse*'
```

`card_pulse_api`と`card_pulse_worker`が、属性列に何も持たない状態で表示される。

## 変更を反映する

application codeはimageの中に入る。bind mountしていないため、`src/`を変更したらbuildし直す。

```bash
docker compose up --build -d
```

依存を変えていなければ、再buildはprojectのinstall layerだけをやり直す。

APIとWorkerは`card-pulse-app:dev`という一つのimageを共有し、buildの宣言は`api` serviceだけが持つ。`worker`だけを単独で起動する場合は、先に`docker compose build`でimageを作る。作られていないとComposeがregistryからpullしようとして失敗する。

## DBの中身を見る

DBのデータはDockerのnamed volume `card-pulse_db-data`にあり、working treeにも`var/`にも現れない（[ADR-0023](../adr/0023-named-volume-for-database-data.md)）。file として開ける形ではないため、中身を見るときはDBとして接続する。

```bash
docker compose exec db psql --username=postgres --dbname=card_pulse
```

host側のpsqlやGUI client（DBeaver、pgAdmin等）からは、公開している`127.0.0.1:5432`へ接続する。`<api-password>`は`.env`の`CARD_PULSE_API_DB_PASSWORD`の値に読み替える。

```bash
psql 'postgresql://card_pulse_api:<api-password>@127.0.0.1:5432/card_pulse'
```

別の環境へ移す場合や、「[初期化](#初期化破壊的)」の前に残す場合は、`pg_dump`の出力を`var/db/`へ置く（[ADR-0022](../adr/0022-configuration-secret-and-local-data-storage.md)）。現時点ではschemaが無いため手順は未整備である。最小のdump・復元手順は`CP-0088`、暗号化と世代管理を含む運用としてのbackupは`CP-0044`が扱う。

## テスト

unit testと品質検査はhostで実行する。Compose環境は不要。

```bash
python3 scripts/check.py
```

DBを使うintegration testは、起動中のCompose環境へ接続する。`<api-password>`は`.env`の`CARD_PULSE_API_DB_PASSWORD`の値に読み替える。

```bash
CARD_PULSE_DATABASE_URL='postgresql://card_pulse_api:<api-password>@127.0.0.1:5432/card_pulse' \
    uv run --locked pytest tests/integration
```

この変数を設定しない場合、`tests/integration`はskipされる。CIにDB serviceが無い状態でも全検査が通るようにするためで、DBを使うCIの追加は`CP-0062`で行う。

## Migration

現時点ではschemaもmigrationも無い。空のDBが作られるだけである。Alembic環境は対象schemaが決まる`CP-0016`以降で追加し、追加後もAPIとWorkerの起動時に暗黙実行せず、専用roleと明示した手順で実行する（[ADR-0014](../adr/0014-postgresql-self-hosted.md)）。

## 障害分離を確認する

一つのserviceを止めても他が動き続けることを確認する。

```bash
docker compose stop db
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/health/dependencies
```

`/health`は`status: ok`のまま200を返し、`/health/dependencies`は`status: degraded`と`database`の失敗理由を返す。`docker compose ps`では`api`と`worker`が`healthy`のままになる。health checkはprocessが生きているかだけを表し、依存の状態は別に報告するためである（[ADR-0016](../adr/0016-local-compose-artifact-volume.md)）。

```bash
docker compose start db
```

30秒以内に`/health/dependencies`が`ok`へ戻る。`api`と`worker`は再起動していない。

`api`と`worker`も同じように個別に停止・起動できる。

## 停止

volumeとデータを残して止める。

```bash
docker compose stop      # containerを止める。次は docker compose start で再開する
docker compose down      # containerとnetworkを削除する。volumeは残る
```

`docker compose down`の後に`docker compose up -d`すると、同じDBと同じ原本のまま起動する。

## 原本を取り出す

artifact storageはDockerのnamed volumeで、working treeには現れない。hostへ取り出す場合は次を使う。

```bash
docker compose cp worker:/srv/card-pulse/artifacts ./var/raw
```

取り出した原本はGit管理外の`var/raw/`に置いたままにする。Git、CI artifact、公開backupへ含めない（[ADR-0012](../adr/0012-private-personal-operation.md)）。`var/`の層ごとの役割は[ADR-0022](../adr/0022-configuration-secret-and-local-data-storage.md)を正とする。

## 初期化（破壊的）

DBの全データと保存済み原本を削除して作り直す。

削除されるもの: `card-pulse_db-data` volume（DB全体）と`card-pulse_artifacts` volume（取得原本すべて）。現時点ではbackup手順が未整備のため（`CP-0088`、`CP-0044`、`backup-restore` Runbook）、削除したデータは復旧できない。

実行前に対象を確認する。

```bash
docker volume ls --filter label=com.docker.compose.project=card-pulse
```

残したい原本がある場合は、先に「[原本を取り出す](#原本を取り出す)」でhostへ複製する。

```bash
docker compose down --volumes
docker compose up --build -d
```

再起動時に`.env`の値でDBとroleが作り直される。

## よくある失敗

| 症状 | 原因 | 対処 |
| --- | --- | --- |
| `copy .env.example to .env first` で起動しない | `.env`が無い、または必須の値が空 | 「[設定](#設定)」を実行する |
| `db`がhealthyにならない | host port 5432が他のPostgreSQLと衝突 | `.env`の`CARD_PULSE_DB_PORT`を変える |
| `api`が起動直後に終了する | `CARD_PULSE_DATABASE_URL`が不正。ログに変数名が出る | `.env`のpasswordにURLで意味を持つ文字が入っていないか確認する。`openssl rand -hex`の出力を使う |
| `/health/dependencies`が`password authentication failed`を返す | `.env`のpasswordを変更したが、既存volumeのroleは初期化時のまま | roleを`ALTER ROLE`で更新するか、「[初期化](#初期化破壊的)」を行う |
| buildが`required-version`で失敗する | Dockerfileが固定するuvのimage tagと`pyproject.toml`の`required-version`が食い違っている | どちらかを揃える。versionの正は`pyproject.toml` |
| `docker`コマンドがdaemonへ接続できない | macOSはColimaのVMが停止している。WSL2はdockerdが起動していない | `colima start`、またはWSL2で`sudo systemctl start docker` |
| `docker compose` が unknown command になる | macOSでplugin pathが未登録 | 「[macOS](#macos)」の`cliPluginsExtraDirs`を設定する |
| `db`はhealthyだがAPIが`password authentication failed`を返す | repositoryがmountされない場所にあり、初期化scriptが実行されなかった | 「[共通](#共通)」の置き場所を満たしてから「[初期化](#初期化破壊的)」を行う |
