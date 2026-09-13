# ADR-0018: container runtimeを固有名詞ではなく選定基準で決め、OSごとに実装を選ぶ

- 状態: Accepted
- 日付: 2026-09-13
- 決定者: プロジェクトオーナー
- 置換するADR: [ADR-0017](0017-colima-container-runtime.md)
- 置換されたADR: なし

## Context

[ADR-0017](0017-colima-container-runtime.md)は、macOSの開発機でColimaを採用した。決め手は、無償条件が「個人利用か商用か」「従業員数と年商」という区分に紐付くruntimeを避け、[ADR-0012](0012-private-personal-operation.md)がCard Pulse自身については判断を避けた区分を、runtimeのために別途決めずに済ませることだった。あわせて「repositoryの成果物をruntimeへ依存させない範囲」を4点で定義した。

その後、同じプロジェクトオーナーが別のマシンへ移る可能性が具体的になった。想定する移行先はWindowsのWSL2である。ColimaはmacOS専用なので、ADR-0017のDecisionはそのままでは適用できない。一方で、決め手も「依存させない範囲」もOSには依存していない。利用者はプロジェクトオーナー本人のままで、[ADR-0012](0012-private-personal-operation.md)の前提（単一利用者、非公開runtime、データを共有しない）は変更しない。共同開発と第三者への公開は本ADRの対象外である。

移植可能性は`CP-0078`で成果物ごとに確認した。確認日は2026-09-13である。

- 固定した3つのimage digestは、いずれも`linux/amd64`と`linux/arm64`を含むindex manifestだった。
- builder段の`uv sync --locked`をamd64のエミュレーションで実行し、CPython 3.14.7とpsycopg 3.3.5のbinary wheelが入って`import`できることを確認した。runtime段のuser作成もamd64で同じ結果になった。
- `uv.lock`はuniversal resolutionで、manylinux x86_64のwheelを収録している。
- `compose.yaml`のhost依存は、`./docker/postgres/initdb`のbind mount一つと、loopbackへのport公開二つだけだった。
- 壊れたのは改行コードだけだった。CRLFになった初期化scriptを実際のPostgreSQLへ渡すと、`set: pipefail: invalid option name`で初期化が中断し、runtime roleが作られないままcontainerが終了した。dotenv fileのCRLFはComposeが吸収するため影響がなかった。

## Decision

### runtimeの選び方

container runtimeは開発機のOSごとに選ぶ。選定基準は、無償で使える条件が利用者や所属組織の区分に依存しないこととする。基準を満たすもののうち、そのOSで標準的な入れ方ができるものを採る。

| OS | 採用するruntime | 入手 | ライセンス |
| --- | --- | --- | --- |
| macOS | Colima | Homebrew formula（`colima`、`docker`、`docker-compose`） | MIT |
| Windows | WSL2内のDocker Engine（docker-ce） | distributionのpackage | Apache 2.0 |

**固有名詞ではなく基準をDecisionへ置くのは、開発機のOSが一つ増えるたびにADRを置き換えないためである。** ADR-0017は採用したtoolの名前を判断そのものにしたため、Colimaが動かないOSが候補に入った時点で前提を外れた。基準を残しておけば、OSの追加は表とRunbookへの追記で足りる。

### repositoryをruntimeとOSへ依存させない範囲

ADR-0017が定めた4点を引き継ぎ、`CP-0078`で見つかった2点を加える。

- `compose.yaml`はCompose Specificationの範囲で書き、runtime固有のextensionを使わない。
- imageは`linux/amd64`と`linux/arm64`を含むindex manifestのdigestで固定する。単一platformのdigestを固定しない。
- build、起動、test、停止、初期化の手順は`docker compose`で表す。OS固有のコマンドはRunbookの前提条件にだけ置く。
- CIはrunnerに用意されたDocker Engineをそのまま使い、runtimeを別途導入しない。
- repositoryのtext fileは、どのOSでcloneしても作業ツリーでLFにする。`.gitattributes`で強制し、bind mountするfileにCRが無いことをtestで検査する。
- repositoryは、container runtimeがmountできる領域へ置く。Colimaは既定で`$HOME`配下だけをVMへmountし、WSL2では`/mnt/c`ではなくWSL2のfilesystem内に置く必要がある。外れた場合、bind mountが空のdirectoryとして成立してしまい、初期化scriptが実行されないままDBが起動する。

