# Architecture Decision Records

ADRは、複数のコンポーネントへ影響する判断、将来の選択肢を制約する判断、後から理由が分かりにくくなる判断を記録する。

## 状態

| 状態 | 意味 | 現行の根拠か |
| --- | --- | --- |
| `Proposed` | 検討中 | まだ決まっていない |
| `Accepted` | 採用中 | **はい** |
| `Rejected` | 採用しなかった | いいえ |
| `Superseded` | 後続ADRに置き換えられた | いいえ（下の注意を読む） |
| `Deprecated` | 新規利用をやめ、移行中または撤去予定 | 移行が終わるまでの経過措置 |

AcceptedとなったADRは、誤字やリンク切れ以外では結論を書き換えない。判断を変更するときは新しいADRを追加し、双方に置換関係を記載する。**判断が変わっても古いADRを消さないのは、当時その選択を採った理由まで残すためである。** 結論だけを上書きすると、前提が変わったときに何を根拠に選んだのかを再現できず、同じ検討をやり直すことになる。

`Superseded`なADRを根拠として引用する前に、置換したADRを読んで範囲を確かめる。**判断の一部だけが置き換わり、残りは生きている場合がある。** 例として[ADR-0005](0005-separate-runtime-services.md)は`Superseded`だが、置換した[ADR-0012](0012-private-personal-operation.md)は「ADR-0005で決めたAPI、Collection Worker、DBのruntime分離は維持する」と明記しており、置き換わったのはAPIを外部公開する部分だけである。引用するときは、生きている範囲と置換したADRを併記する。

## 文書の構成

ADRは [template.md](template.md) を複製して作る。**5つの節をこの順序で必ず置き、増やさない。** 節を共有することで、読む側がどのADRでも同じ手順で目的の情報へ辿り着ける。

| 節 | 書くこと |
| --- | --- |
| `Context` | どのような状況と制約のもとで判断が必要になったか |
| `Decision` | 何を選択したか、およびその選択を決めた理由 |
| `Consequences` | 得られること、受け入れる制約、必要になる作業 |
| `Alternatives considered` | 比較した選択肢と、採用しなかった理由 |
| `Validation` | 妥当性をいつ何で再評価するか、判断を守る検査 |

該当する内容が無い節も削除しない。無いこと自体が情報であり、節が欠けていると「書き忘れ」と区別できない。

見出しの前に置く項目も5つで固定する。**該当が無い場合は空欄にせず「なし」と書く。**

| 項目 | 値 |
| --- | --- |
| 状態 | 上の5つのいずれか |
| 日付 | 判断した日 |
| 決定者 | 判断した人 |
| 置換するADR | **このADRが置き換えた**古いADR |
| 置換されたADR | **このADRを置き換えた**新しいADR |

置換の2項目は向きが逆である。自分が新しい側なら`置換するADR`へ、古い側なら`置換されたADR`へ相手を書く。同じADRが両方に現れることはない。

`###`の小見出しは`Decision`が複数の対象を扱う場合にだけ使う。[ADR-0016](0016-local-compose-artifact-volume.md)がartifact storage、service構成、health check、migrationを分けているのが例である。他の節では使わない。

## 読みやすさ

ADRは後から読み返して再評価するための文書である。一文が長いと、条件と結果と理由が分離できず、どこが前提でどこが結論かを読み手が組み立て直すことになる。**再評価できない書き方は、結論だけが残った判断と同じ問題を起こす。**

- 一文には一つの論点だけを置く。全角60字を超えたら、条件・結果・理由のどれかを切り出せないか検討する。
- `Consequences`と`Alternatives considered`は箇条書きで書く。並列した項目の列挙であり、散文にすると項目どうしを比較できない。
- `Decision`が複数の対象を扱う場合は`###`で分ける。対象ごとに理由が異なるため、続けて書くとどの理由がどの対象のものか辿れなくなる。
- 比較の軸が3つ以上ある場合は表にする。候補ごとに同じ観点が並ぶ形が、採否の根拠を確認しやすい。
- 文書全体の書き分けは [`write-project-docs`](../../.agents/skills/write-project-docs/SKILL.md) に従う。ここではADR固有の点だけを補う。

## 判断理由の書き方

ADRの価値は、何を選んだかよりも、なぜその選択に至ったかが後から読み取れることにある。結論だけが残った判断は前提が変わったときに再評価できず、同じ検討をやり直すことになる。

- `Decision`には、選択の記述に続けてその選択を決めた理由を書き、理由の中心となる一文を**太字**にする。
- 太字にするのは、他の選択肢ではなくこの選択を採る根拠になった一文に限る。節ごとに一つを目安とし、段落全体や結論そのものを太字にしない。強調が増えるほど、どれが決め手だったかは読み取れなくなる。
- 理由は選択の言い換えにせず、比較対象との差、受け入れた制約、避けたい失敗のいずれかを含む形で書く。「保守しやすいため」のように、反対の選択にも当てはまる書き方にしない。
- `Alternatives considered`には、各選択肢を採用しなかった理由を、`Decision`で強調した理由と対応する観点で書く。
- 判断の前提にした外部の事実には、確認日と参照先を添える。

[ADR-0015](0015-quality-check-toolchain.md)の`Decision`が、この書き方の例になる。

この規則は今後の作成と改訂に適用する。強調を加えるためだけに既存ADRの本文を書き換えない。

## 一覧

