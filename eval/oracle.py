#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oracle.py — モンテカルロ（統計的）オラクル。

非決定な処理（シャッフル）を、1回でなく「多数回実行した集計のふるまい」で判定する。
候補 shuffle(xs) が、固定種で多数回実行したとき
  (a) 妥当性: 出力が入力の並べ替え（同じ要素・同じ個数）で、引数を破壊しない。
      重複要素・空リスト・長さ1の入力でも成り立つ。
  (b) 一様性(位置): 各位置に各要素がほぼ均等に来る（位置ごとのカイ二乗が閾値未満）。
  (c) 一様性(順列): 並びそのものが 4!=24 通りにほぼ均等に散らばる
      （順列度数のカイ二乗が閾値未満）。位置ごとの分布だけが均等な
      「巡回シフト」型のすり抜けをここで塞ぐ。
をすべて満たすときだけ PASS。種を固定するので結果は再現可能（決定的）。

使い方:
  python oracle.py                  # reference.py（正例）を採点
  python oracle.py --candidate NAME # NAME.py（エージェント出力）を採点
  python oracle.py --selftest       # オラクル自身を検証（正例→PASS / 既知バグ→FAIL）
終了コード: PASS（または selftest 期待どおり）で 0、それ以外 1。

注意: 候補コードはサンドボックス無しで import 実行する。
信頼できないコードを採点することは、任意コード実行と同じ意味を持つ。
"""
import argparse
import importlib.util
import itertools
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
SEED = 12345   # 種固定（再現可能・決定的）

# --- (b) 位置ごと周辺分布の一様性 ---
K = 6          # 要素数（range(K) を並べ替える）
N = 3000       # 実行回数
CHI2_MAX = 40.0  # 位置ごとカイ二乗の上限（df=5・α=0.001 の臨界≈20.5 に余裕を持たせた値）

# --- (c) 順列全体の一様性 ---
PERM_K = 4     # 要素数。4! = 24 通り。期待度数 PERM_N/24 = 125 ≫ 5 で χ² 近似が妥当。
PERM_N = 3000  # 実行回数
# 上限の根拠: df = 24-1 = 23・α = 0.001 のカイ二乗臨界値 ≈ 49.73 を切り上げた値。
# 種固定で統計量は決定的（SEED=12345 の reference は χ²=27.3 で十分下回る）ため、
# 臨界値以上の余裕は持たせない。
PERM_CHI2_MAX = 50.0

# --- (a) 妥当性チェックの入力形状 ---
# 要素値はわざと 0..K-1 以外（10 など）にする。入力を無視して range(K) や
# その並べ替えを返す実装が、多重集合の不一致で FAIL するようにするため。
VALIDITY_CASES = [
    ("相異なる4要素", [10, 20, 30, 40]),
    ("重複あり", [10, 10, 20, 30]),
    ("空リスト", []),
    ("長さ1", [10]),
]
VALIDITY_REPEAT = 50  # 各形状の実行回数（毎回の出力に多重集合の保存を要求）


def load(path):
    spec = importlib.util.spec_from_file_location("cand_" + path.stem, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if not hasattr(m, "shuffle"):
        raise AttributeError(f"{path.name} に shuffle(xs) が無い")
    return m.shuffle


def check_validity(shuffle):
    """(a) 妥当性: 出力が入力の並べ替えで、引数を破壊しないこと。
    引数はコピーせず同一オブジェクトのまま渡し、呼び出し後にその中身が
    変わっていないかを見る（非破壊性の検証）。NG なら理由、OK なら None。"""
    for name, case in VALIDITY_CASES:
        want = Counter(case)
        for _ in range(VALIDITY_REPEAT):
            arg = list(case)   # この arg 自体を渡す（オラクル側でコピーしない）
            out = shuffle(arg)
            if arg != case:
                return f"妥当性NG({name}): 引数を破壊 {case!r} → {arg!r}"
            if not isinstance(out, list) or Counter(out) != want:
                return f"妥当性NG({name}): 並べ替えでない出力 {out!r}（入力 {case!r}）"
    return None


def evaluate(shuffle):
    random.seed(SEED)

    # (a) 妥当性（非破壊性・多重集合の保存。重複／空／長さ1も）
    bad = check_validity(shuffle)
    if bad is not None:
        return ("FAIL", bad)

    # (b) 一様性(位置): 各位置に各要素がほぼ均等に来るか
    base = list(range(K))
    want = Counter(base)
    counts = [[0] * K for _ in range(K)]  # counts[位置][要素]
    for _ in range(N):
        out = shuffle(list(base))
        if len(out) != K or Counter(out) != want:
            return ("FAIL", f"妥当性NG: 並べ替えでない出力 {out!r}")
        for pos, e in enumerate(out):
            counts[pos][e] += 1
    exp = N / K
    worst = 0.0
    for pos in range(K):
        chi = sum((counts[pos][e] - exp) ** 2 / exp for e in range(K))
        worst = max(worst, chi)
    if worst >= CHI2_MAX:
        return ("FAIL", f"一様性NG(位置): 偏り（最大χ²={worst:.1f} ≥ {CHI2_MAX}）")

    # (c) 一様性(順列): 並びそのものが 4!=24 通りに均等に散らばるか。
    # 位置ごとの分布は均等でも出せる並びが数種類しかない実装（例: 巡回シフト）はここで落ちる。
    perm_base = [10, 20, 30, 40]
    index = {p: i for i, p in enumerate(itertools.permutations(perm_base))}
    freq = [0] * len(index)
    for _ in range(PERM_N):
        out = shuffle(list(perm_base))
        i = index.get(tuple(out))
        if i is None:
            return ("FAIL", f"妥当性NG: 並べ替えでない出力 {out!r}")
        freq[i] += 1
    exp = PERM_N / len(index)
    perm_chi = sum((c - exp) ** 2 / exp for c in freq)
    if perm_chi >= PERM_CHI2_MAX:
        return ("FAIL", f"一様性NG(順列): 24通りの並びに偏り（χ²={perm_chi:.1f} ≥ {PERM_CHI2_MAX}）")

    return ("PASS", f"一様（位置 最大χ²={worst:.1f} < {CHI2_MAX} / 順列 χ²={perm_chi:.1f} < {PERM_CHI2_MAX}）")


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
    # (ファイル名, 期待する壊れ方, FAIL理由に含まれるべき語)
    # broken_rotate は「位置ごとの周辺分布検定はすり抜けるが、順列検定で落ちる」
    # ことまで確認するため、FAIL 理由が 一様性NG(順列) であることも要求する。
    controls = [
        ("broken_identity.py", "混ぜないバグ → 一様性NG", None),
        ("broken_swapfirst.py", "先頭2つだけ交換 → 一様性NG", None),
        ("broken_truncate.py", "1個落とすバグ → 妥当性NG", None),
        ("broken_rotate.py", "巡回シフト → 位置ごとは均等でも順列でNG", "一様性NG(順列)"),
    ]
    brows, caught = [], True
    for f, why, need in controls:
        v, d = grade(CORPUS / f)
        ok = (v == "FAIL") and (need is None or need in d)
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
