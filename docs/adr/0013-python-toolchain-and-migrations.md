# ADR-0013: CPython 3.14、uv、Alembicを開発基盤に採用する

- 状態: Accepted
- 日付: 2026-09-12
- 決定者: プロジェクトオーナー
- 置換するADR: なし
- 置換されたADR: なし

## Context

Card Pulseは、同じPython packageを共有するAPIとCollection Workerを別runtimeとして実行し、Docker ComposeとCIで同じ依存関係を再現する。これからpackage構成を作る前に、Python version、依存関係の解決と固定方法、DB schemaの変更手段を揃える必要がある。

[ADR-0004](0004-server-database-selection.md)によりserver型DBの製品は比較検証後に決める一方、[ADR-0006](0006-docker-compose-local-development.md)では空DBをmigrationから作成することを決めている。そのため、DB製品を先に固定せずに採用でき、選定後のdialectで実際のDDLを検証できるmigration手段が必要である。domainとapplicationは、特定のDB製品、DB driver、ORMから独立させる。

2026-09-12に公式資料を確認した。CPython 3.14は安定版のbugfix段階にあり、最新patchは3.14.7、end-of-lifeは2030-10の予定である。3.15はpre-release段階である。[Python versionの状態](https://devguide.python.org/versions/)と[Python 3.14.7](https://www.python.org/downloads/release/python-3147/)を根拠とする。

同日に確認したuvは、PEP 621の`pyproject.toml`、Python環境、依存解決、cross-platformの`uv.lock`、同期、buildを一つのproject interfaceで扱える。`uv.lock`はversion controlへ含めることが推奨され、`uv sync --locked`はproject metadataとlockの不一致を失敗にできる。一方、pipの`pip lock`と`pylock.toml`対応は現時点でexperimentalであり、生成したlockは現在のPython versionとplatformだけを対象とする。[uvのproject構成](https://docs.astral.sh/uv/concepts/projects/layout/)、[uvのlockと同期](https://docs.astral.sh/uv/concepts/projects/sync/)、[pip lock](https://pip.pypa.io/en/stable/cli/pip_lock/)を根拠とする。

AlembicはSQLAlchemyをengineとしてrelational databaseの変更scriptを作成、管理、実行し、DBへ接続するonline migrationとSQLを生成するoffline modeを持つ。autogenerateはDB schemaとSQLAlchemy `MetaData`の差分から候補を作れるが、rename等を完全には判定できず、生成結果には手動確認が必要である。[Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)、[offline mode](https://alembic.sqlalchemy.org/en/latest/offline.html)、[autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)を根拠とする。

## Decision

Python runtimeには標準GIL buildのCPython 3.14を使う。`pyproject.toml`には`requires-python = ">=3.14,<3.15"`を設定し、未検証のminor versionを対応範囲に含めない。最初の`.python-version`、CI、container imageは3.14.7へ固定する。containerはOS variantを明示し、再現性が必要な参照はimage digestも固定する。3.14系のpatchは、同じ品質検査とintegration testを通して明示的に更新する。

packageとPython環境の管理にはuvのproject interfaceを使う。

- project metadataとruntime dependencyはPEP 621の`[project]`、testやlint等の開発依存は標準のdependency groupsへ記録する。
- MVPは一つのinstallable packageとし、uv workspaceは構成しない。API、Worker、migration、運用CLIは同じpackageの別entrypointにする。
- `uv.lock`を依存解決結果の正としてGitへ含める。依存更新は`uv add`、`uv remove`、`uv lock`等で明示的に行い、CIとimage buildでは`uv sync --locked`を使う。
- uv自体のversionも開発環境とCIで固定し、containerではversionまたはdigestを固定する。uvとAlembicの最初の具体的なversionは`CP-0011`でpackage構成を作る時点の検証済みversionにする。
- localではuvによるCPythonの取得を利用できる。containerでは固定したPython base imageを実行環境とし、uvが別のPythonを暗黙に取得しない構成にする。
- `uv.lock`から生成できるrequirementsや`pylock.toml`は外部連携用の派生物とし、必要になるまで第二のlockfileとして管理しない。

DB migrationにはAlembicを使い、次の規則を適用する。

- `migrations/`にAlembic環境とrevisionを置く。revisionの連鎖をschema変更履歴と空DB再構築の正とし、共有済みまたは適用済みのrevisionを編集せず、新しいrevisionで訂正する。
- online migrationを通常の実行方法とする。APIやWorkerの起動時に自動実行せず、専用entrypointから一つの実行単位として適用する。DB roleとdeployment順序は`CP-0022`および最初のserver配置前のRunbookで定める。
- offline SQL生成は、DDLのreviewや接続権限を分離する場合の補助手段とする。生成時にも対象DBのdialectを指定し、DBに依存しないSQLが得られるとはみなさない。
- SQLAlchemyはAlembicのconnection、dialect、DDL型表現、および必要な`MetaData`のためのmigration依存として受け入れる。この判断だけでapplicationの永続化にSQLAlchemy ORMを採用したことにはしない。
- autogenerateは候補生成にだけ使い、revisionを必ず手動で確認する。tableやcolumnのrename、型変換、data migration、破壊的変更、constraintを重点的に確認し、constraintには安定した明示名またはnaming conventionを使う。
- `CP-0009`と`CP-0010`では、候補DBに保守されたSQLAlchemy dialectとdriverがあること、空DBへのupgrade、既存DBのupgrade、失敗時の挙動、offline SQLを検証する。

DB製品とversion、driver、dialect固有型、transactional DDL、revision単位のtransaction、autogenerateの比較設定、downgradeとbackup復元の分担はDB選定後に決める。選定DBでAlembicを安全に使えないことがPoCで判明した場合は、新しいADRでmigration手段を置き換える。

## Consequences

- local、CI、containerでPython、依存解決、実行コマンドを同じtoolchainへ揃えられる。
- Python 3.14の新しい型注釈評価やprocess開始方法を前提に実装でき、古いminor versionとの互換性を初期設計へ持ち込まずに済む。
- Python、uv、container imageを固定するため、security修正とbugfixを取り込む更新作業が必要になる。
- native extensionを含むdependencyを追加する際は、CPython 3.14と対象container platformに対応するwheelまたは再現可能なbuild手順を確認する必要がある。
- `uv.lock`はuv固有形式である。別toolへ移行する場合は標準のproject metadataを維持し、requirementsまたは`pylock.toml`へのexportを移行経路にできる。
- AlembicによってPython package内でmigrationを管理できる一方、migration環境はSQLAlchemyと選定DBのdriverへ依存する。
- DB製品を決める前にrevision運用を定められるが、DDLの互換性やtransaction、型、indexは対象dialect上で別途検証する必要がある。
- APIとWorkerへschema変更権限を与えずに運用できる。deploymentでは互換性を保つmigration順序と専用実行手順が必要になる。

## Alternatives considered

- CPython 3.13: dependencyの対応範囲は広いが、3.14よりbugfix期間とsecurity support終了が早い。3.14非対応の必須dependencyが見つかった場合の一時的なfallbackとし、初期versionにはしない。
- CPython 3.15: support終了は遅いが、判断時点ではpre-releaseである。安定版公開後にdependencyとcontainer imageの対応を確認してからminor upgradeを再判断する。
- `venv`、pip、pip-toolsを組み合わせる: 標準的な部品を選べるが、Python取得、環境、lock、同期、buildを別々に構成する必要がある。pipの標準lockがexperimentalである現時点では採用しない。
- PDMまたはPoetry: どちらもprojectとdependencyを管理できるが、Card Pulseに必要なPython取得、lock、Docker、CIの手順をuvより少ない追加判断で構成できる根拠がない。
- FlywayまたはLiquibase: DBとは独立した実行toolとして使え、広いDB製品へ対応するが、Pythonとは別のruntime、driver、設定またはDSLが増える。単一DBを選ぶMVPには採用しない。
- SQL fileまたは自作scriptだけで管理する: 小規模な初期schemaは作れるが、revision順序、現在位置、online/offline実行、分岐の管理を再実装することになる。

## Validation

- `CP-0011`で`pyproject.toml`、`.python-version`、`uv.lock`、uv version制約を作成し、固定したCPython 3.14.7で`uv sync --locked`が成功することを確認する。
- `CP-0013`でlocalとCIが同じlockとPython versionを使うsetup、test、lint、format、型チェックのコマンドを定義する。
- dependency追加時にCPython 3.14およびlocal・containerの対象platformでinstallできることを確認する。
- `CP-0009`と`CP-0010`で候補DBごとのAlembic migrationを実行し、採用DBとdialectを決定する。
- `CP-0062`で選定DBの空環境に`alembic upgrade head`を適用し、既存schemaからのupgrade、保存のintegration test、失敗時の復旧手順を検証する。
- CPythonのminor version、package管理tool、またはmigration手段を変更する場合は、dependency互換性、lock、container、CI、保存済みDBのupgradeを確認し、新しいADRで本判断を置き換える。
