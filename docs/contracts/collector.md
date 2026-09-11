# Collector契約

> 状態: Draft
>
> 最終更新: 2026-09-11
>
> 確定条件: MVP採用となる2〜3情報源と手動取込を同じ契約で表現できること

## 目的

Collector契約は、店舗Web、JSON、CSV等の取得方法固有の情報をapplication層へ漏らさず、同じ取込処理へ渡すための境界を定義する。

MVPでは一つの巨大な`collect()`処理にせず、外部アクセスを伴う取得と、保存済み原本だけを扱う解析を分ける。さらに、欠損を許す抽出結果、価格候補、カード同定、確定観測を同じ型や状態へ混ぜない。

```text
fetch(run context) -> raw artifact inputs
persist raw artifacts
process(stored artifact, processor version) -> extracted records
promote(extracted record, source context) -> observation candidate or processing issue
validate / identify -> price observation or review item
```

Python上の正確なprotocolと型定義は実装時のコードを正とする。

## Source adapterの責務

- 情報源へ許可された方法と頻度でアクセスする。
- timeout、再試行上限、backoff、User-Agentをsource設定に従って扱う。
- source内ID、URL、MIME type、取得日時、利用可能なら公開日時を原本候補へ付与する。
- 保存済み原本を、ネットワークアクセスなしで解析する。
- 原文値、欠損、原本内位置、利用できる項目別confidenceを保持した抽出結果へ変換する。
- 0件、形式変更、必須項目欠損、認証・制限、通信失敗を区別して報告する。

Source adapterは次を担当しない。

- DB tableへの直接書込み
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

`source_item_id`は原本と情報源内の対象を追跡する値であり、Card Pulseのカード主キーとして扱わない。同じ印刷仕様のカードを複数情報源へまたがって識別する内部UUIDは、source adapterではなく後続のカード同定で確定する。

## Processingの出力

parseまたは将来のOCR等を一回実行するたびに`processing_run`を作る。処理実行は少なくとも、`artifact_id`、processor名・version、結果へ影響する設定参照、開始・終了日時、状態、抽出件数、error codeを表現できるようにする。

processorは`extracted_record`を0件以上返す。抽出結果は原本に存在した可能性のある行や項目を失わず保持する段階であり、価格観測の必須項目をまだ満たさなくてよい。

| 項目 | 必須 | 意味 |
| --- | --- | --- |
| `processing_run_id` | 必須 | 生成した処理実行 |
| `raw_fields` | 必須 | 原文の項目名と値。空文字、読取不能、欠損を区別する |
| `field_evidence` | 条件付き | 値の由来、原本内位置、confidence、警告。値を抽出または補足した場合に持つ |
| `record_location` | 推奨 | JSON path、CSS selector、行番号、画像内領域等 |
| `warnings` | 任意 | 欠損、解釈、異常に関する構造化警告 |

`field_evidence`は、値が原本、source metadata、取込設定、正規化処理、人間の判断のどこから得られたかを区別する。processorがconfidenceを返さない項目へ推定値を作らない。抽出confidenceは文字や領域の読取りに関する値であり、カード同定のmatch scoreとは別に扱う。

構造化Webのparserでは`extracted_record`が直ちに観測候補の条件を満たすことがある。その場合も、抽出した事実と候補への昇格という意味上の境界を保ち、原本から両方を追跡できるようにする。

## 観測候補への昇格

`extracted_record`が価格候補の最低条件を満たした場合、applicationは`observation_candidate`へ昇格させる。一つの観測候補は少なくとも次を表現できるようにする。

| 項目 | 必須 | 備考 |
| --- | --- | --- |
| `extracted_record_id` | 必須 | 根拠となる抽出結果。processing runとartifactまで追跡できること |
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
| `location` | 推奨 | 抽出結果が参照する原本内位置 |
| `warnings` | 任意 | 欠損、解釈、異常に関する構造化警告 |

`shop_ref`、`tcg_raw`、`currency`、`price_type`等をsource metadataまたは取込設定から与える場合、対応する`field_evidence`から設定のversionまたは参照を追跡できるようにする。

金額を抽出できない、通貨を決められない等、最低条件を満たさない結果は`extracted_record`と昇格できなかった理由を残し、観測候補へ昇格させない。人間が原本から値を修正できる場合はreview対象にできる。カード同定に必要な項目が不足していても価格候補の最低条件を満たす場合は観測候補とし、後続の同定でreview要否を決める。

カード番号、セット、レアリティ、版、言語等は同定候補を作るための原文属性であり、連結値やhashを内部カードの主キーとして発行しない。内部UUID、属性、外部IDを分離する判断は[ADR-0008](../adr/0008-opaque-card-identity-id.md)を参照する。

## 結果と失敗

最低限、次を機械的に区別できる結果型を設ける。

- 成功して候補が1件以上ある。
- 成功して正当に0件だった。
- 一部の原本または行だけ失敗した。
- 通信、認証、rate limit等で取得できなかった。
- 期待した構造が変わり解析できなかった。
- 抽出結果は得られたが、必須項目欠損または値不正により観測候補へ昇格できなかった。
- 観測候補は得られたが、カード同定を確定できずreviewまたは未同定になった。

例外文字列だけに依存せず、`error_code`、再試行可否、artifact参照、詳細を構造化して記録する。

人間が原本から修正できる抽出値の欠損・低confidenceと、候補から解決できる同定曖昧はreview itemにできる。通信失敗、processor停止、原本全体の破損等、人間が値や候補を判断しても解決しない技術的失敗はprocessing issueとして扱う。

## 冪等性と再解析

- 同じsource itemを再取得した場合も、content hashが同じなら同一原本として扱えること。
- 同じartifact、processor version、処理設定から同じ抽出結果集合を生成できること。
- 同じ抽出結果と昇格規則versionから同じ観測候補を生成できること。
- 同じ候補を再投入しても価格観測が重複しないこと。
- processorまたは昇格規則のversionが変わった再解析では、新旧の処理実行、抽出結果、候補とその関係を追跡できること。
- sourceの現在状態を参照しない純粋なprocessingを基本とすること。

## Contract test

すべてのsource adapterに共通test suiteを適用し、次を確認する。

- 固定fixtureから抽出結果を返し、最低条件を満たす結果だけを観測候補へ昇格できる。
- ネットワークなしでprocessingを実行できる。
- 同一入力、processor version、設定に対して決定的な結果を返す。
- 欠損した抽出結果を失わず、確定観測へ混ぜない。
- source metadataまたは取込設定から与えた値の由来を追跡できる。
- 不正fixtureを正常な0件として扱わない。
- source固有の項目名や構造を`extracted_record`の原文値と由来情報に閉じ込め、確定観測のdomain型とschemaへ漏らさない。
- fixtureやエラーに秘密情報を含めない。

層を分ける理由、単一の論理DBを維持する判断、物理分離の再検討条件は[ADR-0007](../adr/0007-layered-ingestion-data.md)、カードの内部UUIDと外部IDを分離する判断は[ADR-0008](../adr/0008-opaque-card-identity-id.md)を参照する。
