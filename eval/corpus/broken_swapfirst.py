# 陰性対照: 先頭2つだけ交換するバグ。位置2以降が固定 → 一様性NG。
def shuffle(xs):
    ys = list(xs)
    if len(ys) >= 2:
        ys[0], ys[1] = ys[1], ys[0]
    return ys
