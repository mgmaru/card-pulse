# Card Pulse DB要件

> 状態: Active
>
> 最終更新: 2026-09-12
>
> 対象: MVPの構造化データを保存するserver型DB

## 目的

この文書は、Card PulseがDBへ要求する容量、同時実行、整合性、backup・復旧、運用、security、費用の基準を定める。`CP-0008`では候補の必須条件と比較基準として使い、`CP-0009`では同じ負荷と合格条件でPoCを行った。製品とhosting方式は[ADR-0014](../adr/0014-postgresql-self-hosted.md)でself-hostのPostgreSQL 18に決定し、この文書は採用後も要求水準と再評価条件の正であり続ける。

## 前提と数値の扱い

Card Pulseはプロジェクトオーナー本人だけが使う非公開システムである。MVPではポケモンカードゲームを対象に、晴れる屋2、遊々亭、フルコンプ池袋店をsourceごとに逐次、日次1回以下で取得し、手動取込を1系統持つ。API、Collection Worker、DBは別serviceとして動き、clientはAPIだけを利用する。構造化データは一つの論理DBに保存し、raw artifact本体は別のartifact storageに置く。

原本、処理実行、抽出結果、観測候補、同定試行、review、確定観測は追記型で保持する。したがって、DB負荷は`price_observation`の件数だけでは見積もらず、再解析を含む処理段階ごとの行数で評価する。これらの前提は[MVP定義](../product/mvp.md)、[アーキテクチャ概要](overview.md)、[データモデル](data-model.md)、[ADR-0007](../adr/0007-layered-ingestion-data.md)を正とする。

現在は全sourceを一巡した実測件数、行byte数、index比率、再解析倍率がない。この文書の件数、応答時間、RPO、RTO、費用、保守時間は、候補を同じ条件で比較するための初期基準であり、運用実績を装った値ではない。最初のsourceを実装した後と2〜4週間の試験収集後に実測値との差を記録し、基準を変更する場合は理由と影響をこの文書へ残す。

## データ量と保持

### 初期負荷プロファイル

