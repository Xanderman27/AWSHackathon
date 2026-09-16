"""Generate data/seed/items.json for the two fraction skills.

Items are hand-authored here so hints, distractor misconception tags, and difficulty are
reviewable in one place. Run: python scripts/build_items.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "seed" / "items.json"

# difficulty 1..5 -> IRT b on roughly [-2, 2]; a stays 1.0 until calibration
B = {1: -2.0, 2: -1.0, 3: 0.0, 4: 1.0, 5: 2.0}


def item(id, skill, diff, prompt, choices, answer, hint, explanation, alt=None):
    return {
        "id": id, "skill_id": skill, "prerequisite_skill_id": "fraction_parts" if skill == "fraction_equivalence" else None,
        "difficulty": diff, "irt_a": 1.0, "irt_b": B[diff],
        "prompt": prompt, "image_alt": alt,
        "choices": [{"id": c[0], "text": c[1], "misconception": c[2] if len(c) > 2 else None} for c in choices],
        "answer": answer, "hint": hint, "explanation": explanation,
        "passage": None, "passage_read_aloud_allowed": True, "approved": True,
    }


# Misconception tags feed the Layer 3 pattern classifier.
# visual_only: can match pictures but not symbols. add_same: adds the same number to top and bottom.
# denominator_size: thinks bigger bottom number means bigger fraction. part_count: counts shaded parts only.
items = [
    # --- fraction_parts (prerequisite, grade 3) ---
    item("fp-01", "fraction_parts", 1, "A pizza is cut into 4 equal slices. You eat 1 slice. What fraction did you eat?",
         [("a", "1/4"), ("b", "1/3", "part_count"), ("c", "4/1", "inverted"), ("d", "1/2", "part_count")], "a",
         "Count all the slices first. That number goes on the bottom.",
         "There are 4 slices in all, and you ate 1, so 1/4.", "A circle cut into 4 equal pieces with 1 piece shaded."),
    item("fp-02", "fraction_parts", 1, "A bar is split into 3 equal parts. 2 parts are shaded. What fraction is shaded?",
         [("a", "2/3"), ("b", "3/2", "inverted"), ("c", "2/5", "part_count"), ("d", "1/3", "part_count")], "a",
         "The bottom number is how many parts in all. The top is how many are shaded.",
         "3 parts in all, 2 shaded, so 2/3.", "A rectangle split into 3 equal parts with 2 shaded."),
    item("fp-03", "fraction_parts", 2, "Which picture shows 3/4?",
         [("a", "4 equal parts, 3 shaded"), ("b", "3 equal parts, 4 shaded", "inverted"), ("c", "4 equal parts, 1 shaded", "part_count"), ("d", "8 equal parts, 3 shaded", "denominator_size")], "a",
         "3/4 means 4 parts in all and 3 of them shaded.", "Four equal parts with three shaded is 3/4."),
    item("fp-04", "fraction_parts", 2, "A shape is cut into 6 equal parts. 5 are shaded. What fraction is NOT shaded?",
         [("a", "1/6"), ("b", "5/6", "part_count"), ("c", "1/5", "part_count"), ("d", "6/1", "inverted")], "a",
         "How many parts are left white? That is the top number.", "6 parts, 1 is not shaded, so 1/6."),
    item("fp-05", "fraction_parts", 3, "Which fraction is the same as one whole?",
         [("a", "5/5"), ("b", "1/5", "part_count"), ("c", "5/1", "inverted"), ("d", "0/5", "part_count")], "a",
         "One whole means all the parts are shaded.", "If all 5 of 5 parts are shaded, that is one whole."),
    item("fp-06", "fraction_parts", 3, "A bar has 8 equal parts. How many parts make 1/2 of the bar?",
         [("a", "4"), ("b", "2", "denominator_size"), ("c", "8", "part_count"), ("d", "1", "part_count")], "a",
         "Half means the same amount on each side. Split 8 into two equal groups.", "Half of 8 parts is 4 parts."),

    # --- fraction_equivalence (target, grade 4) ---
    item("fe-01", "fraction_equivalence", 1, "Look at two bars. One shows 1/2 shaded. The other shows 2/4 shaded. Do they show the same amount?",
         [("a", "Yes, the same amount"), ("b", "No, 2/4 is more", "denominator_size"), ("c", "No, 1/2 is more", "denominator_size"), ("d", "You cannot tell", "visual_only")], "a",
         "Line the two bars up. Does the shading end at the same place?",
         "The shaded parts are the same length, so 1/2 and 2/4 are equal.", "Two equal bars: the first has 1 of 2 parts shaded, the second 2 of 4 parts shaded, ending at the same point."),
    item("fe-02", "fraction_equivalence", 1, "Which picture shows the same amount as 1/3?",
         [("a", "6 equal parts, 2 shaded"), ("b", "6 equal parts, 1 shaded", "denominator_size"), ("c", "3 equal parts, 2 shaded", "part_count"), ("d", "6 equal parts, 3 shaded", "add_same")], "a",
         "Cut each third into two smaller pieces. How many small pieces are shaded now?",
         "Cutting each third in half gives 6 parts with 2 shaded, so 2/6 equals 1/3."),
    item("fe-03", "fraction_equivalence", 2, "Which fraction is equal to 1/2?",
         [("a", "3/6"), ("b", "2/3", "add_same"), ("c", "1/4", "denominator_size"), ("d", "3/4", "part_count")], "a",
         "Half means the top is exactly half of the bottom.", "3 is half of 6, so 3/6 equals 1/2."),
    item("fe-04", "fraction_equivalence", 2, "A bar shows 2/3 shaded. If you cut every part in half, what fraction is shaded now?",
         [("a", "4/6"), ("b", "2/6", "denominator_size"), ("c", "3/4", "add_same"), ("d", "4/3", "inverted")], "a",
         "Cutting parts in half doubles the top AND the bottom.", "2 shaded parts become 4, and 3 parts become 6, so 4/6."),
    item("fe-05", "fraction_equivalence", 3, "Which fraction is equal to 3/4?",
         [("a", "6/8"), ("b", "4/5", "add_same"), ("c", "3/8", "denominator_size"), ("d", "6/4", "inverted")], "a",
         "Multiply the top and the bottom by the same number.", "3 times 2 is 6, and 4 times 2 is 8, so 6/8."),
    item("fe-06", "fraction_equivalence", 3, "Fill in the blank: 2/5 = ?/10",
         [("a", "4"), ("b", "2", "visual_only"), ("c", "7", "add_same"), ("d", "5", "denominator_size")], "a",
         "The bottom went from 5 to 10. That is times 2. Do the same to the top.", "5 times 2 is 10, so 2 times 2 is 4. 2/5 = 4/10."),
    item("fe-07", "fraction_equivalence", 3, "Which two fractions are equal?",
         [("a", "1/4 and 2/8"), ("b", "1/4 and 2/5", "add_same"), ("c", "1/4 and 1/8", "denominator_size"), ("d", "2/8 and 2/4", "part_count")], "a",
         "Try doubling the top and the bottom of 1/4.", "1 times 2 is 2, and 4 times 2 is 8, so 1/4 equals 2/8."),
    item("fe-08", "fraction_equivalence", 4, "Fill in the blank: 6/9 = 2/?",
         [("a", "3"), ("b", "6", "add_same"), ("c", "9", "visual_only"), ("d", "2", "denominator_size")], "a",
         "The top went from 6 to 2. That is divided by 3. Do the same to the bottom.", "6 divided by 3 is 2, and 9 divided by 3 is 3, so 6/9 = 2/3."),
    item("fe-09", "fraction_equivalence", 4, "Which fraction is NOT equal to 1/2?",
         [("a", "3/5"), ("b", "2/4", "visual_only"), ("c", "5/10", "visual_only"), ("d", "4/8", "visual_only")], "a",
         "For 1/2, the top must be exactly half of the bottom. Check each one.", "3 is not half of 5, so 3/5 is not equal to 1/2."),
    item("fe-10", "fraction_equivalence", 4, "Fill in the blank: 3/4 = ?/12",
         [("a", "9"), ("b", "11", "add_same"), ("c", "3", "visual_only"), ("d", "6", "denominator_size")], "a",
         "4 times what number is 12? Multiply the top by that same number.", "4 times 3 is 12, so 3 times 3 is 9. 3/4 = 9/12."),
    item("fe-11", "fraction_equivalence", 5, "Which fraction is equal to 2/3 AND has a bottom number bigger than 10?",
         [("a", "8/12"), ("b", "6/9", "visual_only"), ("c", "10/12", "add_same"), ("d", "8/11", "add_same")], "a",
         "Multiply 2/3 by the same number on top and bottom until the bottom is bigger than 10.", "2 times 4 is 8, and 3 times 4 is 12, so 8/12."),
    item("fe-12", "fraction_equivalence", 5, "Maya says 4/6 and 6/9 are equal. Is she right?",
         [("a", "Yes, both equal 2/3"), ("b", "No, 6/9 is bigger", "denominator_size"), ("c", "No, 4/6 is bigger", "part_count"), ("d", "Yes, because 4 + 2 = 6", "add_same")], "a",
         "Try dividing the top and bottom of each fraction by the same number.", "4/6 divided by 2 is 2/3, and 6/9 divided by 3 is 2/3. They are equal."),
]

# --- main_idea (Grade 4 reading, CCSS RI.4.2) ---
# The passage itself is never read aloud: reading the text to the child would change what the
# item measures (PRD FR-07). The question and the choices may always be read aloud.
def ritem(id, diff, passage, prompt, choices, answer, hint, explanation):
    return {
        "id": id, "skill_id": "main_idea", "prerequisite_skill_id": None,
        "difficulty": diff, "irt_a": 1.0, "irt_b": B[diff],
        "prompt": prompt, "image_alt": None,
        "choices": [{"id": c[0], "text": c[1], "misconception": c[2] if len(c) > 2 else None} for c in choices],
        "answer": answer, "hint": hint, "explanation": explanation,
        "passage": passage, "passage_read_aloud_allowed": False, "approved": True,
    }


# detail_for_main: picks a small detail instead of the big idea.
# off_topic: picks something the passage never says.
# too_broad: picks a statement wider than the passage.
items += [
    ritem("mi-01", 1,
          "Bees live together in a hive. Each bee has a job. Some bees look for flowers. Some bees "
          "take care of the baby bees. Some bees guard the door. Working together keeps the hive safe.",
          "What is this passage mostly about?",
          [("a", "Bees in a hive each have a job"), ("b", "Some bees guard the door", "detail_for_main"),
           ("c", "Flowers grow in gardens", "off_topic"), ("d", "All insects work hard", "too_broad")], "a",
          "Look for the idea that covers the whole passage, not just one sentence.",
          "Every sentence is about the different jobs bees do, so that is the big idea."),
    ritem("mi-02", 1,
          "Rain helps plants grow. After it rains, the soil holds water. Roots drink the water. "
          "Then the plant can make food from sunlight.",
          "What is the big idea of this passage?",
          [("a", "Rain helps plants grow"), ("b", "Roots drink water", "detail_for_main"),
           ("c", "Sunlight is warm", "off_topic"), ("d", "Weather changes every day", "too_broad")], "a",
          "The first sentence often tells you the big idea. Check if the rest of the passage matches it.",
          "The passage explains how rain helps a plant grow, step by step."),
    ritem("mi-03", 2,
          "Sea otters float on their backs. They wrap themselves in seaweed so they do not drift away "
          "while they sleep. They also hold hands with other otters. Both tricks keep the group together.",
          "Which detail supports the big idea that otters keep from drifting away?",
          [("a", "They wrap themselves in seaweed"), ("b", "Sea otters float on their backs", "detail_for_main"),
           ("c", "Otters eat shellfish", "off_topic"), ("d", "Ocean animals are clever", "too_broad")], "a",
          "Find the sentence that shows HOW they stop drifting.",
          "Wrapping in seaweed is what holds an otter in place, so it supports that idea."),
    ritem("mi-04", 2,
          "Long ago, people told time using the sun. A sundial has a stick in the middle. The stick makes "
          "a shadow. As the sun moves across the sky, the shadow moves too. People read the time from "
          "where the shadow falls.",
          "What is this passage mostly about?",
          [("a", "How a sundial shows the time"), ("b", "A sundial has a stick", "detail_for_main"),
           ("c", "The sun is very hot", "off_topic"), ("d", "People invented many machines", "too_broad")], "a",
          "Ask yourself: what is the passage explaining from beginning to end?",
          "Each sentence adds one step in how a sundial tells time."),
    ritem("mi-05", 3,
          "Some frogs can freeze in winter. Ice forms inside their bodies, and their hearts stop beating. "
          "Sugar in their blood protects them from harm. When spring comes, they thaw out and hop away.",
          "Which sentence best states the main idea?",
          [("a", "Some frogs survive winter by freezing and thawing"),
           ("b", "Ice forms inside their bodies", "detail_for_main"),
           ("c", "Frogs eat insects in the spring", "off_topic"),
           ("d", "Animals do amazing things", "too_broad")], "a",
          "A main idea sentence should cover the beginning AND the end of the passage.",
          "The passage covers freezing in winter and thawing in spring, which choice A states."),
    ritem("mi-06", 3,
          "City planners are adding gardens to rooftops. The plants soak up rain, so less water floods the "
          "streets. The leaves also cool the building below, so people use less power in summer. Birds and "
          "bees find new places to visit.",
          "What is the main idea of this passage?",
          [("a", "Rooftop gardens help cities in several ways"),
           ("b", "Leaves cool the building below", "detail_for_main"),
           ("c", "Bees make honey", "off_topic"),
           ("d", "Cities are growing quickly", "too_broad")], "a",
          "Count how many different benefits the passage lists. What do they all have in common?",
          "Flooding, cooling, and wildlife are all ways rooftop gardens help, so choice A covers them."),
    ritem("mi-07", 4,
          "Paper was once made only by hand, one sheet at a time. A worker dipped a screen into wet pulp, "
          "lifted it, and let the water drain. Then the sheet was pressed and hung to dry. A skilled worker "
          "might finish a few hundred sheets in a day. Today a machine can make that many in a second.",
          "Which statement best captures the main idea?",
          [("a", "Making paper changed from slow handwork to fast machines"),
           ("b", "A worker dipped a screen into wet pulp", "detail_for_main"),
           ("c", "Paper is made from trees", "off_topic"),
           ("d", "Machines changed the world", "too_broad")], "a",
          "The last sentence compares old and new. Does your answer include both?",
          "The passage contrasts the slow hand process with fast machines, which choice A states."),
    ritem("mi-08", 4,
          "Desert plants save water in clever ways. A cactus stores water in its thick stem. Some plants "
          "grow roots that spread wide and shallow to catch rain fast. Others drop their leaves in dry months "
          "so they lose less water to the air.",
          "Which detail best supports the main idea?",
          [("a", "A cactus stores water in its thick stem"),
           ("b", "Desert plants save water in clever ways", "detail_for_main"),
           ("c", "Deserts are hot during the day", "off_topic"),
           ("d", "Plants need water to live", "too_broad")], "a",
          "The main idea is already given. Which choice is an EXAMPLE of it?",
          "Storing water in a stem is one clever way a desert plant saves water."),
]

OUT.write_text(json.dumps(items, indent=2), encoding="utf-8")
print(f"wrote {len(items)} items to {OUT}")