この範囲を守る限り、OSを変えても`compose.yaml`、`Dockerfile`、testは変更せずに済む。

### 検証の分担

WSL2はLinux amd64上のDocker Engineであり、`CP-0061`が使うGitHub-hosted runnerと同じ構成になる。Compose環境のWSL2互換性は、CP-0061のCI jobが継続的に検証する位置づけとする。macOS側はCIに相当するものがないため、Runbookの前提条件へOSごとの最終確認日を記録する。

## Consequences

- 開発機のOSが増えても、判断ではなく表とRunbookの前提条件を足せば済む。
- WSL2側は実機で未確認のまま始まる。最初に使う時点でRunbookの手順を通し、最終確認日を記録する必要がある。
- `.gitattributes`の導入で、以後のcloneは全OSでLFになる。現状のfileはすべてLFのため、正規化による差分は発生しなかった。
- 同じ理由により、Windows固有の改行を必要とするfileをrepositoryへ置けなくなる。現時点で該当するfileはない。
- Docker Desktopを使いたくなった場合は本ADRの基準を外れる。新しいADRで判断する。
- WSL2はCI runnerと同じ構成のため、macOS側の方が検証環境として本番想定から遠い位置になる。

## Alternatives considered

- **ADR-0017のままColimaだけを決め、WSL2は使う時点で都度判断する**: ADRの数は増えない。採らなかったのは、判断基準が文書に残らず、OSが増えるたびに同じ比較をやり直すことになるためである。ADR-0017のValidationが求める「compose定義がruntimeへ依存していないことの証拠」も、OSごとに手順が散ると確認しにくくなる。
- **Windows側でDocker Desktopを使う**: WSL2 backendの導入が最も簡単で、外部情報も多い。採らなかったのは、無償条件が従業員数と年商という組織の区分に紐付き、ADR-0017がColimaを選んだときに避けたはずの判断がそのまま戻るためである。基準に照らして外れる。
- **WSL2を使わずWindowsネイティブで動かす**: Windows containerは採用しているimageと無関係で、Linux containerを動かすにはWSL2かHyper-V VMが要る。WSL2以外を選ぶ理由が見つからない。
- **開発機を1台に固定し、移植を想定しない**: 判断自体が不要になる。採らなかったのは、別マシンへ移る可能性が具体的に示されており、前提にできないためである。
- **devcontainerなどの追加レイヤでOS差を吸収する**: エディタを問わず同じ環境になる。採らなかったのは、`compose.yaml`と並ぶ二つ目の環境定義になるためである。このrepositoryはversionを`pyproject.toml`、検査を`scripts/check.py`、列定義をmigrationへ置くように正を一つに保っており、同じ定義を二重に持たせない。

## Validation

- `CP-0061`で、GitHub-hosted runner上のbuild、起動、health checkが成功することを確認する。これがWSL2構成の継続的な検証を兼ねる。
- 改行コードの不変条件は`tests/unit/test_local_environment.py`が検査する。CRを含むbind mount対象fileがあればCIで失敗する。
- WSL2の実機で初めて使う時点で、[ローカル開発環境Runbook](../runbooks/local-development.md)の手順を通し、最終確認日を記録する。
- 次のいずれかが起きた場合に再評価する。
  - 基準を満たすruntimeが、対象のOSで入手できなくなる。
  - WSL2での実行により、Runbookの共通部分をOSごとに分けざるを得ない差が見つかる。
  - 利用者の追加、repositoryの公開範囲の変更など、[ADR-0012](0012-private-personal-operation.md)の前提が変わる。
