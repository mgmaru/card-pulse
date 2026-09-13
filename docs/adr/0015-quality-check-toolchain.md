# ADR-0015: 品質検査にruff、mypy、pytestを採用し、一つのコマンドで実行する

- 状態: Accepted
- 日付: 2026-09-13
- 決定者: プロジェクトオーナー
- 置換するADR: なし
- 置換されたADR: なし

## Context

[ADR-0013](0013-python-toolchain-and-migrations.md)はCPython 3.14とuvを採用し、開発依存と品質検査コマンドの具体化を`CP-0013`へ残した。`CP-0011`で作成したのは責務境界を表すpackage骨格だけで、lint、format、型チェック、testはまだ一つも定義されていない。

この空白は二つの作業を止めている。`CP-0060`はformat、lint、型チェック、unit testをGitHub Actionsへ追加するが、ローカルで何を実行するかが決まらなければCIも定義できない。また[CONTRIBUTING.md](../../CONTRIBUTING.md)は具体的なコマンドの記載を保留したままで、変更を提出する側が検査を再現できない。

ドメイン実装が無い現時点は、厳しい既定値を選ぶ費用が最も小さい。規則違反が蓄積してから型チェックを厳格化すると、既存コードの修正と新しい規則の適用が同じ変更に混ざる。

判断に使うtoolのversionは2026-09-13にPyPIで確認した。

