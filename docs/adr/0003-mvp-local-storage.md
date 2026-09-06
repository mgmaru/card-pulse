# ADR-0003: MVPはSQLiteとローカルファイルシステムを使う

- 状態: Accepted
- 日付: 2026-09-06

## Context

MVPは一人または少人数によるローカル実行、1 TCG、2〜3店舗、低頻度収集を対象とする。最初に検証するのは分散運用や高負荷処理ではなく、価格データの比較可能性と利用価値である。

構造化データと取得原本には異なるアクセス特性がある。観測、関係、状態はtransactionとqueryが必要だが、HTML、JSON、PDF、画像等の原本本体はbyte列として再解析できればよい。

## Decision

- 構造化データのMVP永続化にはSQLiteを使う。
- 取得原本本体はローカルファイルシステムの`var/raw/`に保存する。
- SQLiteには原本メタデータとartifact IDまたは安定した相対参照を保存する。
- DBと原本保存はapplicationが定義するportの後ろに置く。
- ローカルDB、原本、ログ、review用データは`var/`以下に置き、Git管理外とする。

Pythonの具体的なversion、package manager、migration toolはPhase 1で実行環境と合わせて別途決める。

## Consequences

- 外部サービスなしで開発、test、backup、復元を試せる。
- SQLiteからPostgreSQL、ファイルシステムからobject storageへ移行する余地をportで残せる。
- 複数writer、高可用性、大規模並列処理は対象にしない。
- DBと原本を整合した時点へ復元するbackup手順が必要になる。

## Alternatives considered

- PostgreSQL: 将来候補だが、MVPではサーバー管理と運用が増える。
- 原本をSQLite BLOBに保存: transactionは単純になるが、原本の確認、再解析、backup単位が重くなる可能性がある。
- object storage: ローカルMVPでは外部依存が増える。

## Validation

2〜4週間の試験運用でDB容量、原本容量、取込時間、query時間、backup・復元時間を測る。並列実行やデータ量がSQLiteの制約になる場合、新しいADRで移行を判断する。
