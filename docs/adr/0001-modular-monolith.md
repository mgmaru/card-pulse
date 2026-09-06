# ADR-0001: MVPをモジュラーモノリスとして構成する

- 状態: Accepted
- 日付: 2026-09-06

## Context

Card Pulseは、情報源ごとの取得、原本保存、解析、カード同定、価格観測の永続化、相場照会を扱う。各処理には異なる変更理由がある一方、MVPでは1 TCG、2〜3店舗、ローカル実行だけを対象とする。

サービスを分割するとdeployment、通信、schema互換、障害監視が先に必要になる。責務を分けず一つのモジュールへ集約すると、情報源固有の仕様が保存・照会ロジックへ漏れ、Collectorの追加と交換が難しくなる。

## Decision

MVPは単一Pythonパッケージとして実行し、コードを次の境界へ分ける。

- `domain`: 価格観測、カード同定、出典、集計の規則
- `application`: 取込、再解析、レビュー、照会のユースケースとport
- `adapters`: 情報源、永続化、原本保存の具体的実装
- `entrypoints`: CLI、scheduler、将来のAPI

依存方向は外側からdomainへ向ける。domainとapplicationからsource固有コードやSQLite実装へ依存しない。

## Consequences

- 単一プロセスとローカル環境でMVPを素早く検証できる。
- source、DB、原本保存をport経由で交換できる。
- Card Diggerとの境界を内部DBから分離できる。
- モジュール境界はreviewとtestで維持する必要がある。
- 別サービス化が必要になった場合、applicationのユースケース境界を候補として再評価できる。

## Alternatives considered

- sourceごとのmicroservice: MVPの規模に対して運用負担が大きい。
- レイヤなしの単一script群: 最初は短いが、source固有処理と保存・同定が結合しやすい。
- Card Digger内部への実装: 価格履歴を独立資産として利用する目的と合わない。

## Validation

2〜3個目のsource adapterを追加した際に、共通contractが店舗固有の都合に引かれていないか確認する。deployment、負荷、障害分離の実測から別プロセス化が必要になった場合、新しいADRで再判断する。
