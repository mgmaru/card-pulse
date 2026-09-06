# ADR-0004: サーバー側DBを使い、製品は比較検証後に選定する

- 状態: Accepted
- 日付: 2026-09-06
- 置換するADR: [ADR-0003](0003-mvp-local-storage.md)

## Context

Card Pulseは将来、完全自動化したCollection Workerと、PC・スマートフォン等で動くCard Diggerから同時に利用される。APIやWorkerを別の実行環境へ配置する場合、単一hostのローカルファイルとしてDBを持つ構成では共有、複数instance、backup、復旧が制約になる。

一方、PostgreSQL等の特定製品を採用するには、データ整合性、transaction、query、運用、backup・復旧、費用、開発環境との整合を比較する根拠がまだない。

## Decision

- 構造化データのsystem of recordはサーバー側DBへ置く。
- Card Digger等のclientはDBへ直接接続せず、Card Pulse APIを利用する。
- DB製品とhosting providerは現時点で確定しない。
- 複数候補を要件で比較し、上位候補のPoC後に新しいADRで製品を決定する。
- ローカル開発では、選定したDB製品をDocker containerとして実行し、本番とのdatabase engine差を避ける。
- HTML、JSON、CSV、PDF、画像等の原本本体はDBと別のartifact storageへ置く。

選定方法は [DB選定の判断軸](../learning/database-selection.md) に従う。

## Consequences

- APIとWorkerが同じ構造化データをserver経由で利用できる。
- 複数端末やAPIの複数instanceへ発展できる。
- DB serverまたはmanaged databaseの費用、network、認証、監視、backupが必要になる。
- 製品が決まるまでDB固有のschema、migration、query最適化は確定できない。
- DB製品を先に決めず、Card Pulse固有のqueryと運用を使ったPoCを選定作業に含める必要がある。

## Alternatives considered

- SQLiteをAPI serverのローカルファイルとして使う: 小規模な単一instanceでは簡単だが、API・Workerの分離と複数instanceを目標にする構成には合わない。
- PostgreSQLを直ちに採用する: 有力候補だが、他候補との比較と運用要件が未確認である。
- DBを使わずobject storageだけに保存する: relationship、unique constraint、transaction、相場queryを実装しにくい。

## Validation

Phase 1で次を実施し、DB製品を決める。

- 想定データ量、同時接続、可用性、復旧、費用の要件化
- relational databaseを中心とした複数候補の比較
- 同一原本の冪等な取込
- Worker書込み中のAPI照会
- 最新価格、中央値、店舗数、履歴のquery
- schema migration中の互換性
- backupから空環境への復元
