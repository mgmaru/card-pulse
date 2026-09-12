# Card Pulse ロードマップ

> 状態: Active
>
> 最終更新: 2026-09-12
>
> Next task ID: `CP-0076`

この文書は検証と開発の順序を示す。MVPの範囲と完了条件は [MVP定義](mvp.md) を正とする。日々の細かな作業管理を始めた後は、実行タスクをIssue等へ移し、この文書にはフェーズと判断条件を残す。

各タスクはリポジトリ全体で一意なIDと状態を持つ。移動や分割、割り込み時の更新方法は [Roadmap task format](../../.agents/skills/maintain-roadmap/references/task-format.md) に従う。

## Phase 0 — 対象と情報源を決める

- [x] `CP-0001` `done` — 候補となるTCGと店舗を [情報源マップ](../sources/source-map.md) に記録する。
  - Evidence: ポケモンカードゲームと6情報源を[候補一覧](../sources/source-map.md#候補一覧)へ記録し、各個別source文書へリンクした。
- [x] `CP-0002` `done` — URL、形式、更新頻度、カード番号、状態条件、自動取得難易度を確認する。
  - Evidence: [遊々亭](../sources/yuyutei.md#データ形式)、[カードラッシュ](../sources/cardrush.md#データ形式)、[晴れる屋2](../sources/hareruya2.md#データ形式)、[ドラゴンスター](../sources/dragonstar.md#データ形式)、[トレトク](../sources/toretoku.md#データ形式)、[フルコンプ](../sources/fullcomp.md#データ形式)の個別文書に、公開形式、識別項目、価格条件、更新頻度、取得難易度と未確認事項を記録した。
- [x] `CP-0003` `done` — robots.txt、利用規約、アクセス制限、再利用条件、取得間隔を確認し、確認日と根拠URLを記録する。
  - Evidence: 6情報源の[初期比較](../sources/source-map.md#初期比較)と各個別文書の「取得と利用上の制約」に、2026-09-09時点のrobots.txt、規約、自動取得、保存・fixture、取得間隔、根拠URLを記録した。
- [x] `CP-0004` `done` — 代表サンプルを少量だけ確認し、カード識別子と価格条件を抽出できるか比較する。
  - Done when: 各値を原本から直接抽出する値、source metadataまたは取込設定から得る値、欠損可能な値、同定に必要な値へ分類し、同じカードの候補数と価格条件の比較可否を情報源間で記録している。
  - Evidence: 6情報源の値分類、候補衝突、価格条件を[代表サンプル比較](../sources/source-map.md#代表サンプル比較)へ記録し、3情報源で同じカードが各1候補になることと価格条件の差を[同一カード比較](../sources/source-map.md#同一カードの情報源間比較)で確認した。
- [x] `CP-0005` `done` — `1 TCG × 2〜3店舗` を選び、選定理由と見送った候補をADRに残す。
  - Depends on: `CP-0004`
  - Evidence: [ADR-0010](../adr/0010-pokemon-mvp-source-candidates.md)でポケモンカードゲーム、晴れる屋2、遊々亭、フルコンプ池袋店をMVP候補とし、[ADR-0009](../adr/0009-pokemon-mvp-sources.md)を置換した。
- [x] `CP-0070` `cancelled` — 晴れる屋2、遊々亭、フルコンプ池袋店の書面条件と比較可能性を検証する。
  - Depends on: `CP-0005`
  - Done when: 3候補の対象URL、User-Agent、取得頻度、raw artifactと抽出履歴の保持、sanitized fixture、Card Diggerへの派生集計提供、停止・削除条件について、書面回答または回答期限までの経緯がsource文書に記録され、フルコンプ池袋店の代表カードを既存候補と照合して価格条件を比較している。
  - Cancellation reason: [ADR-0011](../adr/0011-no-external-source-inquiries.md)で外部照会を行わない方針へ変更した。公開条件の再確認とフルコンプ池袋店の情報源横断比較はsource文書へ残した。
- [x] `CP-0071` `done` — 3候補の公開条件では採用できない結果を受け、ドラゴンスターの取得安定性と許諾主体を検証し、候補へ加えるか判断する。
  - Done when: robots.txtとCloudflareの挙動、一覧・詳細取得の安定性、価格データの許諾主体、書面確認の窓口、既存候補との同定可能性を確認し、採用、保留、見送りの判断と根拠をsource文書および必要なADRへ記録している。
  - Evidence: [ドラゴンスターの検証](../sources/dragonstar.md#cp-0071の検証)で両hostのrobots.txt、一覧、詳細がCloudflare challengeになること、許諾主体が確定しないこと、既存候補と属性照合できることを記録し、[ADR-0011](../adr/0011-no-external-source-inquiries.md)でMVP候補として見送った。
- [x] `CP-0072` `cancelled` — `CP-0070`と、必要な場合は`CP-0071`の結果から、MVP採用する2〜3店舗を確定する。
  - Depends on: `CP-0070`
  - Done when: 自動取得、保存、fixture、派生集計提供の必要条件を満たす2〜3店舗がMVP採用としてsource文書に記録され、候補構成を変更する場合は新しいADRで決定している。
  - Cancellation reason: 外部照会を行わず、当時の公開条件だけでは必要条件を満たさないため、このタスクの基準では採用しなかった。`CP-0074`で個人・非公開の取得経路へ変更した。
- [x] `CP-0073` `cancelled` — 外部照会を行わずにMVPを検証できる取得経路を決定する。
  - Depends on: `CP-0071`
  - Done when: 必要な利用条件が公開されている情報源と、利用者が権利を持つ手動ファイルまたはsource非由来の合成データを比較し、採用する入力経路、検証できるMVP仮説、原本・fixtureの保存規則をMVP定義とADRへ記録している。
  - Cancellation reason: 公開条件による個別許諾の確認を開発の前提にせず、本人だけが使う非公開Web Collectorへ進む方針に変更した。置換タスクは`CP-0074`。
- [x] `CP-0074` `done` — Card Pulseを個人用の非公開アプリとし、ローカルWeb Collectorの取得経路を確定する。
  - Depends on: `CP-0071`
  - Done when: 単一利用者、非公開runtime、採用情報源と実装順、取得上限、アクセス拒否時の停止、raw artifactとfixtureの保存・非共有境界をMVP定義とADRへ記録している。
  - Evidence: [ADR-0012](../adr/0012-private-personal-operation.md)で個人・非公開のローカル運用、晴れる屋2・遊々亭・フルコンプ池袋店の実装順、取得上限、停止条件、raw artifactとfixtureの保存境界を決定し、[MVP定義](mvp.md)の仮説と完了条件へ反映した。
- [x] `CP-0064` `done` — 次のADR作成時にADR管理の機械検査を導入するか判断する。
  - Done when: ADR ID、状態、日付、必須section、一覧、置換関係を検査するvalidatorを既存の`write-project-docs`とCIへ統合するか、見送る理由を記録する。
  - Evidence: [ADR管理の機械検査](../adr/README.md#adr管理の機械検査)に、現時点で専用validatorを導入しない理由と再検討条件を記録した。
- [x] `CP-0067` `done` — カードの内部主キーと外部識別子の役割を決定する。
  - Evidence: [ADR-0008](../adr/0008-opaque-card-identity-id.md)で、意味を持たない内部UUID、属性による照合、namespace付き外部参照、誤同定の追記型訂正を決定し、データモデルとCollector契約へ反映した。

完了条件: 対象、情報源、取得間隔、利用上の制約が決まり、後続作業が未調査事項で停止しない。

## Phase 1 — 最小の開発基盤を作る

- [x] `CP-0006` `done` — Python version、パッケージ管理、migration手段の決定をADRに残す。
  - Evidence: [ADR-0013](../adr/0013-python-toolchain-and-migrations.md)でCPython 3.14、uvによるproject・lock管理、AlembicによるmigrationとDB選定後に検証する事項を決定した。
- [x] `CP-0007` `done` — 想定データ量、同時接続、整合性、backup・復旧、運用、費用からDB要件を定義する。
  - Evidence: [DB要件](../architecture/database-requirements.md)に、初期・10倍負荷、queryと整合性の合格基準、RPO・RTO、backup世代、権限、保守時間、費用上限、PoC条件、実測後の再評価条件を定義した。
- [x] `CP-0008` `done` — 複数のDB候補を [DB選定の判断軸](../learning/database-selection.md) で比較する。
  - Evidence: [DB候補比較](../research/database-candidate-comparison-2026-09.md#結論)でPostgreSQL、MariaDB、MongoDB、SQLiteを必須条件と8つの判断軸で比較し、PostgreSQL 18.6とMariaDB 12.3.3を`CP-0009`のPoC対象に絞った。BaaSとmanaged hostingはengine選定と別軸として[hosting方式とBaaSの検討](../research/database-candidate-comparison-2026-09.md#hosting方式とbaasの検討)へ記録し、MVPはself-host構成を前提とした。
- [x] `CP-0009` `done` — 上位候補で取込、同時照会、集計、migration、backup・復元のPoCを行う。
  - Evidence: [CP-0009 DB PoC結果](../research/database-poc-2026-09.md#結論)に、PostgreSQL 18.6とMariaDB 12.3.3を1倍（約540万行）と10倍（約4,430万行）で測定した結果を記録した。両候補がPoC合格条件10項目を満たし、追記型保存の権限強制、失敗migrationの部分適用、論理復元時間に差が出た。測定harnessは[`scripts/db_poc/`](../../scripts/db_poc/README.md)にある。
- [ ] `CP-0010` `planned` — DB製品をADRで決定し、ADR-0004の未決事項を解消する。
- [ ] `CP-0011` `planned` — `pyproject.toml`、lockfile、パッケージの最小構成を作る。
- [ ] `CP-0012` `planned` — Docker ComposeでAPI、Worker、選定DB、artifact storageを起動するローカル環境を作る。
- [ ] `CP-0013` `planned` — setup、test、lint、format、型チェックの再現可能なコマンドを定義する。
- [ ] `CP-0014` `planned` — 設定、秘密情報、取得原本、開発用volumeの保存規則を整える。
- [ ] `CP-0015` `planned` — `run_id`、source、開始・終了時刻、取得件数、保存件数、エラー分類を記録するログを定義する。
- [x] `CP-0059` `done` — GitHub Actionsで文書リンクとroadmap形式を継続的に検査する。
  - Evidence: `.github/workflows/ci.yml`でpull requestと`main`へのpushを対象に両方の検査を実行する。
- [ ] `CP-0060` `planned` — format、lint、型チェック、unit testをGitHub Actionsへ追加する。
  - Depends on: `CP-0013`
  - Done when: 対応するPython versionとlockfileを使い、ローカルと同じ品質検査がpull requestで成功する。
- [ ] `CP-0061` `planned` — Docker Composeの設定、image build、service health checkをGitHub Actionsへ追加する。
  - Depends on: `CP-0012`
  - Done when: 空のGitHub-hosted runnerでCompose環境をbuild・起動し、各serviceのhealth checkが成功する。
- [x] `CP-0069` `done` — CodexとClaude Codeの両方で同じエージェント設定が有効になるようにし、乖離をCIで検査する。
  - Depends on: `CP-0059`
  - Evidence: エージェント定義を`.agents/agents/`の中立形式に一本化し、[`maintain-tool-parity`](../../.agents/skills/maintain-tool-parity/SKILL.md)が`.codex/agents/`と`.claude/agents/`を生成する。同Skillの検査スクリプトが生成物の一致、共有Skillのsymlink、`CLAUDE.md`の`@AGENTS.md`取り込みを検証し、CIの`Agent configuration` jobで実行する。
- [ ] `CP-0065` `planned` — ブランチ・PR運用を定義し、作業開始Skillと`main`の保護設定を整える。
  - Depends on: `CP-0059`
  - Done when: [CONTRIBUTING.md](../../CONTRIBUTING.md)をsource of truthとしてSkillが作業ブランチを作成でき、`main`へのマージにpull requestとCI成功が必要になり、ブランチ名CIの導入判断が記録されている。

完了条件: DB選定の根拠がADRに残り、新しい環境で文書どおりにDocker環境を起動し、空DB作成とテスト実行ができる。

## Phase 2 — データ契約と永続化を作る

- [ ] `CP-0068` `planned` — 確定済みの価格観測とカード同定について、再審査、隔離、無効化、置換、復帰の条件と状態遷移を定義する。
  - Depends on: `CP-0004`
  - Done when: 再審査の契機と確定判断、理由・根拠・実行者・規則version、集計対象可否、置換先を追跡する方法が定まり、誤価格、誤同定、parser不具合、重複、復帰の各ケースをtest可能な形でデータモデルまたは契約文書に記録している。
- [ ] `CP-0016` `planned` — [データモデル](../architecture/data-model.md) を実データに合わせて確定する。
  - Depends on: `CP-0068`
- [ ] `CP-0017` `planned` — [Collector契約](../contracts/collector.md) を型として実装する。
  - Done when: 取得port、保存済み原本を処理するport、共通の入出力・失敗型が定義され、domainとapplicationが具体的なsource packageをimportせず、HTTP・DOM・source固有型が境界を越えないことをtestで確認している。
- [ ] `CP-0018` `planned` — 原本メタデータと価格観測値の追記型保存を実装する。
- [ ] `CP-0066` `planned` — processing run、extracted record、observation candidateを追記型で保存し、欠損した解析結果を確定観測と分離する。
  - Depends on: `CP-0016`, `CP-0017`, `CP-0018`
  - Done when: 原本から各中間結果、確定観測またはreviewまで追跡でき、同じ原本の再処理が以前の結果を上書きしない。
- [ ] `CP-0019` `planned` — content hash、情報源内ID、観測値の重複防止規則を決める。
- [ ] `CP-0020` `planned` — 取込、再解析、review確定のtransaction boundaryを定義する。
  - Depends on: `CP-0018`, `CP-0066`
- [ ] `CP-0021` `planned` — DBとartifact storageの片方だけが成功した場合の状態、再実行、孤立データ処理を決める。
- [ ] `CP-0022` `planned` — API、Worker、migration用のDB roleと権限を分ける。
- [ ] `CP-0023` `planned` — 欠損、不正金額、重複、再解析、rollbackのテストを作る。
- [ ] `CP-0062` `planned` — 選定DBを使うmigrationとintegration testをGitHub Actionsへ追加する。
  - Depends on: `CP-0012`, `CP-0023`
  - Done when: 空DBへのmigrationと保存・冪等性・rollbackの検査が本番候補と同じDB engineで成功する。

完了条件: 固定JSON/CSVサンプルを投入し、欠損した抽出結果を確定観測と分離しながら、追跡可能で重複のない観測値を再現できる。

## Phase 3 — ローカルWeb Collectorを縦に通す

- [ ] `CP-0024` `planned` — 最も構造化された情報源で、取得、原本保存、解析、同定、DB保存まで実装する。
  - Depends on: `CP-0074`
  - Done when: URL、request、応答・構造検査、parser、source内IDの解釈が`adapters/sources/<source-slug>/`と所有関係を明示した設定・fixture・testに収まり、entrypointから共通portへ注入され、applicationにsource slugによる処理分岐がない。
- [ ] `CP-0025` `planned` — User-Agent、timeout、低頻度アクセス、backoff、最大再試行、403・429・challenge時の停止をsource設定として定義する。
- [ ] `CP-0026` `planned` — Git管理外のsource由来fixtureとrepository内の合成fixtureを用意し、ネットワークなしでparserをテストする。
  - Depends on: `CP-0074`
- [ ] `CP-0027` `planned` — 実行欠落、通信・応答・構造・データ品質・保存の失敗を段階別に検知し、異常なrunを正常終了または正常な0件にしない。
  - Depends on: `CP-0024`
  - Done when: HTTP成功だけに依存せず、最終URL、media type、source固有の目印、必須構造、件数、必須項目取得率、価格解析率、保存結果を検査し、異常なrunが観測の確定、最終成功日時、鮮度を更新しないことをtestで確認している。
- [ ] `CP-0075` `planned` — source障害の切り分け、停止、保存済み原本からの再解析、検証後の手動再開を実装し、`source-failure` Runbookにする。
  - Depends on: `CP-0025`, `CP-0026`, `CP-0027`
  - Done when: sourceの運用状態、停止理由、直近試行、最終成功日時、失敗段階、診断証拠を確認でき、一つのsourceを停止したまま他sourceの取込を継続し、parser修正後に回帰test、versionを更新した再解析、dry run、差分確認を経て手動再開できる。
- [ ] `CP-0028` `planned` — 2つ目、3つ目の情報源を追加し、共通契約を見直す。
  - Depends on: `CP-0074`, `CP-0075`
  - Done when: 各source packageが相互に依存せず、source固有のURL・応答構造・価格条件の表記と抽出規則が共通HTTP transport、application、domain、永続化、APIへ漏れずに追加でき、共通契約を変更した場合はsource固有事情ではなく共通の意味を追加した根拠を契約文書へ記録している。
- [ ] `CP-0063` `planned` — Collector contract testと固定fixtureによるparser regression testをGitHub Actionsへ追加する。
  - Depends on: `CP-0017`, `CP-0026`, `CP-0027`
  - Done when: source非由来の合成fixtureだけを使い、外部情報源へ接続せずに両方の検査とsource packageの依存境界検査が成功する。source由来fixtureはCIとGitへ含めない。

完了条件: 2〜3店舗のデータが同じ観測モデルに入り、一つの失敗が他へ波及しない。

## Phase 4 — カード同定、相場照会、最小APIを作る

- [ ] `CP-0029` `planned` — TCG、セット、カード番号、レアリティ、版、言語による同定規則を検証する。
- [ ] `CP-0030` `planned` — 原文表記、正規化表記、別名、同定試行、候補と根拠を保存する。
- [ ] `CP-0031` `planned` — 完全一致、自動候補、レビュー必須、未同定を区別する。
- [ ] `CP-0032` `planned` — 最新価格、中央値、最高値、最低値、店舗数、鮮度、スプレッドを計算する。
- [ ] `CP-0033` `planned` — 集計値と根拠観測をCLIまたはJSONで確認できるようにする。
- [ ] `CP-0034` `planned` — API contract、認証、versioning、pagination、エラー形式を定義する。
- [ ] `CP-0035` `planned` — 読取りendpointと書込みendpointを分類し、書込みのidempotencyと同時更新規則を決める。
- [ ] `CP-0036` `planned` — Card Digger等がDBへ直接接続せず、相場と根拠観測を取得できる最小APIを実装する。
- [ ] `CP-0037` `planned` — APIとCollection Workerを別serviceとして起動できることを確認する。

完了条件: 代表カードについて、根拠付きの店舗比較と履歴をAPIから再現できる。

## Phase 5 — 試験運用して価値を判定する

- [ ] `CP-0038` `planned` — 低頻度の増分取得を2〜4週間実行する。
  - Depends on: `CP-0075`
- [ ] `CP-0039` `planned` — 成功率、重複率、未同定率、障害分類、検知・復旧時間、誤検知、レビュー時間、parser変更、保守時間を記録する。
- [ ] `CP-0040` `planned` — 仕入れまたは売却判断に役立った事例を [Experiments](../experiments/README.md) に記録する。
- [ ] `CP-0041` `planned` — 古い価格が新しい価格として表示されず、sourceの停止理由と最終成功日時を確認できることを検証する。
- [ ] `CP-0042` `planned` — API、Worker、DBを別serviceとして本人の端末またはprivate networkへ配置し、API、DB、artifact storageをInternetへ公開しない。
- [ ] `CP-0043` `planned` — 後方互換なschema変更とserviceのdeployment順序をRunbookにする。
- [ ] `CP-0044` `planned` — バックアップと空環境への復元を実施する。
- [ ] `CP-0045` `planned` — 継続、対象変更、中止の判断をADRに残す。

完了条件: 利用価値、維持時間、データ品質を数値と事例で説明できる。

## Phase 6 — 手動画像取込とOCRを検証する

構造化Webだけでは不足すると判明した場合に進む。

- [ ] `CP-0046` `planned` — 画像、店舗、URL、公開日時を一緒に受け取る手動取込を作る。
- [ ] `CP-0047` `planned` — 原画像を先に保存し、OCR結果をextracted recordとして派生関係付きで残す。
  - Depends on: `CP-0066`
- [ ] `CP-0048` `planned` — 項目単位の抽出confidenceとカード同定のmatch scoreを分け、review queueを実装する。
- [ ] `CP-0049` `planned` — 誤認識率と1枚あたりのレビュー時間を測る。

完了条件: 人間の修正時間を含め、手入力より有利か判断できる。

## Phase 7 — X取得を判断する

X限定情報の利益が取得・保守コストを上回る場合だけ進む。

- [ ] `CP-0050` `planned` — Webとの重複率、X限定情報数、判断への寄与、月間件数を測る。
- [ ] `CP-0051` `planned` — 公式APIの料金、rate limit、利用規約をその時点で再確認する。
- [ ] `CP-0052` `planned` — 公式API、手動取込、非公式取得の費用・規約・停止リスク・保守時間を比較してADRに残す。
- [ ] `CP-0053` `planned` — X固有コードを交換可能なsource adapter内に閉じ込める。
- [ ] `CP-0054` `planned` — 取得停止後も保存済みデータと他の機能を利用できることを確認する。

完了条件: 採用理由、運用制約、撤退条件が明文化されている。

## Phase 8 — Card Diggerと連携する

相場データの有用性を確認した後に進む。

- [ ] `CP-0055` `planned` — Card Diggerのユースケースから必要な問い合わせを定義する。
- [ ] `CP-0056` `planned` — カード識別子、曖昧一致、鮮度、欠損時の応答を決める。
- [ ] `CP-0057` `planned` — Phase 4で作成したAPI contractをCard Diggerの実利用に合わせて拡張する。
- [ ] `CP-0058` `planned` — 中央値、店舗数、鮮度、ばらつき、根拠観測をCard Diggerが正しく評価できることを確認する。

完了条件: 本人が管理するCard Diggerが内部DBへ依存せず、非公開APIから根拠付き価格情報を取得できる。
