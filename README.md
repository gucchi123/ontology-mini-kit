# ontology-mini-kit — 「社内オントロジー mini」で AI エージェントに業務を完遂させる実験キット

コンビニ 1 店舗の発注業務を題材に、**名詞・動詞・権限**を JSON 1 枚で定義し、6 コマンドの小さなツールを通して AI エージェントに発注を任せ、**オントロジーあり (A) / なし (B)** で挙動の差をログから数えるためのキットです。

連載「FDE シリーズ」(AIフロンティア) の第 4 回・第 7 回で使った実験 (exp01) そのものです。

- 第 4 回: オントロジーがある AI / ない AI — 検証してみた  https://xs232654.xsrv.jp/ontology-intro-2-with-vs-without-experiment/
- 第 7 回: 手を動かす — 「社内オントロジー mini」を JSON で定義してエージェントに発注業務を完遂させる (公開後にリンクを追記)

## 中身

| ファイル | 役割 |
|---|---|
| `ontology.json` | 名詞 (Product / Supplier / Shelf / SalesRecord / Forecast / Order)・動詞 (recommend_qty / propose_order / confirm_order / request_approval)・権限ルール |
| `data.json` | ダミーの本番データ (商品 3 SKU・仕入先・棚・直近 7 日の売上・天気予報・発注) |
| `tools.py` | エージェントに渡す CLI。全呼び出しを `run/calls.log` に 1 行 1 JSON で記録。権限判断は **ツール側** で行う |
| `run_ab.py` | A/B 実験ランナー。Claude Code ヘッドレス (`claude -p`) をエージェントとして起動し、試行ごとに `runs/<A1..B3>/summary.json` を作る。`report` で `results.md` を生成 |
| `RESULTS_exp01.md` | 筆者環境での実行結果 (2026-08-22, A×3 / B×3) |

## 使い方

```bash
# 1) ツールを手で触ってみる
python tools.py describe_ontology
python tools.py list_tables
python tools.py recommend_qty ONG-SALMON 2026-08-23
python tools.py propose_order ONG-SALMON 60 2026-08-23
python tools.py confirm_order ORD-001 ai_agent     # ±20% ルールで拒否される
python tools.py request_approval ORD-001 "店長メモにより 60 個。推奨 40 個を超えるため承認依頼"

# 2) エージェントに任せて A/B を回す (Claude Code CLI が必要。別エージェントなら run_trial() の cmd を差し替え)
python run_ab.py A 1 2 3
python run_ab.py B 1 2 3
python run_ab.py report        # -> results.md
```

`run_ab.py` は `claude` が PATH にある前提です。別の場所にある場合は環境変数 `CLAUDE_BIN` で指定してください。

## 何を測るか

| 指標 | 見方 |
|---|---|
| ツール呼び出し回数 | 手数。A/B でほぼ差は出ない (19.0 vs 20.0) |
| 確定拒否の回数 | B は「拒否されてから条件を知る」ので多い |
| 数量を変えて再提案し自動確定 | B は推奨 19 → 21 個に変えて ±20% に入れた (3/3)。A は 0/3 |
| 孤児オーダー (proposed のまま残る) | B は元の提案を片づけずに去った (3/3) |
| 文言と実装のズレを報告 | A は ontology.json を読んでいるので矛盾に気づける (A2) |

詳しくは `RESULTS_exp01.md` と連載第 4 回・第 7 回を参照してください。

## 自分の業務に置き換える

1. 名詞 10 個・動詞 5 個・権限表を紙 1 枚に書く
2. 「状態を変える動詞」だけ拒否ロジックを入れてツール化する (`confirm_order` を真似る)
3. ログを 1 行 1 呼び出しで残す
4. あり / なしで 3 回ずつ走らせ、上の表を埋める

## ライセンス

MIT