| tool | 確認したversion | 根拠 |
| --- | --- | --- |
| ruff | 0.16.7 | [ruff](https://pypi.org/project/ruff/)、[ドキュメント](https://docs.astral.sh/ruff/) |
| mypy | 2.3.1 | [mypy](https://pypi.org/project/mypy/)、[ドキュメント](https://mypy.readthedocs.io/en/stable/index.html) |
| pytest | 9.1.1 | [pytest](https://pypi.org/project/pytest/)、[ドキュメント](https://docs.pytest.org/en/stable/) |
| ty | 0.0.80 | [ty](https://pypi.org/project/ty/)。README上はbeta段階 |
| pyright | 1.1.414 | [pyright](https://pypi.org/project/pyright/) |

検査対象の範囲には、Python runtimeが揃っていない領域が二つある。`.agents/skills/*/scripts/`の検査scriptは、CodexとClaude Code、そしてCIが素の`python3`で実行する。これは固定した3.14ではなく、実行環境ごとに異なるminor versionになる。`scripts/db_poc/`は`CP-0009`の測定harnessで、独自の`pyproject.toml`と`uv.lock`を持ち、[PoC結果](../research/database-poc-2026-09.md)の根拠として凍結している。

## Decision

### 採用するtool

- lintとformatにruffを使う。一つのtoolと一つの設定で両方を扱えるため、formatterとlinterの規則衝突を調停する必要がない。
- 型チェックにmypyを使い、`strict`を既定にする。
- testにpytestを使う。

開発依存は[ADR-0013](0013-python-toolchain-and-migrations.md)に従い`pyproject.toml`の`[dependency-groups]`の`dev`へ記録する。正確なversionは`uv.lock`で固定し、`pyproject.toml`には互換性を壊す更新だけを除外する範囲（ruffは`<0.17`、mypyは`<3`、pytestは`<10`）を書く。ruffは1.0前であり、minor版でformat結果とlint規則が変わり得るため、他の二つより狭い範囲にする。

### コマンド

setupは`uv sync --locked`とする。個別の検査は`uv run --locked`を通して実行し、`uv.lock`と`pyproject.toml`が食い違う環境では検査自体を失敗させる。

| 目的 | コマンド |
| --- | --- |
| setup | `uv sync --locked` |
| format（適用） | `uv run --locked ruff format` |
| format（検査） | `uv run --locked ruff format --check` |
| lint | `uv run --locked ruff check` |
| 型チェック | `uv run --locked mypy` |
| test | `uv run --locked pytest` |
| 全検査 | `python3 scripts/check.py` |

`scripts/check.py`はformat、lint、型チェック、testをこの順で実行する。失敗した段階で打ち切らず、最後に段階ごとの成否をまとめて出力し、一つでも失敗すれば非zeroで終了する。一度の実行で全ての問題を報告するためであり、format違反の修正とtest失敗の修正を別々の往復に分けない。段階名を引数に与えれば部分実行できる。

このscriptをローカルとCIの共通の入口とする。`CP-0060`はこのコマンドを呼ぶjobを追加するだけで済み、検査内容がCI側の設定として二重に定義されることを防ぐ。scriptは`uv`と`python3`だけを前提とし、依存をinstallする前でも実行できる。

`pyproject.toml`の`[tool.ruff]`、`[tool.mypy]`、`[tool.pytest.ini_options]`を規則と対象範囲の正とする。この文書には規則名を複製しない。

### 検査対象の範囲

`src/`、`tests/`、`scripts/`を対象とし、次の二つを除く。

- `.agents/skills/*/scripts/`: 素の`python3`で実行するため、`requires-python = ">=3.14"`から導かれる規則、特に新しい構文への書き換えを適用すると、実行できる環境を狭めてしまう。これらのscriptはCIが毎回実行して終了codeを検査しており、動作は継続的に確認されている。
- `scripts/db_poc/`: 独立したprojectであり、記録として凍結する。

domainがadapterをimportしないといった層の依存規則は、lintでは強制しない。ruffの相対import禁止で層をまたぐimportを読み取れる形にはするが、境界そのものの検査は`CP-0017`の契約testで行う。

## Consequences

- ローカルとCIが同じlock、同じPython version、同じtool versionで検査する。`CP-0060`はjobの追加だけになる。
- 最初のドメイン実装から型注釈が必須になる。`strict`の緩和が必要な箇所は、対象を限定した設定として`pyproject.toml`へ理由とともに残す。
- toolのversion更新は`uv lock`による明示的な変更になる。更新時に新しい規則違反やformat差分が出ることは想定内で、通常の変更として扱う。
- ruffのminor更新はformat結果を変え得るため、更新と機能変更を同じcommitへ混ぜない。
- `.agents/skills/*/scripts/`はこれらのtoolの対象外のままになる。これらのscriptが増える場合、または固定したruntimeで実行する構成へ移す場合に、対象へ加えるかを再検討する。
- runtime依存を追加する際は、`uv.lock`の更新後に全検査を通して、型stubの不足やlint規則との衝突を検出する。

## Alternatives considered

- black、flake8、isortの組み合わせ: 広く使われているが、toolと設定が三つに増え、formatterとlinterの規則衝突を自分で調停することになる。ruffが同じ役割を一つの設定で満たすため採用しない。
- 型チェックにty: ruff、uvと同じ提供元で高速だが、2026-09-13時点で0.0.80のbeta段階であり、診断結果と設定が変わり得る。最初の品質基準を置く土台にはしない。1.0到達時に、mypyと同じコードへ適用して比較し、再検討する。
- 型チェックにpyright: 成熟しているが、Node.js runtimeか別配布のbinaryが必要になり、uvへ揃えたtoolchainへ二つ目の実行環境を持ち込む。
- Makefileまたはjust: task runnerとしては簡潔だが、`make`または追加toolへの依存が増える。このリポジトリは既に検査scriptを`python3`のscriptとして提供し、人とCIが同じ方法で呼んでいるため、同じ形に揃える。
- 集約scriptを作らず4つのコマンドを文書化するだけ: 設定は減るが、CI側が同じ内容を書き写すことになり、ローカルとCIの乖離を防ぐ手段が文書だけになる。
- 検査をCIだけで実行する: ローカルの手順は減るが、失敗の発見がpush後になり、修正の往復が長くなる。

## Validation

- `CP-0060`で`scripts/check.py`を実行するCI jobを追加し、pull requestで成功することを確認する。
- 最初のドメイン実装とCollector実装で、`strict`な型チェックと選択した規則が実際のコードで過剰でないかを確認する。恒常的に抑制が必要な規則が出た場合は設定を変更し、理由を記録する。
- tyが1.0へ到達した時点で、mypyとの比較を行い、型チェックtoolを再判断する。
- `.agents/skills/*/scripts/`を対象へ加えるかは、これらのscriptが増えるか、固定runtimeで実行する構成になった時点で再検討する。
- CPython、uv、または品質検査toolのmajor更新時に、この判断を再評価する。
