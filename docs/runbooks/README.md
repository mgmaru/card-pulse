# Runbooks

Runbookは、開発者または運用者が同じ手順を再現する必要がある作業を記載する。現在は実行環境とCollectorが未実装のため、個別Runbookはまだない。

## 作成する条件

| Runbook | 作成する時点 | 最低限含める内容 |
| --- | --- | --- |
| `local-development.md` | Phase 1 | Docker要件、build、起動、設定、migration、test、lint、型チェック、停止、初期化 |
| `ingestion.md` | 最初のCollector実装時 | 通常実行、dry run、再実行、結果確認、終了code |
| `source-failure.md` | 定期取得開始時 | エラー分類、再試行、停止、parser変更検知、復旧確認 |
| `review-queue.md` | review機能実装時 | 確認方法、確定・却下・保留、監査履歴 |
| `backup-restore.md` | DBとartifact保存実装時 | 対象、整合性、backup、空環境への復元、検証 |
| `reparse.md` | parser version管理実装時 | 対象選択、旧結果保持、実行、差分確認、rollback |
| `schema-change.md` | 最初のserver配置前 | 後方互換なmigration、API・Workerのdeployment順序、rollback |
| `deployment.md` | 最初のserver配置前 | API・Worker・DBの配置、private接続、role、secret、health check |
| `twscrape.md` | twscrape採用時のみ | 認証情報、version固定、監視、障害、撤退手順 |

## 記載ルール

- 前提条件と影響範囲を冒頭に書く。
- コピーして実行できるコマンドと、期待する結果を対にする。
- 秘密情報をコマンド例、ログ例、画像へ含めない。
- 破壊的操作には対象を確認する手順と復旧方法を付ける。
- 作成時と変更時に、空または隔離した環境で一度実行して最終確認日を記録する。
