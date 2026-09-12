# Research

このディレクトリには、構想、技術比較、外部サービス、取得方法について、調査時点で得られた情報を保存する。

Research文書は現在の仕様や採用判断そのものではない。現在有効な要求は `docs/product/`、設計は `docs/architecture/` と `docs/contracts/`、採用判断は `docs/adr/` を正とする。

## 文書

- [Card Diggerと相場データ基盤の連携構想](card-digger-market-data-concept.md)
- [CP-0008 DB候補比較](database-candidate-comparison-2026-09.md)
- [TCG相場情報の収集方法](tcg-market-data-collection-methods.md)
- [twscrape運用検討](twscrape-operations-guide.md)

## 更新ルール

- 調査日または基準日を明記する。
- 価格、rate limit、規約、version、運営状況には根拠URLと確認日を付ける。
- 調査結果を採用する場合、ADR、source文書、runbookへ必要な結論を移す。
- 古い調査資料を現在の結論へ見せかけて上書きせず、状態または後継文書への参照を追加する。
