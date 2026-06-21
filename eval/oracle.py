#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oracle.py — モンテカルロ（統計的）オラクル。

非決定な処理（シャッフル）を、1回でなく「多数回実行した集計のふるまい」で判定する。
候補 shuffle(xs) が、固定種で N 回実行したとき
  (a) 妥当性: 毎回、入力の並べ替え（同じ要素・同じ個数）になっている。
  (b) 一様性: 各位置に各要素がほぼ均等に来る（位置ごとのカイ二乗が閾値未満）。
を満たすときだけ PASS。種を固定するので結果は再現可能。

使い方:
  python oracle.py                  # reference.py（正例）を採点
  python oracle.py --candidate NAME # NAME.py（エージェント出力）を採点
  python oracle.py --selftest       # オラクル自身を検証（正例→PASS / 既知バグ→FAIL）
終了コード: PASS（または selftest 期待どおり）で 0、それ以外 1。
"""
import argparse
import importlib.util
import random
import sys
from collections import Counter
from pathlib import Path

# Windows コンソール(cp932)でも日本語・記号を出せるよう出力を UTF-8 に統一。
# Linux/Mac は元から UTF-8 なので無害。これが無いと Windows で print が落ちる。
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

EVAL = Path(__file__).resolve().parent
CORPUS = EVAL / "corpus"
K = 6          # 要素数（range(K) を並べ替える）
N = 3000       # 実行回数
SEED = 12345   # 種固定（再現可能）
CHI2_MAX = 40.0  # 位置ごとカイ二乗の上限（df=5・α=0.001 の臨界≈20.5 に余裕を持たせた値）


def load(path):
    spec = importlib.util.spec_from_file_location("cand_" + path.stem, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if not hasattr(m, "shuffle"):
        raise AttributeError(f"{path.name} に shuffle(xs) が無い")
    return m.shuffle


def evaluate(shuffle):
    random.seed(SEED)
    base = list(range(K))
    want = Counter(base)
    counts = [[0] * K for _ in range(K)]  # counts[位置][要素]
    bad = None
    for _ in range(N):
        out = shuffle(list(base))
        if len(out) != K or Counter(out) != want:
            if bad is None:
                bad = out
            continue
        for pos, e in enumerate(out):
            counts[pos][e] += 1
    if bad is not None:
        return ("FAIL", f"妥当性NG: 並べ替えでない出力 {bad!r}")
    exp = N / K
    worst = 0.0
    for pos in range(K):
        chi = sum((counts[pos][e] - exp) ** 2 / exp for e in range(K))
        worst = max(worst, chi)
    if worst < CHI2_MAX:
        return ("PASS", f"一様（最大χ²={worst:.1f} < {CHI2_MAX}）")
    return ("FAIL", f"一様性NG: 偏り（最大χ²={worst:.1f} ≥ {CHI2_MAX}）")


def grade(path):
    try:
        sh = load(path)
    except Exception as e:
        return ("FAIL", f"読込失敗: {e}")
    try:
        return evaluate(sh)
    except Exception as e:
        return ("FAIL", f"実行エラー: {type(e).__name__}: {e}")


def table(rows, title):
    print(f"\n### {title}")
    print("| 対象 | 判定 | 詳細 |")
    print("|---|---|---|")
    for n, v, d in rows:
        print(f"| {n} | {v} | {d} |")


def selftest():
    print("# オラクル自己検証 — モンテカルロ（統計的）シャッフル")
    rv, rd = grade(CORPUS / "reference.py")
    table([("reference", rv, rd)], "① 正しいシャッフル reference（PASS であるべき）")
    controls = [
        ("broken_identity.py", "混ぜないバグ → 一様性NG"),
        ("broken_swapfirst.py", "先頭2つだけ交換 → 一様性NG"),
        ("broken_truncate.py", "1個落とすバグ → 妥当性NG"),
    ]
    brows, caught = [], True
    for f, why in controls:
        v, d = grade(CORPUS / f)
        ok = (v == "FAIL")
        caught = caught and ok
        brows.append((f, v, ("検出OK " if ok else "検出NG ") + d))
    table(brows, "② 壊れた実装（FAIL であるべき）")
    valid = (rv == "PASS") and caught
    print(f"\n## オラクル判定: {'PASS（バグを捕まえ正例を通す＝信頼できる）' if valid else 'FAIL（オラクル自体に欠陥）'}")
    return valid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", default="reference")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    v, d = grade(CORPUS / f"{a.candidate}.py")
    table([(f"{a.candidate}.py", v, d)], "採点（モンテカルロ）")
    sys.exit(0 if v == "PASS" else 1)


if __name__ == "__main__":
    main()
