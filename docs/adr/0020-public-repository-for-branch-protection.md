# ADR-0020: repositoryをpublicへ戻し、`main`の保護設定を公開範囲の整合より優先する

- 状態: Accepted
- 日付: 2026-09-13
- 決定者: プロジェクトオーナー
- 置換するADR: [ADR-0019](0019-private-repository.md)
- 置換されたADR: なし

## Context

[ADR-0019](0019-private-repository.md)は、`CP-0080`の棚卸しを受けてrepositoryをprivateにした。切り替えた直後に、rulesetとbranch protectionのAPIがいずれも403を返すことが分かった。

```text
Upgrade to GitHub Pro or make this repository public to enable this feature.
```

GitHub Freeでは、private repositoryのprotected branchesが提供されない。この機能はGitHub Pro以上に含まれ、public repositoryでは無料で使える（[GitHubのプラン](https://docs.github.com/en/get-started/learning-about-github/githubs-plans)、確認日2026-09-13）。

これにより、`CP-0065`が[保護設定](../../CONTRIBUTING.md#main-の保護設定)として定めたもののうち、次が失効した。

| 設定 | private化後 |
| --- | --- |
| Require a pull request before merging | 失効 |
| Require status checks to pass | 失効 |
| Require branches to be up to date | 失効 |
| Allow merge commits ON、squash・rebase OFF | 維持（repository設定のため残る） |

`main`へ直接pushでき、CIが失敗したままでもmergeできる状態になった。[ADR-0019](0019-private-repository.md)はConsequencesにGitHub Actionsの枠しか書いておらず、この影響を検討していなかった。

選択肢は3つだった。GitHub Pro（月4ドル）へ移って両立させる、publicへ戻す、privateのまま保護なしで運用する。

## Decision

repositoryをpublicへ戻し、[ADR-0019](0019-private-repository.md)を置き換える。

**`main`の保護は、外れたことに気付けないまま壊れていく種類の仕組みであり、規約と運用上の注意では代替できない。** `CP-0065`は、実装の多くをAIエージェントが行うこのrepositoryでは、pull requestが人間の差分を確認する唯一の地点になると記録した。保護が外れると、CIが失敗したままのmergeも`main`への直接pushも通る。一方、[ADR-0012](0012-private-personal-operation.md)との不整合は文書上の食い違いであり、記録と判断で解ける。

費用で両立させる案は採らない。MVPの成立性をまだ検証していない段階で、月額の固定費を増やす理由が弱い。

### 残る不整合

[ADR-0012](0012-private-personal-operation.md)は「ソースコード、取得原本、source由来fixture、抽出値、価格履歴、APIを第三者へ公開または提供しない」と定めており、publicなrepositoryはこれに反する。`docs/sources/`の12行と[ADR-0009](0009-pokemon-mvp-sources.md)の1行にある代表サンプルも再び公開される。

この不整合は未解決のまま残す。解消は`CP-0084`で扱い、公開してよい対象の境界、既存の抽出値の扱い、LICENSEの有無を決める。それまでの間、本ADRは「不整合を認識したうえで公開を選んだ」記録として機能する。認識しないまま公開されていた`CP-0080`以前の状態とは区別する。

新たに取得した原本、source由来fixture、価格履歴をrepositoryへ入れない規則は[ADR-0012](0012-private-personal-operation.md)のまま変えない。公開範囲の判断が動いても、`var/`配下のGit管理外領域に置く境界は動かさない。

### 機械検査

[ADR-0019](0019-private-repository.md)がCIへ追加したvisibility検査は外す。検査していた条件そのものが決定ではなくなったためである。

## Consequences

- `CP-0065`の保護設定が使える状態へ戻る。private化ではrulesetが削除されず無効化されるだけで、public化により`main protection`がenforcement `active`のまま戻ることを2026-09-13に確認した。再作成は不要だった。
- GitHub Actionsがpublic repositoryの無制限枠へ戻る。`CP-0061`でCompose検査を追加しても、実行時間を枠に対して気にしなくてよい。
- [ADR-0012](0012-private-personal-operation.md)との不整合が残る。`CP-0084`が解くまで、ソースコードと代表サンプル13行が公開される。
- privateを選んで戻した経緯が[ADR-0019](0019-private-repository.md)と本ADRに残る。同じ検討を繰り返さずに済む。
- 有料planへ移る判断は将来へ残る。利用者が増える場合、または保護をさらに強める必要が出た場合に再評価する。

## Alternatives considered

- **GitHub Pro（月4ドル）へ移り、privateと保護を両立する**: 判断としては最も素直で、[ADR-0019](0019-private-repository.md)と`CP-0065`の両方を維持できる。採らなかったのは、MVPの成立性をまだ検証していない段階で、[DB要件](../architecture/database-requirements.md#運用と費用)が置いた月額目標とは別の固定費を増やす理由が弱いためである。保護の必要性は費用と無関係に残るため、再評価条件として本ADRに残す。
- **privateのまま、保護なしで運用する**: 費用も公開も伴わない。採らなかったのは、`CP-0065`が記録した「pull requestが人間の確認する唯一の地点」という前提が崩れ、CIの失敗を無視したmergeを規約だけで防ぐことになるためである。
- **privateのまま、保護を別の仕組みで代替する**: ローカルのpre-push hookや、`main`への直接pushをCIで検知する方法が考えられる。採らなかったのは、hookは開発機ごとの設定で強制力がなく、CIによる検知は`main`が壊れた後にしか働かないためである。

## Validation

- public化の直後にrulesetを確認し、`CP-0065`の保護設定が有効であることを確かめた（2026-09-13）。`bypass_actors`は空で、必須status checkは`Documentation`、`Agent configuration`、`Quality checks`の3つだった。
- `CP-0084`で[ADR-0012](0012-private-personal-operation.md)との不整合を解消する。
- 次のいずれかが起きた場合に再評価する。
  - 公開を続けられない事情が生じる。情報源の運営者からの指摘、利用者の追加、公開したくない情報の混入のいずれか。
  - 有料planへ移る理由が生じる。
  - `CP-0084`の結論が、公開を許容しないものになる。
