# Architecture Decision Records

ADRは、複数のコンポーネントへ影響する判断、将来の選択肢を制約する判断、後から理由が分かりにくくなる判断を記録する。

## 状態

- `Proposed`: 検討中
- `Accepted`: 採用中
- `Rejected`: 採用しなかった
- `Superseded`: 後続ADRに置き換えられた
- `Deprecated`: 新規利用をやめ、移行中または撤去予定

AcceptedとなったADRは、誤字やリンク切れ以外では結論を書き換えない。判断を変更するときは新しいADRを追加し、双方に置換関係を記載する。

## 一覧

| ADR | 状態 | 判断 |
| --- | --- | --- |
| [0001](0001-modular-monolith.md) | Accepted | MVPをPythonのモジュラーモノリスとして構成する |
| [0002](0002-append-only-provenance.md) | Accepted | 原本と価格観測を追記型で保存し、出典を追跡する |
| [0003](0003-mvp-local-storage.md) | Accepted | MVPはSQLiteとローカルファイルシステムを使う |

新しいADRは [template.md](template.md) を複製し、4桁の連番と短いslugを付ける。
