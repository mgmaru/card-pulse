# ADR-0021: `main`の保護規則をrepository内のfileを正として管理する

- 状態: Accepted
- 日付: 2026-09-13
- 決定者: プロジェクトオーナー
- 置換するADR: なし
- 置換されたADR: なし

## Context

`CP-0065`は`main`の保護設定をGitHubのrulesetで作り、その内容を[CONTRIBUTING.md](../../CONTRIBUTING.md#main-の保護設定)へ表として書いた。rulesetはGitHub側に保存され、repositoryにはfileが無い。表は写しであり、両者を突き合わせる仕組みは無かった。

`CP-0083`でその弱さが実際に現れた。repositoryをprivateにした瞬間、GitHub Freeではprotected branchesが使えないためrulesetが無効化された。repository側は何も変わらず、CIも緑のままで、気付いたのはAPIを直接呼んだからである。

publicへ戻した後に実設定を読み直すと、表に無い規則が3つ動いていた。`deletion`（`main`の削除禁止）、`non_fast_forward`（force push禁止）、`require_extra_approval_for_unattributed_changes`である。表は実設定より緩い側にずれており、どちらが正かも決まっていなかった。

同じ種類の問題は`CP-0069`が解いている。CodexとClaude Codeの設定を`.agents/`の中立形式から生成し、乖離をCIで検査する形にした。rulesetにも同じ形が使える。

`CP-0085`で調べた前提は次のとおりである。確認日は2026-09-13。

- public repositoryのrulesetは未認証で読める。`cli/cli`、`github/docs`、`astral-sh/uv`のいずれもHTTP 200を返した。CIから読むために追加のcredentialは要らない。
- `bypass_actors`だけは、書き込み権限のある読み手にしか返らない（[Repository rules API](https://docs.github.com/en/rest/repos/rules)）。未認証の応答には含まれていなかった。
- GitHubはrulesetのimportとexportを正式機能として提供し、[github/ruleset-recipes](https://github.com/github/ruleset-recipes)でruleset JSONをpublic repositoryへ置いている。fileとして持つこと自体は公式に想定された使い方である。

## Decision

`main`の保護規則は`.github/rulesets/main-protection.json`を正とし、GitHubが強制している内容をそこから派生させる。規則を変えるときはfileを変更し、`python3 scripts/ruleset.py apply`で反映する。

**規則の変更をfile側から始めるのは、変更がpull requestの差分として必ず現れるようにするためである。** GitHubのUIから直接変えると、変更の事実がrepositoryのどこにも残らず、`CP-0083`で起きたように誰も気付かないまま保護が動く。fileを正にすれば、規則の変更はcodeの変更と同じ経路を通る。

### CIは検査だけを行い、適用しない

`Repository ruleset` jobが`scripts/ruleset.py check`を実行し、fileと実設定の差分を報告する。適用は人が明示的に実行するコマンドに限る。

**CIから適用できると、`main`を守る規則が`main`経由で書き換え可能になる。** 保護を緩めるpull requestを通せば、その保護自体が外れる。保護設定の要件は「守られる側から変更できないこと」であり、自動適用はその要件と正面から衝突する。

同じ理由で、`scripts/ruleset.py apply`はworkflowから呼ばない。適用にはrepositoryのadmin権限が要り、その権限を持つcredentialをCIへ置かない。public repositoryでは検査に追加のcredentialが不要なため、この制約は検査の能力を下げない。

### `bypass_actors`を持たない

fileに`bypass_actors`を書かない。GitHubがこの項目を書き込み権限のある読み手だけに返すのは、誰が保護を迂回できるかが秘匿すべき情報だからである。public repositoryのfileへ書けば、GitHubが隠している情報を自ら公開することになる。

`apply`はこの項目を空として送るため、fileから適用するかぎり迂回できる主体は常に存在しない。CIの検査はこの項目を読めないため確認をとばし、書き込み権限のあるtokenで実行したときだけ空であることを確かめる。迂回を許す必要が生じた場合は、本ADRを置き換えて秘匿と検査の方法を決め直す。

### fileが持つ範囲

fileには、人が宣言する`name`、`target`、`enforcement`、`conditions`、`rules`だけを置く。`id`、`node_id`、`created_at`、`updated_at`、`source`はGitHubが割り当てるため持たない。[CONTRIBUTING.md](../../CONTRIBUTING.md#main-の保護設定)は設定値を複製せず、各規則が何を防ぐかと、変更の手順を書く。

## Consequences

- 保護規則が読める形でrepositoryに入り、変更の履歴がgitに残る。
- 規則の変更がpull requestとしてレビューされる。`CP-0061`が`Repository ruleset`のような必須status checkを足す場合も、fileの差分として現れる。
- 実設定が勝手に動けばCIが失敗する。`CP-0083`と同じ失効も、rulesetが読めなくなる時点で検出される。
- `apply`を忘れるとfileと実設定が食い違い、CIが赤くなる。適用は人の操作であり、この赤は「適用していない」ことを示す正しい失敗である。
- `bypass_actors`はCIで検査できない。書き込み権限のあるtokenで`check`を実行したときだけ確認できる。
- GitHubのUIから直接変更する経路は塞がない。塞げないため、CIの検査がその経路を検出する役割を持つ。
- rulesetを持つのは`main`の保護だけである。tag rulesetやorganization rulesetが要る場合は、同じ場所へfileを足す。

## Alternatives considered

- **GitHub側を正とし、fileを記録に留める**: UIから自由に変更でき、記録は後から追いつく。採らなかったのは、変更がpull requestを通らず、記録の更新が忘れられた時点で元の問題へ戻るためである。UIでの都度変更を避けたいという運用上の要求とも合わない。
- **CIからrulesetを自動適用する**: fileと実設定が常に一致し、`apply`の忘れが起きない。採らなかったのは、保護を緩める変更をpull requestで通せてしまい、`main`を守る仕組みが`main`から書き換え可能になるためである。
- **admin権限のPATをsecretへ置き、CIで`bypass_actors`まで検査する**: 検査の範囲は広がる。採らなかったのは、public repositoryでadmin権限のcredentialを持つ危険が、検査できる項目一つに見合わないためである。実装の多くをAIエージェントが行うこのrepositoryでは、被害範囲を広げる判断を避ける。
- **検査を既存のjobへ相乗りさせる**: 必須status checkを増やさずに済む。採らなかったのは、`Documentation`や`Agent configuration`が対象とするものと内容が違い、失敗したときにどの検査が落ちたか読み取りにくくなるためである。fileを正にしたことで、必須指定の追加自体がfileの差分として扱えるようになった。

## Validation

- CIの`Repository ruleset` jobが、fileと実設定の差分を検出して失敗する。`CP-0085`で、規則を1つ落とした場合と`strict_required_status_checks_policy`を変えた場合の両方が検出されることを確認した。
- 次のいずれかが起きた場合に再評価する。
  - `bypass_actors`へ主体を追加する必要が生じる。
  - repositoryをprivateへ戻す判断が出る。未認証での読み取りができなくなり、CIの検査にcredentialが要る。
  - `apply`の忘れが繰り返し起き、手動適用の前提が運用に合わないと分かる。
