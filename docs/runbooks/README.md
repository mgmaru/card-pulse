# Runbooks

Runbookは、開発者または運用者が同じ手順を再現する必要がある作業を記載する。

## 一覧

| Runbook | 内容 |
| --- | --- |
| [ローカル開発環境](local-development.md) | Docker ComposeでAPI、Worker、DB、artifact storageを起動、確認、停止、初期化する |

## 作成する条件

Collectorとreview、backupの手順は対応する実装が入った時点で作る。作成は[ロードマップ](../product/roadmap.md)のタスクが持ち、担当の無いRunbookを増やさない。担当を書かずに条件だけを置くと、実装が終わった時点で誰も手順を書かないまま次へ進む。

| Runbook | 作成するタスク | 最低限含める内容 |
| --- | --- | --- |
| `ingestion.md` | `CP-0024`（最初のCollector実装） | 通常実行、dry run、再実行、結果確認、終了code |
| `source-failure.md` | `CP-0075`（定期取得の開始前） | 実行欠落と失敗段階の判定、診断証拠の確認、再試行可否、source停止、正常原本との比較、parser修正、保存済み原本の再解析、dry run、手動再開、最終成功日時と鮮度の確認 |
| `review-queue.md` | `CP-0090`（レビュー操作の実装） | 確認方法、確定・却下・保留、監査履歴 |
| `backup-restore.md` | `CP-0088`（DBとartifact保存の後） | 対象、整合性、backup、空環境への復元、検証 |
| `reparse.md` | `CP-0089`（計画的なparser更新の手順） | 対象選択、旧結果保持、実行、差分確認、rollback |
| `schema-change.md` | `CP-0043`（最初のserver配置前） | 後方互換なmigration、API・Workerのdeployment順序、rollback |
| `deployment.md` | `CP-0042`（最初のserver配置） | API・Worker・DBの配置、private接続、role、secret、health check |
| `twscrape.md` | twscrapeの採用を決めるADR | 認証情報、version固定、監視、障害、撤退手順 |

`review-queue.md`はPhase 4の`CP-0090`が作り、Phase 6の`CP-0048`がOCR固有の手順を追記する。

## 記載ルール

- 前提条件と影響範囲を冒頭に書く。
- コピーして実行できるコマンドと、期待する結果を対にする。
- 秘密情報をコマンド例、ログ例、画像へ含めない。
- 破壊的操作には対象を確認する手順と復旧方法を付ける。
- 作成時と変更時に、空または隔離した環境で一度実行して最終確認日を記録する。
