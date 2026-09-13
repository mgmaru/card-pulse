# Architecture Decision Records

ADRは、複数のコンポーネントへ影響する判断、将来の選択肢を制約する判断、後から理由が分かりにくくなる判断を記録する。

## 状態

- `Proposed`: 検討中
- `Accepted`: 採用中
- `Rejected`: 採用しなかった
- `Superseded`: 後続ADRに置き換えられた
- `Deprecated`: 新規利用をやめ、移行中または撤去予定

AcceptedとなったADRは、誤字やリンク切れ以外では結論を書き換えない。判断を変更するときは新しいADRを追加し、双方に置換関係を記載する。

## 判断理由の書き方

ADRの価値は、何を選んだかよりも、なぜその選択に至ったかが後から読み取れることにある。結論だけが残った判断は前提が変わったときに再評価できず、同じ検討をやり直すことになる。

- `Decision`には、選択の記述に続けてその選択を決めた理由を書き、理由の中心となる一文を**太字**にする。
- 太字にするのは、他の選択肢ではなくこの選択を採る根拠になった一文に限る。節ごとに一つを目安とし、段落全体や結論そのものを太字にしない。強調が増えるほど、どれが決め手だったかは読み取れなくなる。
- 理由は選択の言い換えにせず、比較対象との差、受け入れた制約、避けたい失敗のいずれかを含む形で書く。「保守しやすいため」のように、反対の選択にも当てはまる書き方にしない。
- `Alternatives considered`には、各選択肢を採用しなかった理由を、`Decision`で強調した理由と対応する観点で書く。
- 判断の前提にした外部の事実には、確認日と参照先を添える。

[ADR-0015](0015-quality-check-toolchain.md)の`Decision`が、この書き方の例になる。

この規則は今後の作成と改訂に適用する。強調を加えるためだけに既存ADRの本文を書き換えない。

## 一覧

| ADR | 状態 | 判断 |
| --- | --- | --- |
| [0001](0001-modular-monolith.md) | Accepted | MVPをPythonのモジュラーモノリスとして構成する |
| [0002](0002-append-only-provenance.md) | Accepted | 原本と価格観測を追記型で保存し、出典を追跡する |
| [0003](0003-mvp-local-storage.md) | Superseded | MVPはSQLiteとローカルファイルシステムを使う |
| [0004](0004-server-database-selection.md) | Accepted | 構造化データをサーバー側DBに置き、製品は比較検証後に選定する |
| [0005](0005-separate-runtime-services.md) | Superseded | API、Collection Worker、DBを別serviceとして扱う |
| [0006](0006-docker-compose-local-development.md) | Accepted | Docker Composeでローカルのservice topologyを再現する |
| [0007](0007-layered-ingestion-data.md) | Accepted | 情報源横断の構造化データを一つの論理DBで管理し、処理段階で分離する |
| [0008](0008-opaque-card-identity-id.md) | Accepted | カード同定には意味を持たない内部UUIDを使い、属性と外部IDを分離する |
| [0009](0009-pokemon-mvp-sources.md) | Superseded | ポケモンカードのMVP情報源に晴れる屋2と遊々亭を選ぶ |
| [0010](0010-pokemon-mvp-source-candidates.md) | Superseded | ポケモンカードのMVP情報源候補に晴れる屋2、遊々亭、フルコンプ池袋店を選ぶ |
| [0011](0011-no-external-source-inquiries.md) | Superseded | MVP情報源を公開条件だけで判断し外部照会を行わない |
| [0012](0012-private-personal-operation.md) | Accepted | Card Pulseを個人用の非公開アプリとして運用する |
| [0013](0013-python-toolchain-and-migrations.md) | Accepted | CPython 3.14、uv、Alembicを開発基盤に採用する |
| [0014](0014-postgresql-self-hosted.md) | Accepted | 構造化データのDBにPostgreSQL 18を採用し、self-hostで運用する |
| [0015](0015-quality-check-toolchain.md) | Accepted | 品質検査にruff、mypy、pytestを採用し、一つのコマンドで実行する |
| [0016](0016-local-compose-artifact-volume.md) | Accepted | ローカル環境のartifact storageをDocker volume上のfilesystemにする |
| [0017](0017-colima-container-runtime.md) | Superseded | ローカル開発のcontainer runtimeにColimaを採用する |
| [0018](0018-per-os-container-runtime.md) | Accepted | container runtimeを選定基準で決め、OSごとに実装を選ぶ |

新しいADRは [template.md](template.md) を複製し、4桁の連番と短いslugを付ける。

## ADR管理の機械検査

2026-09-12にADR-0013を追加して13件となったため、専用validatorの導入を再検討し、引き続き見送った。一覧、状態、日付、必須section、置換関係は一つの変更内で確認でき、既存の文書リンク検査がファイルと参照の欠落を検出する。追加した5件を含めてID、状態、一覧、置換関係の不整合は発生しておらず、現時点では検査規則とCIの保守対象を増やす具体的な効果が小さい。

ADRが20件へ達した場合、または状態遷移、置換関係、一覧更新の不整合が発生した時点で、専用validatorを再検討する。
