# Card Pulseへの変更

Card Pulseは現在、情報源とMVPの成立性を確認する段階です。実装量より、取得データを再現・追跡できることを優先します。

## 変更前に確認する文書

1. [プロダクト構想](docs/product/vision.md)
2. [MVP定義](docs/product/mvp.md)
3. 変更対象に関係する [ADR](docs/adr/README.md)
4. Collector変更の場合は [Collector契約](docs/contracts/collector.md) と対象のsource文書

## ブランチとpull request

この節をブランチ・マージ運用のsource of truthとします。手順の実行は [`start-task`](.agents/skills/start-task/SKILL.md) Skillが担い、`main` の保護設定がこの規則を強制します。

### 作業ブランチ

- `main` へ直接コミットしません。変更は必ず作業ブランチで行います。
- ブランチ名は `cp-<タスクID>-<要約>` とします。要約は英小文字のkebab-caseです。例: `cp-0011-python-package-baseline`
- 対応するタスクが [ロードマップ](docs/product/roadmap.md) に無い場合は、先に [`maintain-roadmap`](.agents/skills/maintain-roadmap/SKILL.md) でタスクを起こしてIDを確定します。
- 作業ブランチは最新の `main` から作成します。

### マージ

- `main` へのマージはpull request経由のみとし、CIの成功を必須とします。
- マージ方法はマージコミットだけを許可します。squash mergeとrebase mergeは無効にします。これは、どのコミット群が1つのタスクだったかを履歴に残すためです。fast-forwardではこの境界がグラフに残りません。
- `main` が進んだ場合は、PRブランチを `main` の上へrebaseしてからマージします。交差した履歴を作らないためです。
- マージ後も作業ブランチを削除しません。検証の経緯を追跡できる状態を保ちます。

### `main` の保護設定

| 設定 | 値 | 目的 |
| --- | --- | --- |
| Allow merge commits | ON | タスクの境界を履歴へ残す |
| Allow squash merging | OFF | コミット単位の経緯を失わせない |
| Allow rebase merging | OFF | fast-forward相当の直線化を防ぐ |
| Require a pull request before merging | ON | `main` への直接pushを禁止する |
| Require status checks to pass | ON | CI成功をマージ条件にする |
| Require branches to be up to date | ON | 古い `main` の上での検査結果でマージさせない |
| Require linear history | OFF | マージコミットを禁止しないため |

必須にするstatus checkは、CIに存在するjobだけを指定します。品質検査とCompose検査のjobは `CP-0060` と `CP-0061` で追加され、その時点で必須指定へ加えます。

### ブランチ名の機械検査

現時点では導入しません。ブランチ名は `start-task` が生成し、誤った名前が付いても機能的な影響が無く、CIが失敗を報告できるのはpush後で修正コストが名前の付け直しになるためです。ruleset側で命名を強制する方法も、臨時の調査ブランチまで作成できなくなるため採用しません。手動でのブランチ作成が常態化した場合、または命名から作業単位を機械的に辿る仕組みを導入する場合に再検討します。

## 文書の扱い

- 現在の要求は `docs/product/`、現在の設計は `docs/architecture/` と `docs/contracts/` を正とします。
- 採用した重要な判断はADRに残します。過去のADR本文を現在の判断に合わせて書き換えず、新しいADRから置換対象を参照します。
- 日付で変わり得る外部情報には確認日と根拠URLを記載します。
- DB列やschemaをMarkdownへ複製せず、意味と不変条件を記載します。
- 実装によって振る舞い、契約、運用方法が変わる場合は、同じ変更で対応する文書を更新します。
- Markdown変更後は `python3 .agents/skills/check-doc-links/scripts/check_doc_links.py` を実行します。
- Roadmap変更後は `python3 .agents/skills/maintain-roadmap/scripts/validate_roadmap.py` も実行します。
- エージェント定義やSkillを変更した後は `python3 .agents/skills/maintain-tool-parity/scripts/check_tool_parity.py --write` を実行し、生成されたファイルも一緒にコミットします。

## 実装上の原則

- ドメイン層をHTTP、HTML、特定のDB製品、OCRなどの詳細へ依存させません。
- 情報源固有の処理は `src/card_pulse/adapters/sources/<source>/` に閉じ込めます。
- 原本を保存してから解析し、固定fixtureだけでparserを再実行できるようにします。
- 価格観測値は追記型とし、再実行で重複しない識別規則を持たせます。
- 自動同定の誤結合を避け、曖昧な結果はレビュー対象にします。
- 認証情報、Cookie、個人情報、取得原本、開発用DB volumeをGitへ追加しません。

## テスト

テスト環境はPhase 1で整備します。整備後は、少なくとも次を変更内容に応じて実行します。

- ドメイン規則のunit test
- 保存と再実行のintegration test
- 共通Collector契約のcontract test
- 固定fixtureを使ったparser regression test

テストから実際の情報源へアクセスしません。固定fixtureには保存と再配布が許され、秘密情報を含まないサンプルだけを使用します。

## 完了条件

- 変更の目的と責務の場所が明確である。
- 関係するテストが通っている。
- 必要な文書、ADR、schema、migrationが更新されている。
- ログやfixtureに秘密情報が含まれていない。
- 集計結果から観測値と原本メタデータまで追跡できる。

ローカル開発環境はDocker ComposeでAPI、Worker、選定したDB、artifact storageを起動できるようにします。本番固有のmanaged service、IAM、負荷分散、backupはDockerで再現できる前提にしません。

セットアップ、lint、型チェック、テストの具体的なコマンドは、Phase 1で `pyproject.toml` とDocker環境を作成した時点で追記します。
