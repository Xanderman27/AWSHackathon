from app.mastery import bkt
from app.mastery.select import next_item, should_route_to_prerequisite
from app.models import Choice, Item, ItemResponse

P = bkt.SkillParams()


def test_worked_example_matches_learner_model_doc():
    e = P.p_init
    e = bkt.update(e, True, P)
    assert abs(e - 0.71) < 0.01
    e = bkt.update(e, False, P)
    assert abs(e - 0.35) < 0.01
    e = bkt.update(e, True, P, hint_used=True)
    assert abs(e - 0.64) < 0.01


def test_hinted_correct_moves_less_than_unhinted():
    assert bkt.update(0.3, True, P, hint_used=True) < bkt.update(0.3, True, P)


def test_bands():
    assert bkt.band(0.2) == "building"
    assert bkt.band(0.5) == "practicing"
    assert bkt.band(0.9) == "extension"


def _item(i, skill, diff, b):
    return Item(id=i, skill_id=skill, difficulty=diff, irt_b=b, prompt="q",
                choices=[Choice(id="a", text="x")], answer="a", hint="h", explanation="e")


def test_selection_prefers_informative_item_above_floor():
    bank = [_item("easy", "s", 1, -2.0), _item("mid", "s", 3, 0.0), _item("hard", "s", 5, 2.0)]
    chosen = next_item(0.5, "s", bank, set())
    assert chosen.id in ("easy", "mid")  # hard fails the 0.60 success floor at theta 0


def test_route_after_two_easy_misses():
    items = {"e1": _item("e1", "s", 1, -2.0), "e2": _item("e2", "s", 2, -1.0)}
    rs = [ItemResponse(item_id="e1", choice_id="b", correct=False, hint_used=False),
          ItemResponse(item_id="e2", choice_id="b", correct=False, hint_used=False)]
    assert should_route_to_prerequisite(rs, items)
