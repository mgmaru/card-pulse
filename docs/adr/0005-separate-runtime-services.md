# ADR-0005: API、Collection Worker、DBを別serviceとして扱う

- 状態: Accepted
- 日付: 2026-09-06

## Context

Card Pulseには、Card Diggerから短時間で応答するAPI処理と、外部情報源の遅延・仕様変更・再試行を伴う収集処理がある。DBは永続データ、backup、復旧を担い、APIやWorkerとは異なるlifecycleを持つ。

同じprocessや同じruntime unitへまとめると、Collectorの停止、高いCPU・memory使用、再起動がAPI応答へ波及する。一方、serviceを分けてもDB schemaへの依存は残るため、物理分離だけでは変更影響をなくせない。

## Decision

- Card Pulse API、Collection Worker、DBを別のruntime serviceとして起動・配置する。
- raw artifact storageもDBとは別の保存serviceまたはvolumeとして扱う。
- 公開するのはHTTPS APIだけとし、Worker、DB、artifact storageを外部公開しない。
- Card Digger等のclientにDB credentialを渡さない。
- APIとWorkerは同じrepositoryとPython packageのdomain・application codeを共有し、別entrypointから起動する。
- schedulerはAPI requestを経由せず、Worker jobを起動する。

具体的なhosting provider、台数、network製品、可用性構成は別途決定する。

## Consequences

- Collectorの障害と負荷をAPIのruntimeから分離できる。
- API、Worker、DBを異なる頻度でdeploy・upgradeできる。
- APIとWorkerに異なるDB roleを割り当てられる。
- service間network、認証、observability、接続失敗を設計する必要がある。
- DB schema変更時はAPIとWorkerの互換性を保つmigration・deployment手順が必要である。
- ローカルでは複数serviceを簡単に起動する仕組みが必要になる。

## Alternatives considered

- API process内で定期収集する: 構成は少ないが、長時間処理と外部障害がAPIへ影響する。
- DBとAPIを一つのhost・lifecycleに固定する: 初期費用を抑えられるが、永続データとstateless computeを独立して管理しにくい。
- APIとWorkerを別repositoryにする: 現段階ではdomain codeとcontractの重複、release調整が増える。

## Validation

- Docker ComposeでAPI停止中もWorkerとDB、Worker停止中もAPIと保存済みデータを扱えることを確認する。
- 試験環境でWorker高負荷時のAPI応答を測る。
- Phase 2でrole別DB権限を定義する。
- 最初のserver配置前に、後方互換なmigrationとdeployment順序をRunbook化する。
