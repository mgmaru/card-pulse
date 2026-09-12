# Architecture Decision Records

ADRは、複数のコンポーネントへ影響する判断、将来の選択肢を制約する判断、後から理由が分かりにくくなる判断を記録する。

## 状態

- `Proposed`: 検討中
- `Accepted`: 採用中
- `Rejected`: 採用しなかった
- `Superseded`: 後続ADRに置き換えられた
- `Deprecated`: 新規利用をやめ、移行中または撤去予定

AcceptedとなったADRは、誤字やリンク切れ以外では結論を書き換えない。判断を変更するときは新しいADRを追加し、双方に置換関係を記載する。

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

新しいADRは [template.md](template.md) を複製し、4桁の連番と短いslugを付ける。

## ADR管理の機械検査

2026-09-09時点では、ADR専用validatorの導入を見送る。ADR-0008の追加で件数が7件から8件へ増えたため再検討したが、一覧、状態、日付、必須section、置換関係を手作業で確認できる規模にあり、既存の文書リンク検査でファイルと参照の欠落は検出できる。現時点で専用validatorが防ぐ具体的な不整合も発生していないため、検査規則とCIを増やす費用を先に負わない。

ADRが12件へ達した場合、または状態遷移、置換関係、一覧更新の不整合が発生した時点で、専用validatorを再検討する。
