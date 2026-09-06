# ADR-0006: Docker Composeでローカル開発環境を構成する

- 状態: Accepted
- 日付: 2026-09-06

## Context

Card PulseはAPI、Collection Worker、サーバー型DB、artifact storageを別serviceとして扱う。開発者ごとにruntimeやDBを個別installすると、version、設定、network、初期化手順が異なりやすい。

ローカルでは複数の物理serverを用意せず、本番に近いservice topologyを一台のPCで再現する必要がある。

## Decision

- ローカル開発環境はDocker Composeで構成する。
- API、Worker、選定DB、artifact storageを別containerまたは明示的なserviceとして定義する。
- application runtimeと直接依存をimageで固定する。
- database schemaはmigrationから作成し、手作業で初期状態を作らない。
- 開発用データはvolumeへ保存し、秘密情報はimageとrepositoryへ含めない。
- testやCIでも可能な範囲で同じdatabase engineとservice dependencyを使用する。

Dockerで再現できる範囲と限界は [Dockerによる環境再現](../learning/docker-environment-reproduction.md) に記載する。

## Consequences

- 新しい開発環境で複数serviceを同じ手順から起動できる。
- 本番候補と同じdatabase engineでmigrationとintegration testを実行できる。
- container image、Compose設定、volume初期化を保守する必要がある。
- Docker Desktop等の導入が必要になり、host OSとの差やfilesystem性能差は残る。
- managed database、cloud IAM、load balancer、backup、自動拡張、実network障害はDocker Composeだけでは検証できない。

## Alternatives considered

- hostへ各依存を直接installする: 軽い構成では速いが、versionと初期化手順が環境ごとにずれやすい。
- 開発用の共有serverだけを使う: 本番に近いが、offline開発、並行作業、データ初期化が難しい。
- local Kubernetes: 本番候補になり得るが、MVPのローカル環境には管理対象が多い。

## Validation

Phase 1で次を満たすCompose環境とRunbookを作る。

- 一つの手順でbuild・起動できる。
- health check後にmigrationとtestを実行できる。
- volumeを維持した再起動と、明示的な初期化を区別できる。
- API、Worker、DBの停止を個別に試せる。
- 新しい環境で同じ手順を再現できる。
