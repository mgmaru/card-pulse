# ADR-0017: ローカル開発のcontainer runtimeにColimaを採用する

- 状態: Superseded
- 日付: 2026-09-13
- 決定者: プロジェクトオーナー
- 置換するADR: なし
- 置換されたADR: [ADR-0018](0018-per-os-container-runtime.md)

## Context

[ADR-0006](0006-docker-compose-local-development.md)はローカル開発環境をDocker Composeで構成すると決めたが、そのComposeを何の上で動かすかは決めていない。`CP-0012`でCompose環境を実装した時点で、開発機にcontainer runtimeが入っていないことが分かり、選定が必要になった。

macOSはLinux containerを直接実行できず、いずれの選択肢もLinux VMを用意する。そのためruntimeの選択は、VMの実装、docker CLIとcompose v2の入手方法、そしてライセンス条件をまとめて決めることになる。開発機はApple Silicon（arm64）、`CP-0061`が使うCIはGitHub-hosted runner（amd64、Docker Engine同梱）である。

比較した4つの条件は次のとおりで、確認日は2026-09-13である。

| runtime | ライセンス | 入手 | GUI |
| --- | --- | --- | --- |
| Colima | MIT | Homebrew formula（`colima`、`docker`、`docker-compose`） | 不要 |
| Docker Desktop | 250人未満かつ年商1,000万ドル未満は無償（[Docker Desktop license](https://docs.docker.com/subscription/desktop-license/)） | Homebrew cask | 必要 |
| Rancher Desktop | Apache 2.0 | Homebrew cask | 必要 |
| OrbStack | 個人・非商用のみ無償。商用は8ドル/user/月（[OrbStack pricing](https://orbstack.dev/pricing)） | Homebrew cask | 必要 |

技術的な差は小さい。4つともLinux VM上でDocker Engineまたはmobyを動かすため、named volumeが image 側のmount pointの所有者を引き継ぐこと、`127.0.0.1`へのport bind、health check、`docker compose cp`の挙動は同じになる。CI runnerとの差も4つで変わらない。

ライセンス条件には差がある。[ADR-0012](0012-private-personal-operation.md)は、Card Pulseを個人用・非公開としながら「仕入れ・売却判断に使うため、個人用・非公開という事実だけで私的使用に当たるとは判断しない」と明記し、この区分についての判断を避けている。

## Decision

ローカル開発のcontainer runtimeにColima 0.10.3を採用する。docker CLIとcompose v2はHomebrewの`docker`と`docker-compose` formulaから入れ、`~/.docker/config.json`の`cliPluginsExtraDirs`へplugin pathを登録して`docker compose`として呼び出す。

**Colimaを採るのは、runtimeのライセンス判断をこのプロジェクトへ持ち込まないためである。他の3つはいずれも「個人利用か商用か」または「従業員数と年商」という区分に無償条件が紐付き、ADR-0012がCard Pulse自身については判断を避けた区分を、runtimeのために別途決めることになる。** MITのColimaにはその区分がない。

技術的な優劣で選んでいない。4候補ともこの構成で使う機能に差が出ないため、受け入れる不便は次の3点になる。GUIが無く`colima start`を明示的に実行すること、compose v2をplugin pathへ登録する一手間、Docker Desktopを前提に書かれた外部情報との差である。

### repositoryをruntimeへ依存させない範囲

runtimeは開発機ごとの選択であり、repositoryの成果物はそれに依存させない。

- `compose.yaml`はCompose Specificationの範囲で書き、runtime固有のextensionを使わない。
- imageは`linux/amd64`と`linux/arm64`を含むmulti-archのdigestで固定する。開発機はarm64、CIはamd64で同じ定義を使う。
- build、起動、test、停止、初期化の手順は`docker compose`で表す。Colima固有のコマンドはRunbookの前提条件にだけ置く。
- CIはrunnerに用意されたDocker Engineをそのまま使い、Colimaを導入しない。

この範囲を守る限り、runtimeを入れ替えても`compose.yaml`、`Dockerfile`、testは変更せずに済む。

### VMの構成

CPU、memory、diskの割り当てはColimaの既定値から始め、実際に使った値と変更した場合の理由を`CP-0012`のローカル開発環境Runbookの前提条件へ記録する。`--vm-type`はApple SiliconのVirtualization.frameworkという既定に任せ、ADRでは固定しない。実測なしに割り当てを決めても、[DB要件](../architecture/database-requirements.md)の判断材料にはならないためである。

## Consequences

- ライセンス条件の確認が今後不要になる。利用者や用途が変わってもruntimeの区分を判断し直さなくてよい。
- 開発を始めるたびに`colima start`が要る。停止中は`docker`コマンドがdaemonへ接続できず失敗するため、Runbookの前提条件に含める。
- `docker`本体とcompose pluginが別formulaになり、versionが独立して上がる。前提確認に`docker compose version`を含める。
- GUIが無いため、containerとvolumeの状態確認はCLIで行う。
- Docker Desktopを前提に書かれた外部の手順とは、daemonの起動方法とplugin pathの扱いで食い違う。
- macOSのVM層はCI runnerのLinuxと同じではない。bind mountの性能、fsync、file systemのcase sensitivityは再現しない（[Dockerによる環境再現](../learning/docker-environment-reproduction.md)）。
- 開発機に`lima`が依存として入る。Colimaを外す場合はこれも合わせて判断する。

## Alternatives considered

- **Docker Desktop**: 無償条件は「250人未満かつ年商1,000万ドル未満」で、個人であれば明確に満たす。外部情報も最も多い。採らなかったのは、無償条件が組織の規模という外部条件に紐付き、条件が変わるたびに再確認が必要になるためである。ライセンスを判断材料から外せない点でColimaと差があり、技術的には同等の第一候補である。
- **Rancher Desktop**: Apache 2.0でライセンス判断は不要になり、この点ではColimaと同等である。採らなかったのは、Kubernetesを含む分だけ導入と常駐の対象が広く、MVPで使わない機能を保守対象に入れることになるためである。GUIによる状態確認が必要になった場合の第一候補になる。
- **OrbStack**: Apple Siliconで最も軽く、起動も速い。採らなかったのは、無償条件が「personal, non-commercial use」であり、ADR-0012がCard Pulse自身について判断を避けた区分にそのまま該当するためである。商用と判断する場合は8ドル/user/月が必要になる。
- **Podman**: OSSでライセンス判断は不要だが、`docker compose`の互換性が実装によって異なり、health checkと`depends_on`のconditionの扱いで差が出る可能性がある。compose定義をruntimeへ依存させないという方針と衝突するため、比較の対象から外した。

## Validation

- `CP-0012`で、ローカル開発環境Runbookの手順どおりにbuild、起動、health check、障害分離、初期化が成功することを確認する。
- `CP-0061`で、Colimaを使わないGitHub-hosted runner上でも同じ`compose.yaml`と`Dockerfile`が動くことを確認する。両方が通れば、compose定義がruntimeへ依存していないことの証拠になる。
- 次のいずれかが起きた場合に再評価する。
  - `colima start`の手間または不具合が、開発の中断として実際に現れる。
  - Colimaが保守されなくなる、または新しいmacOSとApple Siliconへ追従しなくなる。
  - 利用者の追加、GUIによる状態確認の必要、ADR-0012の範囲変更など、選定の前提が変わる。
  - 既定のVM割り当てでbuildまたは取込が収まらなくなる。
