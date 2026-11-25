"""Independent, deliberately simple coordinate-based interpretation of the rules.

Stacks are immutable tuples, bottom first. This implementation does not share
ray tables, move-generation code, or stack encodings with the C++ engine.
"""
from dataclasses import dataclass, field


DIRECTIONS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))


def distance(p, q=(0, 0)):
    x, y = p[0] - q[0], p[1] - q[1]
    return max(abs(x), abs(y), abs(x + y))


POSITIONS = tuple((q, r) for q in range(-6, 7) for r in range(-6, 7)
                  if distance((q, r)) <= 6)
INDEX = {p: i for i, p in enumerate(POSITIONS)}
INNER = frozenset(p for p in POSITIONS if distance(p) < 6)


def outer_colors():
    # Six corners are neutral. Along the circumference the thirty remaining
    # fields alternate white/black; the first after (6,0) is white.
    corners = ((6, 0), (0, 6), (-6, 6), (-6, 0), (0, -6), (6, -6))
    result = {p: 2 for p in corners}
    colored_index = 0
    for corner, end in zip(corners, corners[1:] + corners[:1]):
        dq, dr = (end[0] - corner[0]) // 6, (end[1] - corner[1]) // 6
        for step in range(1, 6):
            result[(corner[0] + step*dq, corner[1] + step*dr)] = colored_index % 2
            colored_index += 1
    return result


OUTER = outer_colors()


@dataclass
class State:
    board: dict = field(default_factory=dict)
    reserve: list = field(default_factory=lambda: [18, 18])
    side: int = 0
    passes: int = 0

    def copy(self):
        return State(self.board.copy(), self.reserve.copy(), self.side, self.passes)


def legal(state, variant):
    """All legal actions; no implicit pass action. variant is 'A' or 'B'."""
    b, c = state.board, state.side
    can_place = state.reserve[c] > 0
    can_full = not can_place and (variant == 'B' or not any(state.reserve))
    placements = []
    if can_place:
        occupied = INNER.intersection(b)
        candidates = ({(p[0]+d[0], p[1]+d[1]) for p in occupied for d in DIRECTIONS}
                      if occupied else {(0, 0)})
        placements = [('p', None, p, 0) for p in sorted(candidates)
                      if p in INNER and p not in b]
        if variant == 'A':
            return placements
    if not can_full and not can_place:
        return []
    captures, other = [], []
    for p, stack in b.items():
        if p not in INNER or stack[-1] != c:
            continue
        h = len(stack)
        for dx, dy in DIRECTIONS:
            for n in range(1, h + 1):
                t = (p[0] + dx*n, p[1] + dy*n)
                if t not in INNER and t not in OUTER:
                    break
                if t in b:
                    if n == h and t in INNER and b[t][-1] != c:
                        captures.append(('c', p, t, 0))
                    break
                if t in OUTER:
                    if can_full and n == h and OUTER[t] in (c, 2):
                        other.append(('e', p, t, 0))
                    break
                if can_full:
                    other.append(('m', p, t, 0))
            t = (p[0] + dx, p[1] + dy)
            if can_full and h >= 12 and t in INNER and t not in b:
                for split in range(1, h):
                    if stack[split-1] == c:
                        other.append(('s', p, t, split))
    if can_place:
        return placements + captures
    return captures if captures else other


def apply(state, action):
    kind, origin, target, split = action
    c = state.side
    if kind == 'p':
        state.board[target] = (c,)
        state.reserve[c] -= 1
    elif kind == 's':
        stack = state.board[origin]
        state.board[origin], state.board[target] = stack[:split], stack[split:]
    else:
        state.board[target] = state.board.get(target, ()) + state.board.pop(origin)
    state.side = 1 - c
    state.passes = 0


def scores(state):
    score = [[0, 0], [0, 0]]
    for p, stack in state.board.items():
        if p in OUTER:
            score[stack[-1]][0] += 1
            score[stack[-1]][1] += len(stack)
    return tuple(map(tuple, score))


def result(state, variant):
    """-1 ongoing, 0 white wins, 1 black wins, 2 regular draw."""
    if variant == 'A' and any(state.reserve):
        return -1
    active = {stack[-1] for p, stack in state.board.items() if p in INNER}
    if all(state.reserve[c] > 0 or c in active for c in (0, 1)):
        return -1
    a, b = scores(state)
    return 0 if a > b else 1 if b > a else 2


def key(state):
    return (state.side, tuple(state.reserve), state.passes, tuple(sorted(state.board.items())))


def assert_invariants(state):
    assert state.side in (0, 1)
    assert state.passes in (0, 1, 2)
    assert all(0 <= n <= 18 for n in state.reserve)
    totals = state.reserve.copy()
    for p, stack in state.board.items():
        assert p in INDEX and 1 <= len(stack) <= 36
        assert all(x in (0, 1) for x in stack)
        if p in OUTER:
            assert OUTER[p] in (2, stack[-1])
        for x in stack:
            totals[x] += 1
    assert totals == [18, 18], totals


def indexed(action):
    kind, p, q, k = action
    return (kind, -1 if p is None else INDEX[p], INDEX[q], k)


def stack_tokens(state):
    return [''.join(map(str, state.board[p])) if p in state.board else '-' for p in POSITIONS]
