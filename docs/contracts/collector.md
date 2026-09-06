# Collector契約

> 状態: Draft
>
> 最終更新: 2026-09-06
>
> 確定条件: 最初の2情報源と手動取込を同じ契約で表現できること

## 目的

Collector契約は、店舗Web、JSON、CSV等の取得方法固有の情報をapplication層へ漏らさず、同じ取込処理へ渡すための境界を定義する。

MVPでは一つの巨大な`collect()`処理にせず、外部アクセスを伴う取得と、保存済み原本だけを扱う解析を分ける。

```text
fetch(run context) -> raw artifact inputs
persist raw artifacts
parse(stored artifact, parser version) -> observation candidates
validate / identify -> observation or review item
```

Python上の正確なprotocolと型定義は実装時のコードを正とする。

## Source adapterの責務

- 情報源へ許可された方法と頻度でアクセスする。
- timeout、再試行上限、backoff、User-Agentをsource設定に従って扱う。
- source内ID、URL、MIME type、取得日時、利用可能なら公開日時を原本候補へ付与する。
- 保存済み原本を、ネットワークアクセスなしで解析する。
- 原文値を保持した観測候補へ変換する。
- 0件、形式変更、必須項目欠損、認証・制限、通信失敗を区別して報告する。

Source adapterは次を担当しない。

- SQLiteテーブルへの直接書込み
- source横断のカード同定
- source横断の重複排除
- 相場集計
- review結果の確定
- Card Digger向けの評価

## Fetchの出力

原本候補は少なくとも次の情報を表現できるようにする。

| 項目 | 必須 | 意味 |
| --- | --- | --- |
| `source_slug` | 必須 | source設定とadapterを識別する安定値 |
| `source_item_id` | 任意 | 情報源側が持つ投稿・文書・商品等のID |
| `source_url` | 条件付き | 人間が出典を再確認できるURL。手動ファイルでは省略可能 |
| `retrieved_at` | 必須 | 取得日時とタイムゾーン |
| `published_at_hint` | 任意 | 取得段階で分かる公開日時候補 |
| `media_type` | 必須 | JSON、HTML、CSV、PDF、画像等の形式 |
| `content` | 必須 | 保存対象となる原本byte列または安全なstream |
| `metadata` | 任意 | 解析や監査に必要なsource固有情報。秘密情報は禁止 |

applicationはcontent hashを計算し、artifact storeへ保存してからparseへ渡す。

## Parseの出力

一つの観測候補は少なくとも次を表現できるようにする。

| 項目 | 必須 | 備考 |
| --- | --- | --- |
| `artifact_id` | 必須 | 根拠となる保存済み原本 |
| `parser_name` / `parser_version` | 必須 | 再現可能な解析処理の識別子 |
| `shop_ref` | 必須 | source内の店舗表記または設定参照 |
| `tcg_raw` | 必須 | 原文またはsource設定から得たTCG |
| `card_name_raw` | 条件付き | カード番号だけの情報源などは実データで判断 |
| `card_number_raw` | 推奨 | カード同定の主要候補 |
| `set_raw` | 任意 | 原文のセット情報 |
| `rarity_raw` | 任意 | 原文のレアリティ |
| `edition_raw` | 任意 | 版、初版、プロモ等の表記 |
| `language_raw` | 任意 | 言語・地域 |
| `amount_minor` | 必須 | 整数の最小通貨単位 |
| `currency` | 必須 | ISO 4217等の明示値 |
| `price_type` | 必須 | buy、sell等の定義済み値 |
| `condition_raw` | 任意 | 美品限定等の原文条件 |
| `published_at` | 任意 | 不明の場合は取得日時で補完しない |
| `valid_until` | 任意 | 情報源が明示した場合だけ設定 |
| `location` | 推奨 | JSON path、CSS selector、行番号等の原本内位置 |
| `warnings` | 任意 | 欠損、解釈、異常に関する構造化警告 |

## 結果と失敗

最低限、次を機械的に区別できる結果型を設ける。

- 成功して候補が1件以上ある。
- 成功して正当に0件だった。
- 一部の原本または行だけ失敗した。
- 通信、認証、rate limit等で取得できなかった。
- 期待した構造が変わり解析できなかった。
- 必須項目欠損または値不正により確定できなかった。

例外文字列だけに依存せず、`error_code`、再試行可否、artifact参照、詳細を構造化して記録する。

## 冪等性と再解析

- 同じsource itemを再取得した場合も、content hashが同じなら同一原本として扱えること。
- 同じartifactとparser versionから同じ候補集合を生成できること。
- 同じ候補を再投入しても価格観測が重複しないこと。
- parser versionが変わった再解析では、新旧結果とその関係を追跡できること。
- sourceの現在状態を参照しない純粋なparse処理を基本とすること。

## Contract test

すべてのsource adapterに共通test suiteを適用し、次を確認する。

- 固定fixtureから必須フィールドを持つ候補を返す。
- ネットワークなしでparseできる。
- 同一入力に対して決定的な結果を返す。
- 不正fixtureを正常な0件として扱わない。
- source固有値がdomainやDBの内部表現へ直接漏れない。
- fixtureやエラーに秘密情報を含めない。
