# CLAUDE.md — monte-carlo-shuffle-agent

このリポジトリは「リストをランダムに並べ替える」エージェントと、その採点係（モンテカルロ統計）です。
出力が毎回変わる非決定処理を、多数回実行した統計（妥当性＋カイ二乗による一様性）で判定します。

## 確認のしかた

- `python eval/oracle.py --selftest` … 採点係が正しいか（正例=PASS／既知バグ=FAIL）
- `python eval/oracle.py --candidate candidate` … エージェントの答え（`eval/corpus/candidate.py`）を採点
- `python eval/oracle.py` … お手本(reference.py)を採点

## いじるときの約束（評価駆動 / EDD）

- 先に eval（合否の基準）を満たすことを確認してから「完成」とする。雰囲気で done にしない。
- `eval/corpus/reference.py` と `broken_*.py` は採点係の検証用。むやみに変えない。
- Python 標準ライブラリのみ。秘密情報・個人情報・客先コードを入れない。

## ファイルの役割

- `.claude/agents/monte-carlo-shuffle-agent.md` … エージェント定義
- `eval/oracle.py` … 採点係（モンテカルロ統計）／`design/design.md` … 設計／`README.md` … 説明
