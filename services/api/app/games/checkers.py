"""Checkers Corner: a classic checkers board between two classmates.

Two seats, one board. The server owns the rules — whose turn it is, which moves are legal,
when a piece becomes a king — so neither client can bend them. Free play like every game
here: no score reaches the teacher, and either player can reset the board at any time.
Captures are never forced and a jump ends the turn, which keeps the game friendly for
learners meeting checkers for the first time.
"""

from __future__ import annotations

from typing import Any, Optional

from .base import GameSpec

GAME = GameSpec(
    id="checkers",
    title="Checkers Corner",
    glyph="🔴",
    tone="rose",
    blurb="A friendly game of checkers with a classmate.",
    instructions="Take turns moving one checker diagonally. Jump over a classmate's checker to collect it, and reach the far side to earn a crown.",
    skill_hint="Planning ahead",
    grouping_skill_id=None,
    min_group=2,
    max_group=2,
    solo=False,
    teacher_note="Exactly two learners per board. A calm, turn-taking game that suits any pair.",
)

SIZE = 8


def _dark(row: int, col: int) -> bool:
    return (row + col) % 2 == 1


def _start_board() -> list[Optional[dict[str, Any]]]:
    board: list[Optional[dict[str, Any]]] = [None] * (SIZE * SIZE)
    for row in range(3):
        for col in range(SIZE):
            if _dark(row, col):
                board[row * SIZE + col] = {"p": 0, "k": False}
    for row in range(SIZE - 3, SIZE):
        for col in range(SIZE):
            if _dark(row, col):
                board[row * SIZE + col] = {"p": 1, "k": False}
    return board


def initial_state() -> dict[str, Any]:
    return {
        "board": _start_board(),
        "seats": {},          # player id -> 0 (red, moves down) | 1 (blue, moves up)
        "turn": 0,
        "winner": None,       # seat number once one side has no checkers left
        "last": None,         # {"from": i, "to": j, "captured": k | None} for the landing animation
        "counts": [12, 12],
    }


def _legal(board: list, seat: int, source: int, target: int) -> tuple[bool, Optional[int]]:
    """Is source -> target legal for this seat? Returns (ok, captured index or None)."""
    piece = board[source]
    if piece is None or piece["p"] != seat or board[target] is not None:
        return False, None
    r1, c1 = divmod(source, SIZE)
    r2, c2 = divmod(target, SIZE)
    if not _dark(r2, c2):
        return False, None
    dr, dc = r2 - r1, c2 - c1
    if abs(dr) != abs(dc) or abs(dr) not in (1, 2):
        return False, None
    if not piece["k"]:
        forward = 1 if seat == 0 else -1
        if (dr > 0) != (forward > 0):
            return False, None
    if abs(dr) == 1:
        return True, None
    mid = (r1 + dr // 2) * SIZE + (c1 + dc // 2)
    jumped = board[mid]
    if jumped is None or jumped["p"] == seat:
        return False, None
    return True, mid


def apply(state: dict[str, Any], action: dict[str, Any], player_id: str) -> bool:
    kind = action.get("type")

    if kind == "sit":
        # First come, first seated. A third opener just watches.
        if player_id in state["seats"] or len(state["seats"]) >= 2:
            return False
        taken = set(state["seats"].values())
        state["seats"][player_id] = 0 if 0 not in taken else 1
        return True

    if kind == "reset":
        seats = state["seats"]
        state.update(initial_state())
        state["seats"] = seats
        return True

    if kind == "move":
        seat = state["seats"].get(player_id)
        source, target = action.get("from"), action.get("to")
        if (
            seat is None or state["winner"] is not None or seat != state["turn"]
            or not isinstance(source, int) or not isinstance(target, int)
            or not (0 <= source < SIZE * SIZE and 0 <= target < SIZE * SIZE)
        ):
            return False
        board = state["board"]
        ok, captured = _legal(board, seat, source, target)
        if not ok:
            return False

        piece = board[source]
        board[source] = None
        board[target] = piece
        if captured is not None:
            board[captured] = None
            state["counts"][1 - seat] -= 1
        row = target // SIZE
        if not piece["k"] and ((seat == 0 and row == SIZE - 1) or (seat == 1 and row == 0)):
            piece["k"] = True
        state["last"] = {"from": source, "to": target, "captured": captured}
        if state["counts"][1 - seat] == 0:
            state["winner"] = seat
        else:
            state["turn"] = 1 - seat
        return True

    return False
