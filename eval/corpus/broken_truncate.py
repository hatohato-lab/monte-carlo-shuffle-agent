# 陰性対照: 1個落とすバグ。長さが変わる → 妥当性NG（並べ替えになっていない）。
import random


def shuffle(xs):
    ys = list(xs)
    random.shuffle(ys)
    return ys[1:]
