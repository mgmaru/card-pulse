# DB PoC harness (CP-0009)

[DB要件](../../docs/architecture/database-requirements.md#cp-0009のpoc合格条件)の合格条件を、PostgreSQLとMariaDBへ同じschema、同じ生成データ、同じqueryで適用して測定する一時的なharnessです。測定結果は[CP-0009 DB PoC結果](../../docs/research/database-poc-2026-09.md)にまとめます。

このディレクトリはDB選定のための検証コードであり、`src/card_pulse/`の実装ではありません。PoC schemaは[データモデル](../../docs/architecture/data-model.md)の部分集合で、確定したschemaではありません。

## 前提

- Homebrewの`postgresql@18`（18.6）と`mariadb`（12.3.3）。いずれもPoC専用のdata directoryとportで起動します。
- `uv`とCPython 3.14。依存は`pyproject.toml`と`uv.lock`で固定します。
- 生成データ、DB、backup、測定結果はすべて`var/db-poc/`へ書き出し、Gitへ含めません。

## 実行

```bash
cd scripts/db_poc
uv sync

# PoC用instanceを作成して起動する
./bin/instances.sh pg-init main && ./bin/instances.sh pg-start main
./bin/instances.sh maria-init main && ./bin/instances.sh maria-start main

# 負荷プロファイルを生成する（1倍は約540万行、10倍は約5,400万行）
uv run python -m dbpoc.generate --scale 1 --artifacts

# 候補ごとに全stepを実行する
uv run python -m dbpoc.run_all postgres --scale 1
uv run python -m dbpoc.run_all mariadb --scale 1
```

個別stepは`uv run python -m dbpoc.<module> <engine> --scale <1|10>`で実行できます。

## 構成

| module | 役割 |
| --- | --- |
| `dbpoc/config.py` | port、role、負荷プロファイル、出力先 |
| `dbpoc/schema.py` | 両候補で同じ意味になるPoC schema |
| `dbpoc/generate.py` | 決定的なデータ生成。`COPY`と`LOAD DATA`が同じ形式で読むTSVを書く |
| `dbpoc/load.py` | 一括投入、投入時間、容量、参照整合の確認 |
| `dbpoc/workload.py` | 制約を有効にしたruntime書込みと冪等な追記 |
| `dbpoc/queries.py` | `DB-QRY-01`〜`DB-QRY-05`のdialect別実装 |
| `dbpoc/bench.py` | 8 reader・2 writerの同時実行測定と実行計画 |
| `dbpoc/ingest.py` | 通常日1日分の取込と28日分の再解析 |
| `dbpoc/integrity.py` | 冪等性、制約、isolation、競合、型往復 |
| `dbpoc/crash.py` | client強制終了とDB強制終了からの復帰 |
| `dbpoc/migrate.py` | 空DB・既存schemaへのmigration、offline SQL、downgrade、失敗migrationの回復 |
| `dbpoc/roles.py` | role分離とnetwork公開範囲 |
| `dbpoc/monitor.py` | 接続、容量、lock待ち、長時間transaction、slow query、backup経過時間 |
| `dbpoc/backup.py` | 暗号化backup、空環境への復元、復元後の検証 |
| `dbpoc/run_all.py` | 上記を1候補・1プロファイル分まとめて実行する |
| `dbpoc/report.py` | 測定結果JSONから比較表を生成する |

## 注意

- `dbpoc/config.py`の`ROLE_PASSWORD`はPoC専用のlocal定数です。運用で使う認証情報をこのharnessへ入れないでください。
- backupの暗号鍵は`var/db-poc/secret/`に生成し、manifestへ含めません。
- `instances.sh`が作るinstanceは`127.0.0.1`だけを待ち受けます。設定値は測定条件としてPoC結果へ記録します。
