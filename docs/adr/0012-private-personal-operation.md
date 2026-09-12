# ADR-0012: Card Pulseを個人用の非公開アプリとして運用する

- 状態: Accepted
- 日付: 2026-09-12
- 決定者: プロジェクトオーナー
- 置換するADR: [ADR-0005](0005-separate-runtime-services.md)、[ADR-0011](0011-no-external-source-inquiries.md)
- 置換されたADR: なし

## Context

[ADR-0011](0011-no-external-source-inquiries.md)では、情報源の運営者へ外部照会を行わず、公開条件だけで自動取得、原本保存、fixture、派生利用を確認できる情報源だけを採用する方針を選んだ。この条件では調査済みの情報源を採用できず、Web Collectorの実装へ進めない。

プロジェクトオーナーは、Card Pulseを自分だけが使う非公開アプリとし、ソースコード、取得原本、source由来fixture、抽出値、価格履歴、APIを第三者へ公開または提供しないことを決定した。情報源の運営者への照会と、公開条件による個別許諾の確認は開発の前提にしない。

[文化庁の2025年度著作権セミナー資料](https://www.bunka.go.jp/seisaku/chosakuken/seidokaisetsu/seminar/2025/pdf/94270801_01.pdf)は、本人が個人的または家庭内等の限られた範囲で行う複製を私的使用の例として説明する一方、仕事での利用と技術的保護手段の回避等を対象外としている。確認日は2026-09-12である。Card Pulseは仕入れ・売却判断に使うため、個人用・非公開という事実だけで私的使用に当たるとは判断しない。この一般的な説明を、各情報源の自動取得、契約条件、保存方法が包括的に許可されたという根拠にも使わない。本ADRは、利用者と公開範囲を限定したプロジェクトオーナーのリスク判断を記録するものであり、個別の法的評価ではない。

[ADR-0005](0005-separate-runtime-services.md)で決めたAPI、Collection Worker、DBのruntime分離は維持する。一方、APIだけを外部公開する構成は個人用アプリの範囲を超えるため、本ADRで非公開構成へ変更する。

## Decision

- Card Pulseの利用者はプロジェクトオーナー本人に限定し、アプリ、API、取得データを一般公開、第三者提供、または第三者向けサービスとして販売しない。
- API、Collection Worker、DB、artifact storageは本人が管理する端末またはprivate network内だけで実行する。APIは既定でloopbackまたはCompose内部networkにbindし、Internetから到達可能にしない。
- API、Collection Worker、DBを別runtime serviceとして扱う設計は維持する。これは公開サービス化のためではなく、障害分離、権限分離、再現可能なローカル運用のために使う。
- MVPのWeb情報源には晴れる屋2、遊々亭、フルコンプ池袋店を採用する。最初に晴れる屋2を縦に実装し、遊々亭、フルコンプ池袋店の順で追加する。
- 取得は認証なしで通常閲覧できる公開URLだけを対象とする。HTTP clientがその未認証の通常閲覧中に受け取るCookieは、同じ取込実行内の一時的なcookie jarで利用でき、実行終了時に破棄する。ブラウザprofileから取り出したCookie、ログイン済みsession、他者から受け取ったCookie、challenge通過用tokenは取得へ使わない。
- CAPTCHAやCloudflare challengeの解答・回避、アクセス制御の迂回は行わない。403、429、CAPTCHA、challengeを受けた情報源は再試行せず停止する。通常requestでchallengeなしに取得できるCloudflare配下の公開ページまで禁止するものではない。
- 取得はsourceごとに逐次実行し、既存調査の技術案を上限として、晴れる屋2は日次1回以下の条件付きGET、遊々亭は日次1回以下かつrequest間隔60秒以上、フルコンプ池袋店は日次1回以下で更新された価格表だけを取得する。
- raw artifact、抽出履歴、source由来fixtureは本人のローカル保存領域に限定する。Git、CI artifact、公開backupへ含めず、`var/`配下または同等のGit管理外領域へ保存する。
- repositoryとCIで共有するfixtureはsource非由来の合成データだけにする。source由来fixtureを使うparser regression testは本人のローカル環境だけで実行する。
- Card Diggerとの連携は同じプロジェクトオーナーが管理する端末間に限定する。hostをまたぐ場合はprivate networkと認証を使い、Internetへ公開しない。
- 情報源の運営者への照会と、利用条件を満たすことの再確認はロードマップの完了条件にしない。HTML構造、データ品質、取得失敗、明示的なアクセス拒否は実装と運用で監視する。

## Consequences

- `CP-0074`で取得経路が確定し、Phase 1以降の基盤実装とPhase 3のWeb Collector実装へ進める。
- 公開API、第三者向けデータ提供、公開fixture、クラウド上の共有運用はMVPから外れる。
- 取得原本を使ったparser regression testはCIで再現しないため、合成fixtureによるcontract testとローカルのsource由来fixtureによるtestを分ける必要がある。
- 利用範囲を個人・非公開に限定しても、各情報源の利用条件やアクセス制御に関する不確実性は残る。明示的な拒否または技術的な遮断が生じた場合は、そのsourceを停止して保存済みデータと他sourceの処理を継続する。
- 将来、利用者の追加、repositoryの公開、Internetから到達可能なhostへの配置、データ共有、第三者向け提供または販売のいずれかを行う場合は、本ADRの前提を外れる。実施前に新しいADRで利用条件、データ削除、公開範囲、認証を再判断する。

## Alternatives considered

- 公開条件だけで明示許可された情報源を探し続ける: 不確実性を下げられるが、MVPの基盤実装が情報源探索に依存し続けるため採用しない。
- 手動ファイルと合成データだけで進める: 取込、保存、同定は検証できるが、Web取得の継続性、parser変更、実価格の有用性を検証できないため主経路にはしない。
- 公開Webサービスとして構築する: 複数端末から利用しやすいが、今回決定した個人・非公開の範囲を超えるため採用しない。
- アクセス制御を回避して取得する: 情報源が示した技術的な拒否を無視するため採用しない。

## Validation

- API、DB、artifact storageがInternetから到達不能で、APIが既定でloopbackまたはCompose内部networkだけにbindすることをtestまたは構成検査で確認する。
- GitとCIへsource由来fixture、raw artifact、抽出値、価格履歴が含まれないことを検査する。
- sourceごとの逐次実行、取得上限、403・429・CAPTCHA・challenge時の即時停止を設定とtestで確認する。
- cookie jarが取込実行ごとに新規作成・破棄され、ブラウザprofile、認証済みsession、他者から受け取ったCookie、challenge通過用tokenを読み込まないことをtestで確認する。
- 合成fixtureだけでCIのCollector contract testが成功し、本人のローカル環境ではGit管理外fixtureからparser regression testを実行できるようにする。
- 公開、共有、利用者追加、第三者向け提供または販売へ範囲を変更する場合は、実装または配置より先に新しいADRを作成する。
