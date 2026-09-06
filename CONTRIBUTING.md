# Card Pulseへの変更

Card Pulseは現在、情報源とMVPの成立性を確認する段階です。実装量より、取得データを再現・追跡できることを優先します。

## 変更前に確認する文書

1. [プロダクト構想](docs/product/vision.md)
2. [MVP定義](docs/product/mvp.md)
3. 変更対象に関係する [ADR](docs/adr/README.md)
4. Collector変更の場合は [Collector契約](docs/contracts/collector.md) と対象のsource文書

## 文書の扱い

- 現在の要求は `docs/product/`、現在の設計は `docs/architecture/` と `docs/contracts/` を正とします。
- 採用した重要な判断はADRに残します。過去のADR本文を現在の判断に合わせて書き換えず、新しいADRから置換対象を参照します。
- 日付で変わり得る外部情報には確認日と根拠URLを記載します。
- DB列やschemaをMarkdownへ複製せず、意味と不変条件を記載します。
- 実装によって振る舞い、契約、運用方法が変わる場合は、同じ変更で対応する文書を更新します。

## 実装上の原則

- ドメイン層をHTTP、HTML、SQLite、OCRなどの詳細へ依存させません。
- 情報源固有の処理は `src/card_pulse/adapters/sources/<source>/` に閉じ込めます。
- 原本を保存してから解析し、固定fixtureだけでparserを再実行できるようにします。
- 価格観測値は追記型とし、再実行で重複しない識別規則を持たせます。
- 自動同定の誤結合を避け、曖昧な結果はレビュー対象にします。
- 認証情報、Cookie、個人情報、取得原本、ローカルDBをGitへ追加しません。

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

セットアップ、lint、型チェック、テストの具体的なコマンドは、Phase 1で `pyproject.toml` と実行環境を作成した時点で追記します。
