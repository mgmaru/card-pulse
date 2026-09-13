# ADR-0022: 設定を環境変数、秘密情報を`.env`、ローカルデータを`var/`へ集約する

- 状態: Accepted
- 日付: 2026-09-13
- 決定者: プロジェクトオーナー
- 置換するADR: なし
- 置換されたADR: なし

## Context

保存に関する規則は、これまで判断のたびに別々の文書へ書かれてきた。[ADR-0012](0012-private-personal-operation.md)はGitとCIへ入れないものを、[ADR-0016](0016-local-compose-artifact-volume.md)は取得原本の物理配置を、[ADR-0003](0003-mvp-local-storage.md)（Superseded）は`var/`の層を決めている。実際の除外は`.gitignore`、ディレクトリの説明は[README](../../README.md)のtreeにあり、`src/card_pulse/entrypoints/settings.py`のdocstringは「設定と秘密情報の保存規則は`CP-0014`で決める」と保留したままだった。

そのため、新しいfileをどこへ置くかを決めるときに読む場所が定まらない。設定値を環境変数で渡すのか設定fileにするのか、秘密をどこに置いてよいのか、Git管理外の領域をいつ消してよいのかが、いずれも明示されていない。

保留のあいだに、決めるべき対象が増えている。

- `CP-0061`でCIがCompose環境を起動するようになり、秘密の出どころが本人の開発機だけではなくなった。CIは`.env.example`から実行ごとの値を作り、runnerとともに破棄する。
- `CP-0009`のPoCが残した`var/db-poc/`が、2026-09-13時点で35GBある。中に`secret/backup.passphrase`が含まれており、`.env`の外にある唯一の秘密になっている。保持と削除の条件は決まっていない。
- `config/`はGit管理下で空のまま置かれ、[アーキテクチャ概要](../architecture/overview.md#情報源adapterの境界)がsource固有の実行設定の置き場と位置づけている。

## Decision

### 設定の入口は環境変数だけにする

application processが読む設定は環境変数に限る。`settings.py`が唯一の読み取り口で、必須値が欠けていれば起動時に失敗する。`.env`はComposeと人が環境変数へ変換するためのfileであり、processが直接読むfileではない。

**設定fileを読む経路を足すと、同じ値が環境変数とfileの二か所から来る状態が生まれ、どちらが勝つかをcomponentごとに決めることになる。** 開発機、Compose、CI、将来の配置で同じimageを動かす以上、値の出所を追うときに読む場所は`.env`と`compose.yaml`の二つに留める。

source固有の実行設定（`CP-0025`が定めるUser-Agent、間隔、再試行など）は`config/`へ置く。これはrepositoryが持つ非秘密の値で、entrypointが読んでadapterへ渡す。秘密は置かない。

### 秘密情報は`.env`だけに置く

- 秘密の置き場はGit管理外の`.env`ひとつとする。`.env.example`は変数名だけを持ち、値を持たない。
- CIは実行ごとに値を生成し、runnerの破棄とともに捨てる（`CP-0061`）。GitHubのsecretへ登録しない。
- 秘密をlog、heartbeat、artifact、CIの出力へ書かない。接続文字列を例外にしない。
- `var/`とrepositoryへ新しい秘密を作らない。

**秘密の置き場が複数あると、漏えいしていないことの確認が置き場の数だけ必要になり、後から増えた一か所を見落とす。** 置き場を一つに固定すれば、検査は「`.env`以外に秘密が無いか」だけで済む。

既存の例外は`var/db-poc/secret/backup.passphrase`の1件で、PoCが作った暗号化backupを開くためのものである。新しい秘密をそこへ足さず、`var/db-poc/`を削除するときに一緒に消す。

### ローカルデータは`var/`へ集め、層ごとに役割を固定する

`var/`はGit管理外の唯一のローカルデータ領域とし、`.gitkeep`以外を追跡しない。

| 層 | 置くもの | 書くもの |
| --- | --- | --- |
| `var/raw/` | 取得原本のhost側copy。host直接実行時のartifact rootの既定 | `docker compose cp`、host実行のWorker |
| `var/logs/` | 実行ログとWorkerのheartbeat（host実行時の既定） | host実行のWorker |
| `var/db/` | DBのdumpと復元の作業領域 | 人。最初の利用者は`CP-0044`のbackup・復元 |
| `var/review/` | review対象の作業データ | Phase 4のreview（`CP-0031`ほか） |
| `var/db-poc/` | `CP-0009`のPoC測定データ | 凍結。新しく書かない |

Compose環境における取得原本の正はnamed volume `artifacts`であり（[ADR-0016](0016-local-compose-artifact-volume.md)）、`var/raw/`はそこから取り出したcopyである。両者が食い違った場合はvolume側を正とする。

現時点で書き込むcomponentが無い`var/db/`と`var/review/`も残す。**層を消して減るのは空のディレクトリ一つだけで、代わりに次に必要になったときへ置き場の判断を先送りすることになる。**

### PoCデータは保持し、削除できる条件を明示する

`var/db-poc/`は保持する。**35GBを消して戻るのは容量だけだが、`CP-0009`の結論に疑いが生じたときに同じ入力で再確認する手段は戻らない。** 測定結果は[PoC結果](../research/database-poc-2026-09.md)に、harnessは`scripts/db_poc/`に凍結されているため、結論の追跡自体はこのデータが無くてもできる。

次のいずれかの時点で`rm -rf var/db-poc`により削除してよい。削除しても文書の根拠は失われない。

- 開発機のディスクが不足し、容量が必要になったとき。
- `CP-0009`の結論を置き換えるADRが出て、同じ入力での再確認が不要になったとき。
- `CP-0024`以降に取得原本が増え、`var/`の実容量を見直したとき。

## Consequences

- 新しいfileの置き場を決めるときに読む文書がこのADR一つになる。個別の物理配置は引き続き[ADR-0016](0016-local-compose-artifact-volume.md)、公開してよい範囲は[ADR-0012](0012-private-personal-operation.md)が正である。
- `tests/unit/test_storage_layout.py`が、`var/`と`config/`に`.gitkeep`以外の追跡fileが無いこと、`.env`と`var/`配下のデータが`.gitignore`で除外されること、runtimeの既定書き込み先が`var/`配下であることを検査する。CIの`Quality checks`が毎回実行する。
- 秘密を増やすときは`.env`へ値を、`.env.example`へ変数名だけを足す。設定fileやsecret storeを足す構成が必要になった場合は、このADRを置き換える。
- `var/db-poc/`の35GBは当面残る。削除は上の条件に当たった時点で、本人が実行する。
- `config/`は`CP-0025`まで空のまま残る。

## Alternatives considered

- **設定fileを読めるようにする（YAML、TOML）**: 値をまとめて見通せるが、環境変数との優先順位をcomponentごとに持つことになり、値の出所を追う場所が増える。非秘密のsource設定は`config/`で足りる。
- **秘密をOS keychainやsecret managerへ置く**: 漏えい時の影響は下がるが、読む主体が本人の開発機とCI runnerの両方になり、経路が`.env`一つより増える。利用者が本人だけでrepositoryもprivate networkも本人の管理下にある現状では、増えた経路の分だけ見落としが増える。
- **`var/db/`と`var/review/`を削除する**: 空の層が減るが、次に使う工程（`CP-0044`、Phase 4のreview）が決まっているため、そのときに置き場の判断をやり直すことになる。
- **PoCデータを削除する**: 35GB戻るが、結論に疑いが生じたときの再確認手段が消える。容量が不足していない時点で選ぶ理由がない。
- **取得原本のhost側copyを持たない**: 原本をvolumeの中だけに置けば経路は一つになるが、[ADR-0012](0012-private-personal-operation.md)が本人のローカル環境だけで認めるsource由来fixtureのparser regression testを、hostから実行できなくなる。

## Validation

- 上の機械検査が失敗しない状態を保つ。規則を破るfileを追加した場合に検査が落ちることを`CP-0014`で確認する。
- Gitとgit履歴へ秘密、取得原本、価格履歴が入っていないことは、`CP-0080`で使った全履歴の走査で再確認できる。
- `CP-0024`で取得原本が実際に増えた時点で、`var/`の実容量と層の使われ方を確認し、保持方針と`var/db-poc/`の削除条件を見直す。
