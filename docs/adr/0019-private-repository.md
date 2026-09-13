# ADR-0019: repositoryをprivateにし、公開範囲をADR-0012へそろえる

- 状態: Accepted
- 日付: 2026-09-13
- 決定者: プロジェクトオーナー
- 置換するADR: なし
- 置換されたADR: なし

## Context

[ADR-0012](0012-private-personal-operation.md)は、Card Pulseをプロジェクトオーナー本人だけが使う非公開アプリとし、「ソースコード、取得原本、source由来fixture、抽出値、価格履歴、APIを第三者へ公開または提供しない」と定めた。Consequencesでは、repositoryの公開を、実施前に新しいADRで判断すべき事項として挙げている。

`CP-0080`で公開範囲を棚卸ししたところ、repositoryは2026-09-04の作成時からpublicだった。その判断を記録した文書は無く、ADR-0012の記述と実際の状態が食い違っていた。

棚卸しの結果は次のとおりである。確認日は2026-09-13。

| 種類 | 棚卸し時の状態 |
| --- | --- |
| ソースコード、設計文書、ADR | 公開されていた |
| 抽出値（代表サンプル13行） | 公開されていた |
| 取得原本 | 追跡されていない |
| source由来fixture | 追跡されていない |
| 価格履歴 | 追跡されていない |
| API | 未配置 |

`var/`は`.gitkeep`だけを追跡し、`tests/fixtures/sources/`は空で、git履歴を全走査しても原本とfixtureが入った形跡は無かった。守られていなかったのはソースコードと抽出値の二つである。

抽出値は`docs/sources/`の12行と[ADR-0009](0009-pokemon-mvp-sources.md)の1行で、5情報源の代表サンプルとして実店舗名、カード、買取価格、source内IDを含む。`docs/sources/`は2026-09-09から09-11に追加され、ADR-0012は09-12に追加された。規則が後から入り、既存データの扱いを決めるタスクが作られなかったための食い違いである。

公開の実績は限定的だった。fork、star、watcherはいずれも0件で、releaseとGitHub Pagesも無い。

## Decision

repositoryをprivateにし、ADR-0012が定めた公開範囲へ実際の状態をそろえる。2026-09-13に切り替えた。

**ADR-0012が私的使用として組み立てた整理は、利用者と公開範囲を本人に限定したことに依存しており、公開repositoryはその前提そのものを崩す。** 公開を続ける選択も検討したが、その場合は公開する対象の境界、既に公開された抽出値の扱い、LICENSE、取得方針を公開したままにすることの是非という四つを新たに決める必要が生じる。privateへ戻す選択はADR-0012の前提を維持し、判断を増やさず、削除作業も伴わない。

### 公開されていた抽出値の扱い

`docs/sources/`と[ADR-0009](0009-pokemon-mvp-sources.md)に残る代表サンプルは削除しない。private化により第三者への公開・提供に当たらなくなるためである。

これらは調査時点の代表サンプルを文書へ記録したもので、ADR-0012が「Git、CI artifact、公開backupへ含めない」と定めた取得原本、抽出履歴、source由来fixtureとは区別する。情報源の比較可能性をどう判断したかの根拠であり、[ADR-0010](0010-pokemon-mvp-source-candidates.md)以降の判断を後から読み解くために要る。

継続的に取得した価格観測をrepositoryへ入れることは、この区別に含めない。取得した観測は引き続き`var/`配下のGit管理外領域に置く。

### 機械検査

repositoryが再びpublicになった状態でpull requestまたはpushが発生した場合、CIの`Documentation` jobが失敗する。判断を変えるときはこの検査も外すことになり、変更が差分として現れる。

検査を`Documentation` jobの中へ置くのは、同jobが`main`のrulesetで必須status checkに指定済みだからである。新しいjobを作ると必須指定の追加が別途必要になり、追加するまでは失敗を無視してマージできる。

## Consequences

- ADR-0012の記述と実際の状態が一致する。公開に関する判断は、再び新しいADRの対象になる。
- GitHub Actionsがprivate repositoryの枠の対象になる。GitHub Freeでは月2,000分で、publicでは無制限だった（[GitHub Actionsの課金](https://docs.github.com/en/billing/managing-billing-for-your-products/about-billing-for-github-actions)、確認日2026-09-13）。現在のCIは1回あたり30秒未満で、枠に対して余裕がある。
- 公開ポートフォリオとしての価値は失う。
- 公開されていた期間の内容は取り消せない。fork、star、watcherが0件で、releaseとPagesも無かったため、実際に参照された形跡は確認できていない。
- 将来公開する場合は、本ADRと[ADR-0012](0012-private-personal-operation.md)を置き換える新しいADRで、公開する対象の境界、既存の抽出値の扱い、LICENSEを決める必要がある。

## Alternatives considered

- **ソースコードの公開を許容し、データだけ非公開にする**: 設計文書の公開価値を残せる。採らなかったのは、ADR-0012の前提を置き換える判断に加えて、公開対象の境界、既存の抽出値13行の扱い、LICENSE、取得方針を公開したままにすることの是非を同時に決める必要があり、MVPの成立性をまだ検証していない段階で判断を増やすためである。抽出値を消してもgit履歴には残り、履歴の書き換えはforce pushを要して`main`の保護設定と衝突する。
- **publicのまま、抽出値を含む節だけを落とす**: 作業量は最も小さい。採らなかったのは、ソースコードの公開というADR-0012との食い違いが残り、公開する対象の境界を決めないまま運用が続くためである。
- **公開範囲を決めず、ADR-0012の記述を緩める**: 判断を先送りできる。採らなかったのは、ADR-0012の私的使用の整理が公開範囲の限定に依存しており、そこを緩めると取得方針の前提まで曖昧になるためである。

## Validation

- CIの`Documentation` jobが、repositoryがpublicになった状態を検出して失敗する。
- 次のいずれかが起きた場合に再評価する。
  - 公開したい具体的な理由が生じる。ポートフォリオとしての公開、外部からの参照、共同開発のいずれか。
  - GitHub Actionsの無料枠が現在のCI実行に対して不足する。
  - [ADR-0012](0012-private-personal-operation.md)の前提が変わる。
