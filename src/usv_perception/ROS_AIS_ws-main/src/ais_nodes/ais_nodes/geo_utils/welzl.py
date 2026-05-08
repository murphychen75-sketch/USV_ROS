import numpy as np
from typing import Tuple
from random import shuffle


def circle_from_two_pts(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
) -> Tuple[float, float, float]:
    # center
    cx, cy = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    r = np.hypot(p1[0] - cx, p1[1] - cy)
    return (cx, cy, r)


def circle_from_three_pts(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
) -> Tuple[float, float, float]:
    ax, ay = p1
    bx, by = p2
    cx, cy = p3

    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if d == 0:  # three pts on one line
        return circle_from_two_pts(p1, p2)

    ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
    uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
    r = np.hypot(ax - ux, ay - uy)

    return (ux, uy, r)


def min_circle_trivial(R) -> Tuple[float, float, float]:
    """
    trivial case:
        find min circle for point set with 0, 1, 2, 3 points
    return:
        x, y, r
    """
    # no points
    if len(R) == 0:
        return (0, 0, 0)
    # 1 point, circle with the point as center and radius == 0
    elif len(R) == 1:
        point = R[0]
        return (point[0], point[1], 0)
    # 2 points, circle with this two points as diameter
    elif len(R) == 2:
        return circle_from_two_pts(R[0], R[1])
    # 3 points circle
    elif len(R) == 3:
        return circle_from_three_pts(R[0], R[1], R[2])
    else:
        raise Exception


def welzl(P, R=[]) -> Tuple[float, float, float]:
    P = P.copy()
    R = R.copy()

    if len(P) == 0 or len(R) == 3:
        return min_circle_trivial(R)

    else:
        # choose p from P randomly
        shuffle(P)
        p = P.pop()
        # calcul min circle without p
        circle = welzl(P, R)
        # if p outside circle, p is a boudary pt, add it to R
        if np.hypot(p[0] - circle[0], p[1] - circle[1]) > circle[2]:
            circle = welzl(P, R+[p])
        # else p is an inside pt, do nothing
        # return
        return circle


if __name__ == "__main__":
    P = [
        (1, 0),
        (2, 0),
        (3, 0),
        (4, 0),
        (2.5, 3),
    ]
    print(welzl(P))