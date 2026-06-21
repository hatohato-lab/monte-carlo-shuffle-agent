# 陰性対照: 混ぜないバグ。毎回そのまま返す → 一様性NG（各要素が常に同じ位置）。
def shuffle(xs):
    return list(xs)
