# Card Pulse ロードマップ

> 状態: Active
>
> 最終更新: 2026-09-07
>
> Next task ID: `CP-0066`

この文書は検証と開発の順序を示す。MVPの範囲と完了条件は [MVP定義](mvp.md) を正とする。日々の細かな作業管理を始めた後は、実行タスクをIssue等へ移し、この文書にはフェーズと判断条件を残す。

各タスクはリポジトリ全体で一意なIDと状態を持つ。移動や分割、割り込み時の更新方法は [Roadmap task format](../../.agents/skills/maintain-roadmap/references/task-format.md) に従う。

## Phase 0 — 対象と情報源を決める

- [ ] `CP-0001` `planned` — 候補となるTCGと店舗を [情報源マップ](../sources/source-map.md) に記録する。
- [ ] `CP-0002` `planned` — URL、形式、更新頻度、カード番号、状態条件、自動取得難易度を確認する。
- [ ] `CP-0003` `planned` — robots.txt、利用規約、アクセス制限、再利用条件、取得間隔を確認し、確認日と根拠URLを記録する。
- [ ] `CP-0004` `planned` — 代表サンプルを少量だけ確認し、カード識別子と価格条件を抽出できるか比較する。
- [ ] `CP-0005` `planned` — `1 TCG × 2〜3店舗` を選び、選定理由と見送った候補をADRに残す。
- [ ] `CP-0064` `planned` — 次のADR作成時にADR管理の機械検査を導入するか判断する。
  - Done when: ADR ID、状態、日付、必須section、一覧、置換関係を検査するvalidatorを既存の`write-project-docs`とCIへ統合するか、見送る理由を記録する。

完了条件: 対象、情報源、取得間隔、利用上の制約が決まり、後続作業が未調査事項で停止しない。

## Phase 1 — 最小の開発基盤を作る

- [ ] `CP-0006` `planned` — Python version、パッケージ管理、migration手段の決定をADRに残す。
- [ ] `CP-0007` `planned` — 想定データ量、同時接続、整合性、backup・復旧、運用、費用からDB要件を定義する。
- [ ] `CP-0008` `planned` — 複数のDB候補を [DB選定の判断軸](../learning/database-selection.md) で比較する。
- [ ] `CP-0009` `planned` — 上位候補で取込、同時照会、集計、migration、backup・復元のPoCを行う。
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
- [ ] `CP-0065` `planned` — ブランチ・PR運用を定義し、作業開始Skillと`main`の保護設定を整える。
  - Depends on: `CP-0059`
  - Done when: [CONTRIBUTING.md](../../CONTRIBUTING.md)をsource of truthとしてSkillが作業ブランチを作成でき、`main`へのマージにpull requestとCI成功が必要になり、ブランチ名CIの導入判断が記録されている。

完了条件: DB選定の根拠がADRに残り、新しい環境で文書どおりにDocker環境を起動し、空DB作成とテスト実行ができる。

## Phase 2 — データ契約と永続化を作る

- [ ] `CP-0016` `planned` — [データモデル](../architecture/data-model.md) を実データに合わせて確定する。
- [ ] `CP-0017` `planned` — [Collector契約](../contracts/collector.md) を型として実装する。
- [ ] `CP-0018` `planned` — 原本メタデータと価格観測値の追記型保存を実装する。
- [ ] `CP-0019` `planned` — content hash、情報源内ID、観測値の重複防止規則を決める。
- [ ] `CP-0020` `planned` — 取込、再解析、review確定のtransaction boundaryを定義する。
- [ ] `CP-0021` `planned` — DBとartifact storageの片方だけが成功した場合の状態、再実行、孤立データ処理を決める。
- [ ] `CP-0022` `planned` — API、Worker、migration用のDB roleと権限を分ける。
- [ ] `CP-0023` `planned` — 欠損、不正金額、重複、再解析、rollbackのテストを作る。
- [ ] `CP-0062` `planned` — 選定DBを使うmigrationとintegration testをGitHub Actionsへ追加する。
  - Depends on: `CP-0012`, `CP-0023`
  - Done when: 空DBへのmigrationと保存・冪等性・rollbackの検査が本番候補と同じDB engineで成功する。

完了条件: 固定JSON/CSVサンプルを投入し、追跡可能で重複のない観測値を再現できる。

## Phase 3 — Web Collectorを縦に通す

- [ ] `CP-0024` `planned` — 最も構造化された情報源で、取得、原本保存、解析、同定、DB保存まで実装する。
- [ ] `CP-0025` `planned` — User-Agent、timeout、低頻度アクセス、backoff、最大再試行をsource設定として定義する。
- [ ] `CP-0026` `planned` — 保存が許される固定fixtureを用意し、ネットワークなしでparserをテストする。
- [ ] `CP-0027` `planned` — 0件、必須項目欠損、件数急減を正常終了にしない検知を作る。
- [ ] `CP-0028` `planned` — 2つ目、3つ目の情報源を追加し、共通契約を見直す。
- [ ] `CP-0063` `planned` — Collector contract testと固定fixtureによるparser regression testをGitHub Actionsへ追加する。
  - Depends on: `CP-0017`, `CP-0026`
  - Done when: 保存と再利用が許可されたfixtureだけを使い、外部情報源へ接続せずに両方の検査が成功する。

完了条件: 2〜3店舗のデータが同じ観測モデルに入り、一つの失敗が他へ波及しない。

## Phase 4 — カード同定、相場照会、最小APIを作る

- [ ] `CP-0029` `planned` — TCG、セット、カード番号、レアリティ、版、言語による同定規則を検証する。
- [ ] `CP-0030` `planned` — 原文表記、正規化表記、別名、同定状態を保存する。
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
- [ ] `CP-0039` `planned` — 成功率、重複率、未同定率、レビュー時間、parser変更を記録する。
- [ ] `CP-0040` `planned` — 仕入れまたは売却判断に役立った事例を [Experiments](../experiments/README.md) に記録する。
- [ ] `CP-0041` `planned` — 古い価格が新しい価格として表示されないことを確認する。
- [ ] `CP-0042` `planned` — API、Worker、DBを別serviceとして試験環境へ配置し、DBとartifact storageを外部公開しない。
- [ ] `CP-0043` `planned` — 後方互換なschema変更とserviceのdeployment順序をRunbookにする。
- [ ] `CP-0044` `planned` — バックアップと空環境への復元を実施する。
- [ ] `CP-0045` `planned` — 継続、対象変更、中止の判断をADRに残す。

完了条件: 利用価値、維持時間、データ品質を数値と事例で説明できる。

## Phase 6 — 手動画像取込とOCRを検証する

構造化Webだけでは不足すると判明した場合に進む。

- [ ] `CP-0046` `planned` — 画像、店舗、URL、公開日時を一緒に受け取る手動取込を作る。
- [ ] `CP-0047` `planned` — 原画像を先に保存し、OCR結果を派生データとして残す。
- [ ] `CP-0048` `planned` — 項目単位のconfidenceとreview queueを実装する。
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

完了条件: Card Diggerが内部DBへ依存せず、根拠付き価格情報を取得できる。
