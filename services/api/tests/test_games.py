"""Logic tests for the collaborative games. They are free play, so nothing here touches
mastery; what matters is that a shared board stays consistent for everyone looking at it."""


from app.games import detectives, fractions, memory, shapes, sorting


def test_a_row_matches_the_target_only_at_the_equivalent_amount():
    state = fractions.initial_state()
    assert state["target"]["label"] == "one half"

    # Two of four is one half; one of four is not.
    fractions.apply(state, {"type": "set_cell", "row": "fourths", "index": 0, "active": True}, "student-01")
    assert state["matched"] == []
    fractions.apply(state, {"type": "set_cell", "row": "fourths", "index": 1, "active": True}, "student-02")
    assert state["matched"] == ["fourths"]

    # Six of twelve is the same half, found by a different teammate.
    for index in range(6):
        fractions.apply(state, {"type": "set_cell", "row": "twelfths", "index": index, "active": True}, "student-03")
    assert set(state["matched"]) == {"fourths", "twelfths"}
    assert state["updated_by"]["twelfths"][0] == "student-03"


def test_changing_the_target_clears_the_wall_for_everyone():
    state = fractions.initial_state()
    fractions.apply(state, {"type": "set_cell", "row": "halves", "index": 0, "active": True}, "student-01")
    fractions.apply(state, {"type": "set_round", "round": 1}, "student-01")
    assert state["target"]["label"] == "two thirds"
    assert not any(any(row) for row in state["rows"].values())


def test_an_unmatched_memory_pair_turns_back_over_on_its_own():
    state = memory.initial_state()
    first = 0
    second = next(index for index in range(1, len(state["cards"])) if state["cards"][index] != state["cards"][first])

    memory.apply(state, {"type": "flip", "index": first}, "student-01")
    memory.apply(state, {"type": "flip", "index": second}, "student-02")
    assert state["flipped"] == [first, second]
    assert state["wake_at"]

    memory.wake(state)
    assert state["flipped"] == []
    assert state["found"] == 0


def test_a_matching_memory_pair_stays_up_and_counts_once():
    state = memory.initial_state()
    first = 0
    second = next(index for index in range(1, len(state["cards"])) if state["cards"][index] == state["cards"][first])

    memory.apply(state, {"type": "flip", "index": first}, "student-01")
    memory.apply(state, {"type": "flip", "index": second}, "student-02")
    assert state["found"] == 1
    assert state["matched"][first] and state["matched"][second]
    assert state["matched_by"][second] == "student-02"
    # A third tap on a matched card changes nothing.
    assert memory.apply(state, {"type": "flip", "index": first}, "student-01") is False


def test_sorting_has_no_answer_key_and_caps_the_bins():
    state = sorting.initial_state()
    for index in range(sorting.MAX_BINS):
        sorting.apply(state, {"type": "add_bin", "name": f"Mine {index}"}, "student-01")
    assert len(state["bins"]) == sorting.MAX_BINS

    item = state["set"]["items"][0]["id"]
    sorting.apply(state, {"type": "place", "item": item, "bin": state["bins"][0]["id"]}, "student-02")
    assert state["placements"][item] == {"bin": state["bins"][0]["id"], "by": "student-02"}
    assert all("answer" not in card for card in state["set"]["items"])


def test_removing_a_bin_returns_its_cards_to_the_pile():
    state = sorting.initial_state()
    bin_id = state["bins"][0]["id"]
    item = state["set"]["items"][0]["id"]
    sorting.apply(state, {"type": "place", "item": item, "bin": bin_id}, "student-01")
    sorting.apply(state, {"type": "remove_bin", "bin": bin_id}, "student-01")
    assert item not in state["placements"]


def test_detective_cards_carry_an_answer_but_nothing_is_scored():
    state = detectives.initial_state()
    card = state["story"]["cards"][0]["id"]
    detectives.apply(state, {"type": "place", "card": card, "column": "main"}, "student-01")
    assert state["placements"][card] == {"column": "main", "by": "student-01"}
    # The group chooses when to look; there is no score field anywhere in the state.
    assert state["revealed"] is False
    detectives.apply(state, {"type": "reveal", "revealed": True}, "student-02")
    assert state["revealed"] is True
    assert "score" not in state


def test_a_piece_cannot_be_dropped_outside_the_outline_or_onto_another():
    state = shapes.initial_state()
    bar = next(piece for piece in state["pieces"] if piece["id"] == "bar")

    # The quilt is 4x4; a 1x4 bar at column 1 would hang off the right edge.
    assert shapes.apply(state, {"type": "place", "piece": "bar", "row": 0, "col": 1}, "student-01") is False
    assert shapes.apply(state, {"type": "place", "piece": "bar", "row": 0, "col": 0}, "student-01") is True
    assert bar["placed"] == {"row": 0, "col": 0}

    # The step piece overlaps the bar's row, so the board refuses it.
    assert shapes.apply(state, {"type": "place", "piece": "step", "row": 0, "col": 0}, "student-02") is False


def test_turning_a_placed_piece_takes_it_back_out():
    state = shapes.initial_state()
    shapes.apply(state, {"type": "place", "piece": "bar", "row": 0, "col": 0}, "student-01")
    shapes.apply(state, {"type": "rotate", "piece": "bar"}, "student-02")
    bar = next(piece for piece in state["pieces"] if piece["id"] == "bar")
    assert bar["placed"] is None
    assert bar["cells"] == [[0, 0], [1, 0], [2, 0], [3, 0]]


def test_four_turns_bring_a_piece_back_to_where_it_started():
    for piece in shapes.ROUNDS[0]["pieces"]:
        cells = shapes._normalise([list(cell) for cell in piece["cells"]])
        turned = cells
        for _ in range(4):
            turned = shapes._rotate(turned)
        assert turned == cells, piece["id"]


def test_every_shape_puzzle_can_actually_be_solved():
    """Search each puzzle for a real solution, so no group is handed an impossible board."""
    for index in range(len(shapes.ROUNDS)):
        state = shapes.initial_state()
        shapes.apply(state, {"type": "set_round", "round": index}, "student-01")
        outline = {(cell[0], cell[1]) for cell in state["puzzle"]["silhouette"]}
        piece_ids = [piece["id"] for piece in state["pieces"]]
        assert sum(len(piece["cells"]) for piece in state["pieces"]) == len(outline), index

        def orientations(cells):
            seen, shape = [], cells
            for _ in range(4):
                for candidate in (shape, shapes._flip(shape)):
                    if candidate not in seen:
                        seen.append(candidate)
                shape = shapes._rotate(shape)
            return seen

        shapes_by_id = {piece["id"]: orientations(piece["cells"]) for piece in state["pieces"]}

        def search(remaining, filled):
            if not remaining:
                return filled == outline
            head, *tail = remaining
            for cells in shapes_by_id[head]:
                for row, col in outline:
                    wanted = {(row + cell[0], col + cell[1]) for cell in cells}
                    if wanted <= outline and not (wanted & filled):
                        if search(tail, filled | wanted):
                            return True
            return False

        assert search(piece_ids, set()), f"puzzle {index} has no solution"


def test_a_solved_board_is_reported_as_solved():
    state = shapes.initial_state()
    # The tiling the piece set was cut from.
    placements = [("corner", 0, 0), ("hook", 0, 1), ("step", 1, 1), ("bar", 3, 0)]
    for piece_id, row, col in placements:
        assert shapes.apply(state, {"type": "place", "piece": piece_id, "row": row, "col": col}, "student-01") is True
    assert state["solved"] is True
