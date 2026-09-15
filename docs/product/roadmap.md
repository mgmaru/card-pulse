# Card Pulse ロードマップ

> 状態: Active
>
> 最終更新: 2026-09-15
>
> Next task ID: `CP-0091`

この文書は検証と開発の順序を示す。MVPの範囲と完了条件は [MVP定義](mvp.md) を正とする。日々の細かな作業管理を始めた後は、実行タスクをIssue等へ移し、この文書にはフェーズと判断条件を残す。

各タスクはリポジトリ全体で一意なIDと状態を持つ。移動や分割、割り込み時の更新方法は [Roadmap task format](../../.agents/skills/maintain-roadmap/references/task-format.md) に従う。

`owner` が付いたタスクは、リポジトリの外でプロジェクトオーナー本人が操作しないと完了しない。何をするかは `Owner action` に書く。未完了のものだけを一覧するには次を実行する。

```bash
python3 .agents/skills/maintain-roadmap/scripts/validate_roadmap.py --owner
```

## Phase 0 — 対象と情報源を決める

- [x] `CP-0001` `done` — 候補となるTCGと店舗を [情報源マップ](../sources/source-map.md) に記録する。
  - Evidence: ポケモンカードゲームと6情報源を[候補一覧](../sources/source-map.md#候補一覧)へ記録し、各個別source文書へリンクした。
- [x] `CP-0002` `done` — URL、形式、更新頻度、カード番号、状態条件、自動取得難易度を確認する。
  - Evidence: [遊々亭](../sources/yuyutei.md#データ形式)、[カードラッシュ](../sources/cardrush.md#データ形式)、[晴れる屋2](../sources/hareruya2.md#データ形式)、[ドラゴンスター](../sources/dragonstar.md#データ形式)、[トレトク](../sources/toretoku.md#データ形式)、[フルコンプ](../sources/fullcomp.md#データ形式)の個別文書に、公開形式、識別項目、価格条件、更新頻度、取得難易度と未確認事項を記録した。
- [x] `CP-0003` `done` — robots.txt、利用規約、アクセス制限、再利用条件、取得間隔を確認し、確認日と根拠URLを記録する。
  - Evidence: 6情報源の[初期比較](../sources/source-map.md#初期比較)と各個別文書の「取得と利用上の制約」に、2026-09-09時点のrobots.txt、規約、自動取得、保存・fixture、取得間隔、根拠URLを記録した。
- [x] `CP-0004` `done` — 代表サンプルを少量だけ確認し、カード識別子と価格条件を抽出できるか比較する。
  - Done when: 各値を原本から直接抽出する値、source metadataまたは取込設定から得る値、欠損可能な値、同定に必要な値へ分類し、同じカードの候補数と価格条件の比較可否を情報源間で記録している。
  - Evidence: 6情報源の値分類、候補衝突、価格条件を[代表サンプル比較](../sources/source-map.md#代表サンプル比較)へ記録し、3情報源で同じカードが各1候補になることと価格条件の差を[同一カード比較](../sources/source-map.md#同一カードの情報源間比較)で確認した。
- [x] `CP-0005` `done` — `1 TCG × 2〜3店舗` を選び、選定理由と見送った候補をADRに残す。
  - Depends on: `CP-0004`
  - Evidence: [ADR-0010](../adr/0010-pokemon-mvp-source-candidates.md)でポケモンカードゲーム、晴れる屋2、遊々亭、フルコンプ池袋店をMVP候補とし、[ADR-0009](../adr/0009-pokemon-mvp-sources.md)を置換した。
- [x] `CP-0070` `cancelled` — 晴れる屋2、遊々亭、フルコンプ池袋店の書面条件と比較可能性を検証する。
  - Depends on: `CP-0005`
  - Done when: 3候補の対象URL、User-Agent、取得頻度、raw artifactと抽出履歴の保持、sanitized fixture、Card Diggerへの派生集計提供、停止・削除条件について、書面回答または回答期限までの経緯がsource文書に記録され、フルコンプ池袋店の代表カードを既存候補と照合して価格条件を比較している。
  - Cancellation reason: [ADR-0011](../adr/0011-no-external-source-inquiries.md)で外部照会を行わない方針へ変更した。公開条件の再確認とフルコンプ池袋店の情報源横断比較はsource文書へ残した。
- [x] `CP-0071` `done` — 3候補の公開条件では採用できない結果を受け、ドラゴンスターの取得安定性と許諾主体を検証し、候補へ加えるか判断する。
  - Done when: robots.txtとCloudflareの挙動、一覧・詳細取得の安定性、価格データの許諾主体、書面確認の窓口、既存候補との同定可能性を確認し、採用、保留、見送りの判断と根拠をsource文書および必要なADRへ記録している。
  - Evidence: [ドラゴンスターの検証](../sources/dragonstar.md#cp-0071の検証)で両hostのrobots.txt、一覧、詳細がCloudflare challengeになること、許諾主体が確定しないこと、既存候補と属性照合できることを記録し、[ADR-0011](../adr/0011-no-external-source-inquiries.md)でMVP候補として見送った。
- [x] `CP-0072` `cancelled` — `CP-0070`と、必要な場合は`CP-0071`の結果から、MVP採用する2〜3店舗を確定する。
  - Depends on: `CP-0070`
  - Done when: 自動取得、保存、fixture、派生集計提供の必要条件を満たす2〜3店舗がMVP採用としてsource文書に記録され、候補構成を変更する場合は新しいADRで決定している。
  - Cancellation reason: 外部照会を行わず、当時の公開条件だけでは必要条件を満たさないため、このタスクの基準では採用しなかった。`CP-0074`で個人・非公開の取得経路へ変更した。
- [x] `CP-0073` `cancelled` — 外部照会を行わずにMVPを検証できる取得経路を決定する。
  - Depends on: `CP-0071`
  - Done when: 必要な利用条件が公開されている情報源と、利用者が権利を持つ手動ファイルまたはsource非由来の合成データを比較し、採用する入力経路、検証できるMVP仮説、原本・fixtureの保存規則をMVP定義とADRへ記録している。
  - Cancellation reason: 公開条件による個別許諾の確認を開発の前提にせず、本人だけが使う非公開Web Collectorへ進む方針に変更した。置換タスクは`CP-0074`。
- [x] `CP-0074` `done` — Card Pulseを個人用の非公開アプリとし、ローカルWeb Collectorの取得経路を確定する。
  - Depends on: `CP-0071`
  - Done when: 単一利用者、非公開runtime、採用情報源と実装順、取得上限、アクセス拒否時の停止、raw artifactとfixtureの保存・非共有境界をMVP定義とADRへ記録している。
  - Evidence: [ADR-0012](../adr/0012-private-personal-operation.md)で個人・非公開のローカル運用、晴れる屋2・遊々亭・フルコンプ池袋店の実装順、取得上限、停止条件、raw artifactとfixtureの保存境界を決定し、[MVP定義](mvp.md)の仮説と完了条件へ反映した。
- [x] `CP-0064` `done` — 次のADR作成時にADR管理の機械検査を導入するか判断する。
  - Done when: ADR ID、状態、日付、必須section、一覧、置換関係を検査するvalidatorを既存の`write-project-docs`とCIへ統合するか、見送る理由を記録する。
  - Evidence: [ADR管理の機械検査](../adr/README.md#adr管理の機械検査)に、現時点で専用validatorを導入しない理由と再検討条件を記録した。
- [x] `CP-0067` `done` — カードの内部主キーと外部識別子の役割を決定する。
  - Evidence: [ADR-0008](../adr/0008-opaque-card-identity-id.md)で、意味を持たない内部UUID、属性による照合、namespace付き外部参照、誤同定の追記型訂正を決定し、データモデルとCollector契約へ反映した。

完了条件: 対象、情報源、取得間隔、利用上の制約が決まり、後続作業が未調査事項で停止しない。

## Phase 1 — 最小の開発基盤を作る

- [x] `CP-0006` `done` — Python version、パッケージ管理、migration手段の決定をADRに残す。
  - Evidence: [ADR-0013](../adr/0013-python-toolchain-and-migrations.md)でCPython 3.14、uvによるproject・lock管理、AlembicによるmigrationとDB選定後に検証する事項を決定した。
- [x] `CP-0007` `done` — 想定データ量、同時接続、整合性、backup・復旧、運用、費用からDB要件を定義する。
  - Evidence: [DB要件](../architecture/database-requirements.md)に、初期・10倍負荷、queryと整合性の合格基準、RPO・RTO、backup世代、権限、保守時間、費用上限、PoC条件、実測後の再評価条件を定義した。
- [x] `CP-0008` `done` — 複数のDB候補を [DB選定の判断軸](../learning/database-selection.md) で比較する。
  - Evidence: [DB候補比較](../research/database-candidate-comparison-2026-09.md#結論)でPostgreSQL、MariaDB、MongoDB、SQLiteを必須条件と8つの判断軸で比較し、PostgreSQL 18.6とMariaDB 12.3.3を`CP-0009`のPoC対象に絞った。BaaSとmanaged hostingはengine選定と別軸として[hosting方式とBaaSの検討](../research/database-candidate-comparison-2026-09.md#hosting方式とbaasの検討)へ記録し、MVPはself-host構成を前提とした。
- [x] `CP-0009` `done` — 上位候補で取込、同時照会、集計、migration、backup・復元のPoCを行う。
  - Evidence: [CP-0009 DB PoC結果](../research/database-poc-2026-09.md#結論)に、PostgreSQL 18.6とMariaDB 12.3.3を1倍（約540万行）と10倍（約4,430万行）で測定した結果を記録した。両候補がPoC合格条件10項目を満たし、追記型保存の権限強制、失敗migrationの部分適用、論理復元時間に差が出た。測定harnessは[`scripts/db_poc/`](../../scripts/db_poc/README.md)にある。
- [x] `CP-0010` `done` — DB製品をADRで決定し、ADR-0004の未決事項を解消する。
  - Evidence: [ADR-0014](../adr/0014-postgresql-self-hosted.md)で、`CP-0009`の実測を根拠にself-hostのPostgreSQL 18を採用し、[ADR-0004](../adr/0004-server-database-selection.md)が残したDB製品とhosting providerの未決事項を解消した。決定を[MVP定義](mvp.md)、[プロダクト構想](vision.md)、[アーキテクチャ概要](../architecture/overview.md)、[DB要件](../architecture/database-requirements.md)、`README.md`へ反映した。
- [x] `CP-0011` `done` — `pyproject.toml`、lockfile、パッケージの最小構成を作る。
  - Evidence: [ADR-0013](../adr/0013-python-toolchain-and-migrations.md)に従い、`pyproject.toml`へ`requires-python = ">=3.14,<3.15"`とuvの`required-version`を、`.python-version`へCPython 3.14.7を固定した。`src/card_pulse/`をsrc layoutの単一installable packageとし、[アーキテクチャ概要](../architecture/overview.md#コード構成)の責務境界に対応する12 packageを作成した。生成した`uv.lock`で`uv sync --locked`、全subpackageのimport、wheel buildが成功することを確認した。runtime依存は空とし、開発依存と品質検査コマンドは`CP-0013`、Alembic環境は対象schemaが決まる時点へ残した。
- [x] `CP-0012` `done` — Docker ComposeでAPI、Worker、選定DB、artifact storageを起動するローカル環境を作る。
  - Depends on: `CP-0077`
  - Evidence: [ADR-0016](../adr/0016-local-compose-artifact-volume.md)でartifact storageをDocker volume上のfilesystemとし、APIとWorkerが共有する単一image、loopbackだけへ公開するport、livenessだけを表すhealth checkを決めた。`compose.yaml`は`db`（`postgres:18.6-trixie`をdigest固定）、`api`、`worker`と`db-data`・`artifacts` volumeを定義し、`Dockerfile`はuv image上でCPython 3.14.7とproject依存を固定して非root uid 10001で実行する。手順は[ローカル開発環境Runbook](../runbooks/local-development.md)を正とする。Colima 0.10.3・Docker 29.8.0・Docker Compose 5.5.1で、build、3 serviceのhealthy化、`/health`と`/health/dependencies`の応答、runtime roleが非superuserで作られること、public tableが0件の空DB、host側からの`tests/integration`成功（2件）、`docker compose stop db`中もAPIが200で`degraded`を返しapi・workerがhealthyのまま再起動しないこと、`docker compose start db`後の復帰、artifact volumeがworkerにだけmountされ`docker compose cp`で取り出せること、`down`でデータが残り`down --volumes`で消えて再初期化されることを確認した。構成の不変条件は`tests/unit/test_local_environment.py`が検査し、CIでの起動検査は`CP-0061`で行う。
- [x] `CP-0013` `done` — setup、test、lint、format、型チェックの再現可能なコマンドを定義する。
  - Evidence: [ADR-0015](../adr/0015-quality-check-toolchain.md)でruff 0.16.7、mypy 2.3.1、pytest 9.1.1を採用し、`pyproject.toml`の`[dependency-groups]`と各tool設定へ反映して`uv.lock`を更新した。setupは`uv sync --locked`、全検査は`python3 scripts/check.py`とし、各段階を`uv run --locked`経由で実行する。`.venv`を削除した状態から`uv sync --locked`を実行し、format、lint、型チェック、testの4段階が成功すること、型不整合を含むfileを置くと3段階が失敗して終了codeが1になること、`uv.lock`と`pyproject.toml`が食い違うと`--locked`が検査前に失敗することを確認した。コマンドは[開発環境と品質検査](../../CONTRIBUTING.md#開発環境と品質検査)を正とし、CIへの追加は`CP-0060`で行う。
- [x] `CP-0078` `done` — Docker環境をWSL2でも同じ手順で起動できるようにする。
  - Depends on: `CP-0012`
  - Done when: 改行コードによる初期化の失敗を機械検査で防ぎ、runtimeの選定基準がOSに依存しない形でADRに残り、Runbookの前提条件がOS別に分かれて共通部分が一つに保たれている。
  - Evidence: `CP-0012`の成果物をfile単位で確認した。固定した3つのimage digestが`linux/amd64`と`linux/arm64`を含むindex manifestであること、builder段の`uv sync --locked`をamd64のエミュレーションで実行してCPython 3.14.7とpsycopg 3.3.5のbinary wheelが入ること、runtime段のuser作成がamd64でも同じ結果になること、`compose.yaml`のhost依存がbind mount一つとloopback公開二つだけであることを確認した。壊れたのは改行コードだけで、CRLFの初期化scriptを実際のPostgreSQLへ渡すと`set: pipefail: invalid option name`で初期化が中断しcontainerが終了した。dotenv fileのCRLFはComposeが吸収した。対処として`.gitattributes`で全text fileをLFに固定し、bind mount対象にCRが無いことを`tests/unit/test_local_environment.py`が検査する（CRを入れると実際に失敗することを確認）。[ADR-0018](../adr/0018-per-os-container-runtime.md)で[ADR-0017](../adr/0017-colima-container-runtime.md)を置換し、判断をruntimeの固有名詞から「無償条件が利用者や所属組織の区分に依存しないこと」という選定基準へ移して、macOSはColima、WindowsはWSL2内のdocker-ceとした。[ローカル開発環境Runbook](../runbooks/local-development.md)の前提を共通・macOS・WSL2へ分け、repositoryをcontainer runtimeがmountできる領域へ置く条件を共通側へ追加した。WSL2の手順は実機未確認で、最終確認日をOSごとに記録する形にした。WSL2はLinux amd64上のDocker Engineであり`CP-0061`のCI jobが継続的な互換性検証を兼ねる。
- [ ] `CP-0079` `planned` — 新しいマシンで開発環境を再現する手順を定義する。
  - Depends on: `CP-0078`
  - Done when: repositoryのcheckoutから開発と取込を始められる状態までの前提と手順が一つのsource of truthに定まり、前提の充足を機械的に確認できるか、確認を自動化しない理由が記録されている。Docker環境に限らず、git設定、Python toolchain、`.env`、エージェント設定を対象に含める。
- [ ] `CP-0081` `blocked` `owner` — WSL2の実機でローカル開発環境Runbookを通し、最終確認日を記録する。
  - Owner action: WSL2 を使える Windows 環境を用意し、Runbook の手順を実行する。
  - Depends on: `CP-0078`
  - Blocker: WSL2を使えるWindows環境が手元に無い。
  - Resume when: WSL2を使えるWindows環境が利用できるようになる。
  - Done when: [ローカル開発環境Runbook](../runbooks/local-development.md)のWSL2の前提と共通手順を実機で実行し、差分があればRunbookを修正したうえで、WSL2の最終確認日を記録している。
- [x] `CP-0014` `done` — 設定、秘密情報、取得原本、開発用volumeの保存規則を整える。
  - Done when: 設定値の入口、秘密情報の置き場、取得原本とローカルデータの層、削除してよい条件が一つのADRに定まり、規則を破る変更をCIが検出する。
  - Evidence: [ADR-0022](../adr/0022-configuration-secret-and-local-data-storage.md)で、設定を「環境ごとに変わる値」と「動作そのものを決める値」へ分け、前者を環境変数で渡して`settings.py`を唯一の読み取り口とし（`.env`はComposeと人がそれを環境変数へ変換するfileで、container内には無い）、後者を`config/`のfileとした。読み取り口を一つにするのは、health checkとそれが検査するprocessが別processでありながら同じportとpathへ合意する必要があるためで、この合意を規約ではなく同じ関数の呼び出しで保証する。秘密情報は`.env`ひとつに限り、ローカルデータを`var/`の5層へ集約した。書き込むcomponentがまだ無い`var/db/`と`var/review/`も残し、`CP-0044`とPhase 4のreviewが最初の利用者であることを明記した。`CP-0009`のPoCが残した`var/db-poc/`は2026-09-13時点で35GBあり、`secret/backup.passphrase`が`.env`の外にある唯一の秘密である。測定結果が[PoC結果](../research/database-poc-2026-09.md)に、harnessが`scripts/db_poc/`に凍結されているため削除しても結論は追跡できるが、同じ入力での再確認手段が消えるため保持し、削除してよい3つの条件をADRへ書いた。`tests/unit/test_storage_layout.py`が、`var/`と`config/`に`.gitkeep`以外の追跡fileが無いこと、`.env`と`var/`配下のデータが除外され`.env.example`だけが追跡されること、`var/`の4層が存在すること、runtimeの既定書き込み先が`var/`配下であることを検査する。`var/raw/page.html`を`git add -f`した場合、`var/db/`を移動した場合、`DEFAULT_ARTIFACT_ROOT`を`var/`の外へ変えた場合のそれぞれで対応する検査が失敗することを確認した。参照は[実装上の原則](../../CONTRIBUTING.md#実装上の原則)、[アーキテクチャ概要](../architecture/overview.md#raw-artifact-storage)、[ローカル開発環境Runbook](../runbooks/local-development.md#原本を取り出す)、[README](../../README.md)、`settings.py`のdocstringから同じADRへ向けた。
- [x] `CP-0087` `done` — DBのdata directoryをhostへbind mountするか決める。
  - Depends on: `CP-0014`
  - Done when: 開発と本番でvolumeの方式を分けるかどうかが判断され、理由と再検討条件がADRに残り、compose定義がその判断どおりであることを機械検査が保つ。
  - Evidence: [ADR-0023](../adr/0023-named-volume-for-database-data.md)で、DBのdata directoryを開発機でも将来の配置でもnamed volume `db-data`とし、`var/db/`を含むhost pathへのbind mountを採らないと決めた。判断の材料は、PostgreSQLのfile system level backupがserver停止を要しcluster全体でしか成立しないこと、major versionを跨げないこと、公式imageのPGDATAがversion固有pathで所有者の一致を要すること（いずれも確認日2026-09-14、URLはADRに記載）、およびhostからDBを読む経路が公開済みの`127.0.0.1:5432`にすでにあることである。開発だけbind mountする案は、PGDATAがhostから読めるfileではないため利点が実現せず、`CP-0061`の`Compose environment` jobが検証する構成と日常的に動かす構成が永続化層で食い違うため採らなかった。持ち出しと移植は`pg_dump`の出力を`var/db/`へ置く形とし（[ADR-0022](../adr/0022-configuration-secret-and-local-data-storage.md)）、手順は`CP-0044`が扱う。`tests/unit/test_local_environment.py`が、host pathのbind mountが読み取り専用の初期化scriptだけであることを検査し、書き込み可能なbind mountを`compose.yaml`へ足すと失敗することを確認した。[ローカル開発環境Runbook](../runbooks/local-development.md#dbの中身を見る)へ、データの所在と接続方法を追加した。
- [ ] `CP-0015` `planned` — `run_id`、source、開始・終了時刻、取得件数、保存件数、エラー分類を記録するログを定義する。
- [x] `CP-0059` `done` — GitHub Actionsで文書リンクとroadmap形式を継続的に検査する。
  - Evidence: `.github/workflows/ci.yml`でpull requestと`main`へのpushを対象に両方の検査を実行する。
- [x] `CP-0060` `done` — format、lint、型チェック、unit testをGitHub Actionsへ追加する。
  - Depends on: `CP-0013`
  - Done when: 対応するPython versionとlockfileを使い、ローカルと同じ品質検査がpull requestで成功する。
  - Evidence: `.github/workflows/ci.yml`の`Quality checks` jobが`python3 scripts/check.py`を実行し、検査内容をworkflowへ複製しない。uvのversionは`pyproject.toml`の`required-version`、CPythonのversionは`.python-version`からuv自身が解決する。pull request #4の実行logでuv 0.12.13とCPython 3.14.7が使われ、format、lint、型チェック、testの4段階と13件のtestが10秒で成功したことを確認した。`main`のrulesetの必須status checkへ`Quality checks`を追加し、[保護設定](../../CONTRIBUTING.md#main-の保護設定)へ反映した。
- [x] `CP-0077` `done` — ローカル開発で使うcontainer runtimeを選定し、ADRに残す。
  - Done when: ライセンス条件、CI runnerとの差、導入方法を比較したうえで採用するruntimeが決まり、repositoryの成果物がruntime固有の機能へ依存しない範囲と再選定の条件がADRに記録されている。Runbookの前提条件への反映は`CP-0012`で行う。
  - Evidence: [ADR-0017](../adr/0017-colima-container-runtime.md)でColima、Docker Desktop、Rancher Desktop、OrbStackを2026-09-13時点のライセンス条件、入手方法、GUIの要否で比較し、Colimaを採用した。4候補ともLinux VM上の同じDocker Engineで技術差が出ないため、ADR-0012が判断を避けた個人利用・商用の区分へ依存しないMITのColimaを選んだ。`compose.yaml`をCompose Specificationの範囲に限る、imageをmulti-archのdigestで固定する、手順を`docker compose`で表す、CIはrunnerのDocker Engineを使うという4点で、repositoryの成果物をruntimeへ依存させない範囲を定めた。Homebrewからcolima 0.10.3、docker 29.8.0、docker-compose 5.5.1、lima 2.2.0を導入し、`~/.docker/config.json`の`cliPluginsExtraDirs`を設定して`docker compose version`が5.5.1を返すことを確認した。
- [x] `CP-0061` `done` — Docker Composeの設定、image build、service health checkをGitHub Actionsへ追加する。
  - Depends on: `CP-0012`
  - Done when: 空のGitHub-hosted runnerでCompose環境をbuild・起動し、各serviceのhealth checkが成功する。同jobを`main`のrulesetの必須status checkへ追加し、[保護設定](../../CONTRIBUTING.md#main-の保護設定)へ反映している。
  - Evidence: `.github/workflows/ci.yml`の`Compose environment` jobが、ubuntu-24.04のrunnerで`.env.example`のpassword行をその実行限りの値で埋めた`.env`を作り、`docker compose up --build --wait`でimage buildと起動を行う。`--wait`が3 serviceのhealth checkの成功を待ち、一つでも失敗すればjobが失敗する。変数名をworkflowへ書き写さず`.env.example`から`.env`を作るため、必要な変数が増えてもjob側の変更は要らない。health checkはliveness（[ADR-0016](../adr/0016-local-compose-artifact-volume.md)）だけを表し、runtime roleが作られない、artifact volumeへ書けないといった壊れ方ではprocessが落ちずhealthyのまま通ってしまうため、APIの`/health/dependencies`とWorkerのheartbeatが`status: ok`であることも検査する。Colima（macOS、arm64）で`docker compose stop db`を実行した状態を作り、`api`と`worker`がhealthyのままこの2つの検査だけがexit 1になること、正常時は両方が`ok`を返すことを確認した。必須status checkへの追加は[`.github/rulesets/main-protection.json`](../../.github/rulesets/main-protection.json)の差分として行い（[ADR-0021](../adr/0021-ruleset-as-a-file.md)）、`python3 scripts/ruleset.py apply`で適用した。[保護設定](../../CONTRIBUTING.md#main-の保護設定)は各規則が防ぐことだけを書き値を複製しないため表の変更は不要で、[ローカル実行環境](../../CONTRIBUTING.md#ローカル実行環境)へCIが同じ手順を実行することを追記した。pull request #14の実行logで、空のubuntu-24.04 runnerがimageをbuildし、db・api・workerがhealthyになり、両方の依存検査が`ok`を返すまでを26秒で終えたことを確認した。
- [x] `CP-0069` `done` — CodexとClaude Codeの両方で同じエージェント設定が有効になるようにし、乖離をCIで検査する。
  - Depends on: `CP-0059`
  - Evidence: エージェント定義を`.agents/agents/`の中立形式に一本化し、[`maintain-tool-parity`](../../.agents/skills/maintain-tool-parity/SKILL.md)が`.codex/agents/`と`.claude/agents/`を生成する。同Skillの検査スクリプトが生成物の一致、共有Skillのsymlink、`CLAUDE.md`の`@AGENTS.md`取り込みを検証し、CIの`Agent configuration` jobで実行する。
- [x] `CP-0065` `done` — ブランチ・PR運用を定義し、作業開始Skillと`main`の保護設定を整える。
  - Depends on: `CP-0059`
  - Done when: [CONTRIBUTING.md](../../CONTRIBUTING.md)をsource of truthとしてSkillが作業ブランチを作成でき、`main`へのマージにpull requestとCI成功が必要になり、ブランチ名CIの導入判断が記録されている。
  - Evidence: [ブランチとpull request](../../CONTRIBUTING.md#ブランチとpull-request)へ、`cp-<タスクID>-<要約>`の命名、マージコミットのみ許可する理由、rebase後にマージする規則、マージ後もブランチを残す判断、保護設定の一覧、ブランチ名の機械検査を見送る理由と再検討条件を記録した。[`start-task`](../../.agents/skills/start-task/SKILL.md) Skillが分岐からpull request、マージまでの手順を実行する。`main`のrulesetでpull requestとCI成功を必須にし、squash mergeとrebase mergeを無効化した。必須status checkは現存する`Documentation`と`Agent configuration`から開始し、`CP-0060`と`CP-0061`で追加する。

- [x] `CP-0076` `done` — ADRに判断理由を明示し、決め手となる一文を強調する書き方を定める。
  - Evidence: [判断理由の書き方](../adr/README.md#判断理由の書き方)を規則の正とし、`Decision`で理由の中心となる一文を太字にすること、強調を一つに絞ること、理由を比較・制約・回避したい失敗として書くことを定めた。[ADR template](../adr/template.md)、[`write-project-docs`](../../.agents/skills/write-project-docs/SKILL.md)、`AGENTS.md`、[CONTRIBUTING.md](../../CONTRIBUTING.md#文書の扱い)から同じ規則を参照する。既存ADRは[ADR README](../adr/README.md#状態)の規則どおり書き換えず、[ADR-0015](../adr/0015-quality-check-toolchain.md)の`Decision`を手本として示した。

- [x] `CP-0082` `done` — オーナー本人が操作するタスクをロードマップ上で識別できるようにする。
  - Evidence: task行の状態の後ろへ任意の`owner`markerを置き、`Owner action`metadataでリポジトリの外で何をするかを書く形式にした。`blocked`が`Blocker`と`Resume when`を必須にするのと同じ関係で、`owner`は`Owner action`を必須とし、markerの無い`Owner action`も検査で弾く。`validate_roadmap.py --owner`が未完了のownerタスクを一覧する。markerだけの行、markerの無い`Owner action`、両方揃った行の3通りを検査にかけ、前2つが失敗し3つ目が通ることを確認した。判定基準は「リポジトリの外でオーナー本人が操作しないと完了しない」こととし、`CP-0061`、`CP-0080`、`CP-0081`、`CP-0038`、`CP-0040`、`CP-0042`の6件へ付けた。完了済みタスクへ遡って付けない方針を[Roadmap task format](../../.agents/skills/maintain-roadmap/references/task-format.md)へ記載した。

- [x] `CP-0080` `done` — repositoryの公開範囲を[ADR-0012](../adr/0012-private-personal-operation.md)と整合させる。
  - Evidence: 棚卸しの結果、repositoryは2026-09-04の作成時からpublicで、ソースコードに加えて`docs/sources/`の12行と[ADR-0009](../adr/0009-pokemon-mvp-sources.md)の1行に実店舗名・カード・買取価格・source内IDを含む代表サンプルが公開されていた。取得原本、source由来fixture、価格履歴はgit履歴を全走査しても追跡されておらず、fork・star・watcherはいずれも0件、releaseとPagesも無かった。`docs/sources/`の追加が2026-09-09〜09-11、ADR-0012が09-12で、規則が後から入ったことによる食い違いだった。[ADR-0019](../adr/0019-private-repository.md)でrepositoryをprivateにする判断を記録し、2026-09-13に切り替えた。代表サンプルは第三者提供に当たらなくなるため削除せず、取得原本・抽出履歴・価格履歴とは区別する線引きを同ADRへ書いた。CIの`Documentation` jobへ`github.event.repository.private`を検査するstepを追加し、publicへ戻した状態のpull requestとpushが失敗するようにした。必須status checkに指定済みのjobへ置いたのは、新しいjobだと必須指定を追加するまで失敗を無視してマージできるためである。なおprivate化の直後に、GitHub Freeではprivate repositoryのprotected branchesが使えず`CP-0065`の保護設定が失効することが判明し、`CP-0083`で[ADR-0020](../adr/0020-public-repository-for-branch-protection.md)へ置き換えてpublicへ戻した。棚卸しの結果と[ADR-0012](../adr/0012-private-personal-operation.md)との不整合の内容は有効で、解消は`CP-0084`が引き継ぐ。
  - Done when: 現在公開されている成果物の棚卸しと、[ADR-0012](../adr/0012-private-personal-operation.md)のどの記述が影響を受けるかが整理され、ソースコードの公開を許容するかrepositoryをprivateにするかが新しいADRで決まっている。許容する場合は、公開するものと公開しないものの境界を同じADRへ記載する。
- [x] `CP-0083` `done` — `main`の保護設定を回復するため、repositoryの公開設定を見直す。
  - Depends on: `CP-0080`
  - Evidence: private化の直後にrulesetとbranch protectionのAPIが403を返し、GitHub Freeではprivate repositoryのprotected branchesが使えないことが分かった。`CP-0065`のpull request必須、status check必須、最新`main`必須が失効していた。[ADR-0020](../adr/0020-public-repository-for-branch-protection.md)で[ADR-0019](../adr/0019-private-repository.md)を置換してpublicへ戻し、CIのvisibility検査を削除した。public化後に`main protection`がenforcement `active`のまま戻ることを確認し、rulesetは削除されず無効化されていただけだったため再作成は不要だった。`bypass_actors`は空、必須status checkは`Documentation`、`Agent configuration`、`Quality checks`の3つ、merge方法はmerge commitのみで、[保護設定](../../CONTRIBUTING.md#main-の保護設定)の表と一致した。[ADR-0012](../adr/0012-private-personal-operation.md)との不整合は未解決のまま残し、`CP-0084`が引き継ぐ。
- [ ] `CP-0084` `planned` `owner` — [ADR-0012](../adr/0012-private-personal-operation.md)が定める非公開の範囲と、publicなrepositoryの不整合を解消する。
  - Depends on: `CP-0083`
  - Owner action: 公開してよい対象の範囲を判断する。
  - Done when: 公開してよいものと公開しないものの境界、`docs/sources/`と[ADR-0009](../adr/0009-pokemon-mvp-sources.md)に残る代表サンプルの扱い、LICENSEの有無が決まり、[ADR-0012](../adr/0012-private-personal-operation.md)との関係を明示した新しいADRに記録されている。
- [x] `CP-0085` `done` — `main`のrulesetをrepositoryから可視化し、実設定との乖離を検出できるようにする。
  - Depends on: `CP-0083`
  - Done when: rulesetのexportがrepositoryの正として置かれ、[保護設定](../../CONTRIBUTING.md#main-の保護設定)の記述がそれと一致している。実設定との乖離をCIが検出し、CIから読めない`bypass_actors`の扱いが決まっている。fileからGitHubへ適用する手動操作があり、CIから自動適用しない理由がADRに記録されている。2026-09-13時点で表に無い`deletion`、`non_fast_forward`、`require_extra_approval_for_unattributed_changes`の3規則も解消に含める。
  - Evidence: [ADR-0021](../adr/0021-ruleset-as-a-file.md)で`.github/rulesets/main-protection.json`を正とし、GitHub側をそこから派生させる形を決めた。決め手は、規則の変更をfile側から始めればpull requestの差分として必ず現れることで、UIからの直接変更はrepositoryに痕跡を残さない。`scripts/ruleset.py`が`check`、`apply`、`export`を持ち、CIの`Repository ruleset` jobは`check`だけを実行する。適用をCIから行えると`main`を守る規則が`main`経由で緩められるため、`apply`は人が実行する操作に限った。public repositoryのrulesetは未認証で読めることを`cli/cli`など3件で確認済みで、CIに追加のcredentialを置かない。`bypass_actors`は書き込み権限のある読み手にしか返らないためfileへ置かず、`apply`が常に空を送ることで迂回できる主体が生じない形にした。規則を1つ落とした場合と`strict_required_status_checks_policy`を変えた場合の両方で検査が失敗することを確認した。CI job自身を必須status checkへ追加する変更もfileの差分として行い、適用後に4つの必須checkが揃うことを確認した。表に無かった`deletion`、`non_fast_forward`、`require_extra_approval_for_unattributed_changes`は、[保護設定](../../CONTRIBUTING.md#main-の保護設定)を値の複製から各規則が防ぐことの説明へ書き換えて解消した。

- [ ] `CP-0086` `planned` — ADR管理の機械検査を導入するか再判断する。
  - Done when: [ADR管理の機械検査](../adr/README.md#adr管理の機械検査)が定めた再検討条件（ADR 20件）に達した時点の判断が記録され、validatorを追加するか、見送る理由と次の再検討条件が同じ節へ更新されている。

完了条件: DB選定の根拠がADRに残り、新しい環境で文書どおりにDocker環境を起動し、空DB作成とテスト実行ができる。

## Phase 2 — データ契約と永続化を作る

- [ ] `CP-0068` `planned` — 確定済みの価格観測とカード同定について、再審査、隔離、無効化、置換、復帰の条件と状態遷移を定義する。
  - Depends on: `CP-0004`
  - Done when: 再審査の契機と確定判断、理由・根拠・実行者・規則version、集計対象可否、置換先を追跡する方法が定まり、誤価格、誤同定、parser不具合、重複、復帰の各ケースをtest可能な形でデータモデルまたは契約文書に記録している。
- [ ] `CP-0016` `planned` — [データモデル](../architecture/data-model.md) を実データに合わせて確定する。
  - Depends on: `CP-0068`
- [ ] `CP-0017` `planned` — [Collector契約](../contracts/collector.md) を型として実装する。
  - Done when: 取得port、保存済み原本を処理するport、共通の入出力・失敗型が定義され、domainとapplicationが具体的なsource packageをimportせず、HTTP・DOM・source固有型が境界を越えないことをtestで確認している。
- [ ] `CP-0018` `planned` — 原本メタデータと価格観測値の追記型保存を実装する。
- [ ] `CP-0066` `planned` — processing run、extracted record、observation candidateを追記型で保存し、欠損した解析結果を確定観測と分離する。
  - Depends on: `CP-0016`, `CP-0017`, `CP-0018`
  - Done when: 原本から各中間結果、確定観測またはreviewまで追跡でき、同じ原本の再処理が以前の結果を上書きしない。
- [ ] `CP-0019` `planned` — content hash、情報源内ID、観測値の重複防止規則を決める。
- [ ] `CP-0020` `planned` — 取込、再解析、review確定のtransaction boundaryを定義する。
  - Depends on: `CP-0018`, `CP-0066`
- [ ] `CP-0021` `planned` — DBとartifact storageの片方だけが成功した場合の状態、再実行、孤立データ処理を決める。
- [ ] `CP-0022` `planned` — API、Worker、migration用のDB roleと権限を分ける。
- [ ] `CP-0023` `planned` — 欠損、不正金額、重複、再解析、rollbackのテストを作る。
- [ ] `CP-0062` `planned` — 選定DBを使うmigrationとintegration testをGitHub Actionsへ追加する。
  - Depends on: `CP-0012`, `CP-0023`
  - Done when: 空DBへのmigrationと保存・冪等性・rollbackの検査が本番候補と同じDB engineで成功する。
- [ ] `CP-0088` `planned` — 手元のデータを失わずに別環境へ移せる最小のdump・復元手順を作る。
  - Depends on: `CP-0016`, `CP-0018`
  - Done when: 成果物は`backup-restore` Runbookで、[Runbooksの作成条件](../runbooks/README.md#作成する条件)が求める対象、整合性、backup、空環境への復元、検証を含む。稼働中のCompose環境からdumpを取って`var/db/`へ置き、空のvolumeから復元してAPIとWorkerが接続できること、artifact volumeを取り出して戻せることを実行して確認している。手順は接続先、認証、出力先を環境変数または引数で受け取り、本文へ環境固有の値を書かない。開発機と[配置先](../adr/0014-postgresql-self-hosted.md)で同じコマンド列になることを、`CP-0044`が手順を書き直さずに包めるかたちで満たす。取得原本と人が下したreviewの判断は再取得できないため、実データが生まれる`CP-0024`より前に用意する（[ADR-0023](../adr/0023-named-volume-for-database-data.md)）。暗号化、世代管理、manifest、復元訓練は`CP-0044`が扱う。

完了条件: 固定JSON/CSVサンプルを投入し、欠損した抽出結果を確定観測と分離しながら、追跡可能で重複のない観測値を再現できる。

## Phase 3 — ローカルWeb Collectorを縦に通す

- [ ] `CP-0024` `planned` — 最も構造化された情報源で、取得、原本保存、解析、同定、DB保存まで実装する。
  - Depends on: `CP-0074`
  - Done when: URL、request、応答・構造検査、parser、source内IDの解釈が`adapters/sources/<source-slug>/`と所有関係を明示した設定・fixture・testに収まり、entrypointから共通portへ注入され、applicationにsource slugによる処理分岐がない。通常実行、dry run、再実行、結果確認、終了codeを`ingestion` Runbookに書いている（[Runbooksの作成条件](../runbooks/README.md#作成する条件)）。
- [ ] `CP-0025` `planned` — User-Agent、timeout、低頻度アクセス、backoff、最大再試行、403・429・challenge時の停止をsource設定として定義する。
- [ ] `CP-0026` `planned` — Git管理外のsource由来fixtureとrepository内の合成fixtureを用意し、ネットワークなしでparserをテストする。
  - Depends on: `CP-0074`
- [ ] `CP-0027` `planned` — 実行欠落、通信・応答・構造・データ品質・保存の失敗を段階別に検知し、異常なrunを正常終了または正常な0件にしない。
  - Depends on: `CP-0024`
  - Done when: HTTP成功だけに依存せず、最終URL、media type、source固有の目印、必須構造、件数、必須項目取得率、価格解析率、保存結果を検査し、異常なrunが観測の確定、最終成功日時、鮮度を更新しないことをtestで確認している。
- [ ] `CP-0075` `planned` — source障害の切り分け、停止、保存済み原本からの再解析、検証後の手動再開を実装し、`source-failure` Runbookにする。
  - Depends on: `CP-0025`, `CP-0026`, `CP-0027`
  - Done when: sourceの運用状態、停止理由、直近試行、最終成功日時、失敗段階、診断証拠を確認でき、一つのsourceを停止したまま他sourceの取込を継続し、parser修正後に回帰test、versionを更新した再解析、dry run、差分確認を経て手動再開できる。
- [ ] `CP-0028` `planned` — 2つ目、3つ目の情報源を追加し、共通契約を見直す。
  - Depends on: `CP-0074`, `CP-0075`
  - Done when: 各source packageが相互に依存せず、source固有のURL・応答構造・価格条件の表記と抽出規則が共通HTTP transport、application、domain、永続化、APIへ漏れずに追加でき、共通契約を変更した場合はsource固有事情ではなく共通の意味を追加した根拠を契約文書へ記録している。
- [ ] `CP-0089` `planned` — parser versionを更新したときの再解析手順を`reparse` Runbookにする。
  - Depends on: `CP-0066`, `CP-0075`
  - Done when: 対象の選択、旧結果の保持、実行、差分確認、rollbackを[Runbooksの作成条件](../runbooks/README.md#作成する条件)のとおり書き、保存済み原本から一度実行して確認している。障害時の切り分けと手動再開は`CP-0075`の`source-failure` Runbookが扱い、ここでは計画的なparser更新だけを対象にする。
- [ ] `CP-0063` `planned` — Collector contract testと固定fixtureによるparser regression testをGitHub Actionsへ追加する。
  - Depends on: `CP-0017`, `CP-0026`, `CP-0027`
  - Done when: source非由来の合成fixtureだけを使い、外部情報源へ接続せずに両方の検査とsource packageの依存境界検査が成功する。source由来fixtureはCIとGitへ含めない。

完了条件: 2〜3店舗のデータが同じ観測モデルに入り、一つの失敗が他へ波及しない。

## Phase 4 — カード同定、相場照会、最小APIを作る

- [ ] `CP-0029` `planned` — TCG、セット、カード番号、レアリティ、版、言語による同定規則を検証する。
- [ ] `CP-0030` `planned` — 原文表記、正規化表記、別名、同定試行、候補と根拠を保存する。
- [ ] `CP-0031` `planned` — 完全一致、自動候補、レビュー必須、未同定を区別する。
- [ ] `CP-0090` `planned` — レビュー待ちの同定を人が確定・却下・保留できる操作を実装する。
  - Depends on: `CP-0020`, `CP-0068`, `CP-0031`
  - Done when: review queueの一覧と1件の詳細（理由、原本参照、抽出結果、同定候補と根拠）をCLIまたはJSONで確認でき、確定・却下・保留が`CP-0068`の定めた状態遷移どおりに追記されて、当初の候補と判断履歴が残る。確定した同定が`CP-0032`の集計へ反映される。人間の判断で解決できない処理失敗をqueueへ混ぜない（[データモデル](../architecture/data-model.md#取込実行とレビュー)）。操作手順は`review-queue` Runbookに書く（[Runbooksの作成条件](../runbooks/README.md#作成する条件)）。`CP-0038`の試験運用でレビュー時間を測るため、Phase 5より前に用意する。
- [ ] `CP-0032` `planned` — 最新価格、中央値、最高値、最低値、店舗数、鮮度、スプレッドを計算する。
- [ ] `CP-0033` `planned` — 集計値と根拠観測をCLIまたはJSONで確認できるようにする。
- [ ] `CP-0034` `planned` — API contract、認証、versioning、pagination、エラー形式を定義する。
- [ ] `CP-0035` `planned` — 読取りendpointと書込みendpointを分類し、書込みのidempotencyと同時更新規則を決める。
- [ ] `CP-0036` `planned` — Card Digger等がDBへ直接接続せず、相場と根拠観測を取得できる最小APIを実装する。
- [ ] `CP-0037` `planned` — APIとCollection Workerを別serviceとして起動できることを確認する。

完了条件: 代表カードについて、根拠付きの店舗比較と履歴をAPIから再現できる。レビュー必須と判定された同定を人が確定でき、その結果が集計へ反映される。

## Phase 5 — 試験運用して価値を判定する

- [ ] `CP-0038` `planned` `owner` — 低頻度の増分取得を2〜4週間実行する。
  - Owner action: 2〜4週間、実際に定期取得を運用する。
  - Depends on: `CP-0075`
- [ ] `CP-0039` `planned` — 成功率、重複率、未同定率、障害分類、検知・復旧時間、誤検知、レビュー時間、parser変更、保守時間を記録する。
- [ ] `CP-0040` `planned` `owner` — 仕入れまたは売却判断に役立った事例を [Experiments](../experiments/README.md) に記録する。
  - Owner action: 実際の仕入れ・売却の判断で使い、役立った事例と外れた事例を提供する。
- [ ] `CP-0041` `planned` — 古い価格が新しい価格として表示されず、sourceの停止理由と最終成功日時を確認できることを検証する。
- [ ] `CP-0042` `planned` `owner` — API、Worker、DBを別serviceとして本人の端末またはprivate networkへ配置し、API、DB、artifact storageをInternetへ公開しない。
  - Owner action: 配置先の端末と private network を用意する。
  - Done when: 配置、private接続、role、secret、health checkの手順を`deployment` Runbookに書き（[Runbooksの作成条件](../runbooks/README.md#作成する条件)）、その手順どおりに配置した環境でAPIとWorkerが動き、API、DB、artifact storageがInternetから到達不能であることを確認している。
- [ ] `CP-0043` `planned` — 後方互換なschema変更とserviceのdeployment順序を`schema-change` Runbookにする。
  - Done when: 後方互換なmigration、API・Workerのdeployment順序、rollbackを[Runbooksの作成条件](../runbooks/README.md#作成する条件)のとおり書いている。配置そのものの手順は`CP-0042`の`deployment` Runbookが扱う。
- [ ] `CP-0044` `planned` — バックアップと空環境への復元を実施する。
  - Depends on: `CP-0088`
  - Done when: 日次backupと、schema migration・大量手動取込・重要なreview作業の前の臨時backupが実行され、backupの失敗と前回成功からの26時間超過を検知できる（`DB-REC-01`）。暗号化した日次7世代・週次4世代の保持、基準時刻・migration revision・artifact manifest・checksumを含むbackup set、空環境への復元訓練を実施し、[DB要件](../architecture/database-requirements.md#backup復旧可用性)の`DB-REC-*`を実測で満たしている。手順そのものは`CP-0088`が作り、ここではそれを運用として満たす。
- [ ] `CP-0045` `planned` — 継続、対象変更、中止の判断をADRに残す。

完了条件: 利用価値、維持時間、データ品質を数値と事例で説明できる。

## Phase 6 — 手動画像取込とOCRを検証する

構造化Webだけでは不足すると判明した場合に進む。

- [ ] `CP-0046` `planned` — 画像、店舗、URL、公開日時を一緒に受け取る手動取込を作る。
- [ ] `CP-0047` `planned` — 原画像を先に保存し、OCR結果をextracted recordとして派生関係付きで残す。
  - Depends on: `CP-0066`
- [ ] `CP-0048` `planned` — 項目単位の抽出confidenceとカード同定のmatch scoreを分け、OCR由来の抽出結果を`CP-0090`のreview queueへ載せる。
  - Depends on: `CP-0090`
  - Done when: 抽出confidenceと同定のmatch scoreが別の指標として保存され、OCR由来のreview itemが既存のqueueと同じ操作で確定・却下・保留でき、OCR固有の確認手順を`review-queue` Runbookへ追記している。
- [ ] `CP-0049` `planned` — 誤認識率と1枚あたりのレビュー時間を測る。

完了条件: 人間の修正時間を含め、手入力より有利か判断できる。

## Phase 7 — X取得を判断する

X限定情報の利益が取得・保守コストを上回る場合だけ進む。

- [ ] `CP-0050` `planned` — Webとの重複率、X限定情報数、判断への寄与、月間件数を測る。
- [ ] `CP-0051` `planned` — 公式APIの料金、rate limit、利用規約をその時点で再確認する。
- [ ] `CP-0052` `planned` — 公式API、手動取込、非公式取得の費用・規約・停止リスク・保守時間を比較してADRに残す。
- [ ] `CP-0053` `planned` — X固有コードを交換可能なsource adapter内に閉じ込める。
- [ ] `CP-0054` `planned` — 取得停止後も保存済みデータと他の機能を利用できることを確認する。

完了条件: 採用理由、運用制約、撤退条件が明文化されている。

## Phase 8 — Card Diggerと連携する

相場データの有用性を確認した後に進む。

- [ ] `CP-0055` `planned` — Card Diggerのユースケースから必要な問い合わせを定義する。
- [ ] `CP-0056` `planned` — カード識別子、曖昧一致、鮮度、欠損時の応答を決める。
- [ ] `CP-0057` `planned` — Phase 4で作成したAPI contractをCard Diggerの実利用に合わせて拡張する。
- [ ] `CP-0058` `planned` — 中央値、店舗数、鮮度、ばらつき、根拠観測をCard Diggerが正しく評価できることを確認する。

完了条件: 本人が管理するCard Diggerが内部DBへ依存せず、非公開APIから根拠付き価格情報を取得できる。
