# 正例（陽性対照）: 正しいシャッフル。random モジュール（オラクルが種を固定する）を使う。
import random


def shuffle(xs):
    ys = list(xs)
    random.shuffle(ys)
    return ys