| ADR | 状態 | 判断 |
| --- | --- | --- |
| [0001](0001-modular-monolith.md) | Accepted | MVPをPythonのモジュラーモノリスとして構成する |
| [0002](0002-append-only-provenance.md) | Accepted | 原本と価格観測を追記型で保存し、出典を追跡する |
| [0003](0003-mvp-local-storage.md) | Superseded | MVPはSQLiteとローカルファイルシステムを使う |
| [0004](0004-server-database-selection.md) | Accepted | 構造化データをサーバー側DBに置き、製品は比較検証後に選定する |
| [0005](0005-separate-runtime-services.md) | Superseded | API、Collection Worker、DBを別serviceとして扱う |
| [0006](0006-docker-compose-local-development.md) | Accepted | Docker Composeでローカルのservice topologyを再現する |
| [0007](0007-layered-ingestion-data.md) | Accepted | 情報源横断の構造化データを一つの論理DBで管理し、処理段階で分離する |
| [0008](0008-opaque-card-identity-id.md) | Accepted | カード同定には意味を持たない内部UUIDを使い、属性と外部IDを分離する |
| [0009](0009-pokemon-mvp-sources.md) | Superseded | ポケモンカードのMVP情報源に晴れる屋2と遊々亭を選ぶ |
| [0010](0010-pokemon-mvp-source-candidates.md) | Superseded | ポケモンカードのMVP情報源候補に晴れる屋2、遊々亭、フルコンプ池袋店を選ぶ |
| [0011](0011-no-external-source-inquiries.md) | Superseded | MVP情報源を公開条件だけで判断し外部照会を行わない |
| [0012](0012-private-personal-operation.md) | Accepted | Card Pulseを個人用の非公開アプリとして運用する |
| [0013](0013-python-toolchain-and-migrations.md) | Accepted | CPython 3.14、uv、Alembicを開発基盤に採用する |
| [0014](0014-postgresql-self-hosted.md) | Accepted | 構造化データのDBにPostgreSQL 18を採用し、self-hostで運用する |
| [0015](0015-quality-check-toolchain.md) | Accepted | 品質検査にruff、mypy、pytestを採用し、一つのコマンドで実行する |
| [0016](0016-local-compose-artifact-volume.md) | Accepted | ローカル環境のartifact storageをDocker volume上のfilesystemにする |
| [0017](0017-colima-container-runtime.md) | Superseded | ローカル開発のcontainer runtimeにColimaを採用する |
| [0018](0018-per-os-container-runtime.md) | Accepted | container runtimeを選定基準で決め、OSごとに実装を選ぶ |
| [0019](0019-private-repository.md) | Superseded | repositoryをprivateにし、公開範囲をADR-0012へそろえる |
| [0020](0020-public-repository-for-branch-protection.md) | Accepted | repositoryをpublicへ戻し、`main`の保護設定を公開範囲の整合より優先する |
| [0021](0021-ruleset-as-a-file.md) | Accepted | `main`の保護規則をrepository内のfileを正として管理する |
| [0022](0022-configuration-secret-and-local-data-storage.md) | Accepted | 設定を環境変数、秘密情報を`.env`、ローカルデータを`var/`へ集約する |
| [0023](0023-named-volume-for-database-data.md) | Accepted | DBのdata directoryを開発と本番で分けず、named volumeに統一する |

新しいADRは [template.md](template.md) を複製し、4桁の連番と短いslugを付ける。

## ADR管理の機械検査

2026-09-12にADR-0013を追加して13件となったため、専用validatorの導入を再検討し、引き続き見送った。一覧、状態、日付、必須section、置換関係は一つの変更内で確認でき、既存の文書リンク検査がファイルと参照の欠落を検出する。追加した5件を含めてID、状態、一覧、置換関係の不整合は発生しておらず、現時点では検査規則とCIの保守対象を増やす具体的な効果が小さい。

ADRが20件へ達した場合、または状態遷移、置換関係、一覧更新の不整合が発生した時点で、専用validatorを再検討する。

2026-09-15に23件へ達し、`CP-0096`のヘッダ項目の点検で不整合が6件見つかった（ADR-0001・0002・0006が3項目欠落、ADR-0003が3項目欠落と独自ラベル`後継ADR`、ADR-0004・0005が1項目欠落）。件数と不整合の両方で再検討条件を満たしたため、`CP-0086`で専用validatorを導入した。**見送りを続けなかったのは、この6件が規則の存在しなかった時期に生まれており、`CP-0096`で規則を文章にしただけでは同じ経路で再発するためである。**

`.agents/skills/write-project-docs/scripts/validate_adrs.py`が次を検査し、CIの`Documentation` jobで実行する。

- 5つの節が[文書の構成](#文書の構成)の順序で存在すること
- ヘッダ5項目が同じ順序で存在し、該当が無い欄が「なし」であること
- 状態が[状態](#状態)の5つのいずれかで、日付が`YYYY-MM-DD`であること
- 置換関係が双方のADRに書かれ、置換された側の状態が`Superseded`であること
- 上の一覧表が全ADRを列挙し、状態がファイルと一致すること
- `###`が`Decision`の中だけで使われ、タイトルの番号がファイル名と一致すること

読みやすさの指針（[読みやすさ](#読みやすさ)）は検査しない。一文が長くても明快な場合はあり、機械が一律に却下すると書き手の判断を奪う。60字はあくまで分割を検討する目安であり、合否の線ではない。

次に再検討するのは、検査が実態に合わず回避されるようになった場合、または節・ヘッダ以外の不整合（本文の重複、理由の欠落など）が繰り返し発生した場合とする。