[晴れる屋2の2026-09-11確認](../sources/hareruya2.md#データ形式)では全件JSONが約8.79 MBであり、残り2 sourceは対象ページ数と行数を実装前に確定できない。この不確実性を吸収するため、PoCでは次の保守的な負荷を「1倍」とする。件数はdomain上の上限ではなく、容量と性能を比較するための生成データ件数である。

| 処理段階 | 1日あたりの初期基準 | 28日分 | 算定上の仮定 |
| --- | ---: | ---: | --- |
| `raw_artifact` metadata | 500 | 14,000 | 原本本体は含めず、DB内のmetadataだけを数える |
| `extracted_record` | 30,000 | 840,000 | 3 sourceと手動取込を一巡した抽出行 |
| `observation_candidate` | 30,000 | 840,000 | 全抽出行が候補へ進む保守的な上限 |
| `identity_resolution_attempt` | 60,000 | 1,680,000 | 1候補につき平均2候補を検討する仮定 |
| `price_observation` | 30,000 | 840,000 | 全候補が確定する保守的な上限 |
| `review_item` | 3,000 | 84,000 | 抽出行の10%がreviewを生む仮定 |

28日分は主要な追記型データで約430万行になる。`source`、`shop`、`ingest_run`、`processing_run`、`card_identity`、外部参照、状態変更履歴等も容量へ含めるが、上表では件数の小さい補助行として省略している。10倍プロファイルはすべての件数を10倍した約4,300万行とし、source追加、再解析、対象拡大時の余裕を確認する。

### 容量要件

| ID | 要件 |
| --- | --- |
| `DB-CAP-01` | 構造化された履歴とprovenanceを最低3年間onlineで保持できること。MVP中は自動削除せず、3年経過後もarchive・削除規則を別途決定するまで証拠を削除しないこと。 |
| `DB-CAP-02` | 初期負荷プロファイルを28日分投入した状態と、その10倍の状態について、table、index、DB内部log、backupの実容量を測定できること。 |
| `DB-CAP-03` | 3年間の必要容量は、source別の実測日次行数、段階別の平均row byte、index比率、再解析倍率から算出し、算出値に50%の空き容量を加えて計画すること。raw artifact本体はDB容量へ含めず、artifact metadataと参照は含めること。 |
| `DB-CAP-04` | 通常日1日分の30,000抽出行と派生行を10分以内にcommitでき、API相当の読取りを同時に継続できること。28日分の全再解析相当を8時間以内に追記できること。外部HTTP待ちやartifact I/O中はDB transactionを保持しないこと。 |
| `DB-CAP-05` | storage使用率70%で警告、85%でcriticalを検知できること。実測値が初期基準の2倍を2回連続で超える、3年予測が計画容量の70%を超える、または月額上限を超える場合は、容量、index、partition、archive、hosting方式を再評価すること。 |

## 接続、同時実行、query

通常構成ではAPIのconnection poolを最大5、Workerを最大2、migration・backup・運用を合計最大3とし、DB全体の利用上限を10 connectionに収める。候補DBは少なくとも20 active connectionを安定して扱い、将来は設定変更または同一製品内のscaleで50 connectionまで拡張できること。migrationは通常のAPI・Workerと同時に無計画に実行せず、専用roleと明示した保守時間で行う。

`CP-0009`では、8並行readerと2 writerを同時に実行する。通常の定期取得は1 writerだが、再解析または手動取込との競合と、同じ冪等入力を2 writerが同時に投入する場合を検証する。

| ID | 代表query | 1倍プロファイルでの合格基準 |
| --- | --- | ---: |
| `DB-QRY-01` | 1カードの最新価格、中央値、最高値、最低値、店舗数、鮮度 | p95 200 ms以内 |
| `DB-QRY-02` | 最大100カードの最新価格と集計 | p95 1秒以内 |
| `DB-QRY-03` | 1カードの1年分の履歴を取得日時順に最大1,000件返す | p95 500 ms以内 |
| `DB-QRY-04` | 集計結果または観測からcandidate、processing run、artifact metadataまで追跡する | p95 200 ms以内 |
| `DB-QRY-05` | 未処理review itemを優先順に100件返す | p95 200 ms以内 |

時間はDB内の実行時間を測り、同時writerが動く状態で判定する。PoCでは28日分の広いデータ分布に加え、代表カードには1年分の履歴を生成する。使用hardware、DB設定、データ分布、cold/warm cache、実行計画を記録し、合格判定は同じqueryを一度実行した後のwarm cacheで行い、cold cacheの値も比較資料として残す。結果集合が大きいqueryには安定した並び順とpaginationを要求し、全履歴を無制限にmemoryへ読み込まない。

## 整合性とtransaction

| ID | 要件 |
| --- | --- |
| `DB-INT-01` | ACID transaction、foreign key、`NOT NULL`、`CHECK`、複合`UNIQUE`または同等の一意性制約を持ち、constraint違反をapplicationが機械的に判別できること。 |
| `DB-INT-02` | 金額、通貨、価格種別、shop、TCG、取得日時、artifact参照、確定済みcard identityを欠く結果を`price_observation`としてcommitできないこと。価格0は欠損と区別し、有効な整数値として保存できること。 |
| `DB-INT-03` | 同じ冪等入力を逐次または2 writerから同時に投入しても、確定観測が1件だけになること。具体的な冪等keyは`CP-0019`で決定する。 |
| `DB-INT-04` | APIの一つの応答を構成する複数queryが同じ`as_of`の一貫したsnapshotを読めること。dirty readを許さず、通常の読取りが長時間writerを停止させないこと。採用するisolation levelと再試行規則は実装時に記録すること。 |
| `DB-INT-05` | reviewを2 sessionが同時に確定しようとした場合に、row lock、version比較、条件付きupdate等で競合を検知し、一方だけが成功すること。 |
| `DB-INT-06` | deadlock、serialization failure、lock timeout、connection failureを区別でき、未commitのtransaction全体を安全に再試行または失敗として扱えること。 |
| `DB-INT-07` | 原本、処理結果、同定判断、review判断、確定観測の履歴を追記型で保持し、訂正と再解析を新しい履歴として表現できること。通常runtime roleが証拠履歴を無制限に`UPDATE`または`DELETE`できない権限制御を持つこと。 |
| `DB-INT-08` | UUID、timezone付き日時、整数の最小通貨単位、source固有metadataを意味を失わず格納できること。DB固有型を使う場合はlogical export時の変換方法を記録すること。 |

具体的な重複防止key、取込・再解析・review確定のtransaction boundary、状態遷移は`CP-0019`と`CP-0020`で決める。このタスクでは、どの境界を選んでも上表の結果を保証できるDB機能を要求する。

DBとartifact storageを一つの分散transactionで更新する機能は要求しない。artifact本体の保存成功後にDB metadataを確定し、片方だけが成功した状態を検知して再実行または孤立データ処理へ進める必要がある。具体的な状態と回復手順は`CP-0021`で決定する。

## Backup、復旧、可用性

| ID | 要件 |
| --- | --- |
| `DB-REC-01` | RPOは24時間以内とする。1日1回のbackupに加え、schema migration、大量手動取込、重要なreview作業の前に臨時backupを取得すること。backup失敗または前回成功から26時間超過を検知すること。 |
| `DB-REC-02` | RTOはDBが利用不能になってから24時間以内とする。DBの空環境へのrestoreと整合検証は2時間以内、API・Workerの接続確認とartifact参照検証を含む復旧作業全体は開始から8時間以内を目標とすること。 |
| `DB-REC-03` | 暗号化した日次backupを7世代、週次backupを4世代保持すること。migration前backupは変更後の検証完了から30日まで保持すること。 |
| `DB-REC-04` | backupはDBのdata volumeと別の障害領域にある、本人が管理する非公開保存先へ置くこと。provider snapshotだけに依存せず、同じDB engineの空環境へ復元できるlogical backupまたは同等の可搬なbackupを持つこと。 |
| `DB-REC-05` | 一つのbackup setに基準時刻、DB backup、migration revision、artifact manifest、各fileのchecksumを記録すること。MVPではbackup中にWorkerを停止して整合点を作る方法を許容する。秘密情報と暗号鍵をmanifestへ含めないこと。 |
| `DB-REC-06` | restore後にentity別件数、constraint、代表レコードのhash、全DB参照に対応するartifactの存在を検査すること。余分な孤立artifactは回復処理の対象にできるが、DBから参照するartifactの欠落を正常復旧として扱わないこと。 |
| `DB-REC-07` | MVP試験収集の開始前に空環境へのrestoreを1回実測し、その後は3か月ごと、およびDB engine・major version・hosting・backup方式の変更時に復元訓練を行うこと。破損backupと暗号鍵不一致を成功として扱わないこと。 |

MVPではsingle primaryで開始し、replica、自動failover、複数region、24時間のon-call、稼働率SLAを必須にしない。point-in-time recoveryは比較上の利点として記録するが、RPOを日次backupで満たせる間は必須条件にしない。一つのsourceやWorkerが停止してもDBとAPIが保存済みデータを読めることは、DBのreplicaではなくserviceと処理の分離で保証する。

## Securityと権限

| ID | 要件 |
| --- | --- |
| `DB-SEC-01` | DB portをInternetへ公開しないこと。同一hostではCompose内部network、hostをまたぐ場合は認証済みprivate networkとserver証明書を検証するTLSを使うこと。 |
| `DB-SEC-02` | API、Worker、migration、backup・export、管理者を別roleと別credentialに分離できること。APIは原則read-only、Workerは必要な読取り・追記・状態遷移、migrationだけがDDLを実行できること。具体的なgrantは`CP-0022`で決定する。 |
| `DB-SEC-03` | DB data volume、transaction log、backup、snapshotを保存時暗号化の対象にすること。本人のローカル端末ではOSまたはvolumeの暗号化で満たしてよい。 |
| `DB-SEC-04` | credentialをrepository、container image、log、backup manifestへ保存せず、role単位で他roleを止めずにrotationできること。 |
| `DB-SEC-05` | 接続、認証失敗、role・権限変更、DDL、backup、restoreを30日間確認できること。価格値を含む全SQL statementの常時記録は要求しない。 |

`DB-SEC-01`が指すloopback、Compose内部network、LAN、認証済みprivate networkの違いは[private networkの種類と使い分け](../learning/private-network-types.md)を参照する。

## 運用と費用

| ID | 要件 |
| --- | --- |
| `DB-OPS-01` | vendorまたはcommunityがsecurity updateを提供するsupported versionを使い、major version、driver、dialectを固定してDocker Composeと実行環境でそろえられること。 |
| `DB-OPS-02` | backup成否、storage、connection使用率、5秒超のlock待ち、60秒超のtransaction、slow query、DB再起動、replicationを採用した場合はその遅延を観測できること。connection使用率70%で警告すること。 |
| `DB-OPS-03` | 通常のbackup確認、容量・接続・slow query確認、minor updateを含む定常DB保守を月1時間以内に収めること。初期構築、四半期の復元訓練、schema変更、実障害対応は別に計測すること。 |
| `DB-OPS-04` | 月1回、最大2時間の計画停止を許容する。security update、major upgrade、credential rotation、backup・restore、障害対応を再現可能な手順として残せること。 |
| `DB-COST-01` | 1倍の日次負荷を3年間保持する予測構成について、DB compute、構造化storage、DB backup、network転送、monitoringに起因する月額増分費用を3,000円以内にすることを目標とし、5,000円を暫定上限とすること。raw artifact storageの費用は別に記録すること。 |
| `DB-COST-02` | 既存hardwareを使う場合も無料とせず、割当disk、電力、backup保存先、更新作業を分けて記録すること。候補ごとに初年度と3年目の月額、初期構築時間、定常保守時間、復元訓練時間を比較すること。 |

すべての候補が費用上限を超える場合は、必須の整合性や復旧を省略して製品を決めず、負荷プロファイル、hosting方式、費用上限のどれを変えるかをプロジェクトオーナーが判断し、`CP-0010`のADRへ記録する。

## 開発環境とmigration

- 同じDB engineとmajor versionをDocker Composeで実行し、CIで同じdialectのintegration testを行えること。
- Alembicに保守されたdialectとdriverがあり、空DBへの`upgrade head`、既存schemaのupgrade、offline SQL生成、失敗時の挙動を確認できること。
- APIやWorkerの起動時にmigrationを暗黙実行せず、専用entrypointとroleから適用できること。
- testごとにschemaまたはDBを分離して初期化でき、transaction、日時、JSON、constraintの意味を本番候補と同じengineで検証できること。
- standardな形式へのlogical exportを行い、DB固有の型、関数、index、extensionへの依存を一覧化できること。

## 候補の必須条件

`CP-0008`では、次のいずれかを満たさない候補を点数比較だけで採用しない。

1. 別serviceのAPIとWorkerがprivate networkからserver接続できる。
2. `DB-INT-01`から`DB-INT-08`までの整合性と追記型履歴を実装できる。
3. 1倍プロファイルを保持し、代表queryと同時実行の合格基準を満たす現実的な構成を提示できる。
4. RPO、RTO、世代保持、空環境への復元、artifact照合を満たせる。
5. role分離、非公開network、credential rotation、保存時暗号化を満たせる。
6. 同じengineをDocker ComposeとCIで使い、Alembic migrationを検証できる。
7. 1倍の日次負荷を3年間保持する予測構成の月額増分費用が暫定上限内に収まる。

## CP-0009のPoC合格条件

候補ごとに同じgenerator、schema、query、測定方法を使い、少なくとも次を確認する。

1. 空DBと既存schemaへAlembic migrationを適用し、失敗時に未完了の状態を識別する。
2. 1倍と10倍の28日プロファイルについて、table、index、log、backupの容量と投入時間を記録する。
3. 8 readerと2 writerで代表queryのp95、書込み時間、lock待ち、deadlock、connection使用数、実行計画を測る。
4. 同一入力を逐次および同時に再投入し、確定観測が重複しないことを確認する。
5. transactionの途中でconstraint違反、process停止、DB再起動を発生させ、未commitの部分行が残らず、commit済み行が再起動後も残ることを確認する。
6. 一貫した`as_of`の最新値・集計、履歴、provenance追跡、review競合を確認する。
7. 後方互換なschema変更中に旧queryと新queryを実行し、migrationのlock時間とrollbackまたはbackup復元の境界を記録する。
8. DB backupとartifact manifestを作り、元DBを使わない空環境へ復元して、件数、constraint、hash、artifact参照を検査する。
9. API roleの書込み、Worker roleのDDL・証拠履歴削除、外部networkからの接続が拒否されることを確認する。
10. 1倍と10倍について月額費用、初期構築時間、定常保守時間、復元訓練時間を記録する。

## 再評価条件

次のいずれかが起きた場合は、この文書の初期基準とDB選定を見直す。

- 実測した段階別日次件数、row byte、index比率、再解析倍率が初期負荷プロファイルを継続的に超える。
- 保存量、query p95、batch時間、connection、lockが警告値を超え、indexまたは同一製品内のscaleで解消できない。
- RPO、RTO、backup保持、restore時間、artifact照合を満たせない。
- 月額増分費用が5,000円、または定常DB保守が月1時間を継続的に超える。
- source、TCG、利用者、API instance、Workerを増やす、Internet公開する、または第三者へデータを提供する。
- 3年間のonline保持を満たす前にarchiveまたは削除が必要になる。

## 関連文書

- [MVP定義](../product/mvp.md)
- [アーキテクチャ概要](overview.md)
- [データモデル](data-model.md)
- [DB選定の判断軸](../learning/database-selection.md)
- [ADR-0004: server型DBと製品選定](../adr/0004-server-database-selection.md)
- [ADR-0007: 処理段階による構造化データの分離](../adr/0007-layered-ingestion-data.md)
- [ADR-0012: 個人用の非公開運用](../adr/0012-private-personal-operation.md)
- [ADR-0013: Python toolchainとmigration](../adr/0013-python-toolchain-and-migrations.md)
