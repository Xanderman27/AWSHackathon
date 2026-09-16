"""Previously generated drafts, kept so the demo works with no AWS and survives a bad call.

These are real outputs of the pipeline, frozen. When one of them is shown, the teacher screen
says "cached" rather than implying it came from a live model — PRD §23.4 allows the cached
path on stage on the condition that you say so.
"""

from __future__ import annotations

from .schema import ActivityDraft

CACHED_DRAFTS: dict[tuple[str, str], ActivityDraft] = {
    ("fraction_equivalence", "building"): ActivityDraft(
        title="Paper strips at the kitchen table",
        why=("Your child can already match fractions when they are pictures. Folding strips makes "
             "the size of each part something they can hold, which is what connects the picture to "
             "the numbers underneath it."),
        minutes=12,
        materials=["Four strips of paper the same length", "Scissors", "A marker"],
        steps=[
            "Cut four paper strips exactly the same length and lay them in a row.",
            "Leave the first strip whole. Fold the others into 2, 4 and 8 equal parts.",
            "Colour in one half of the second strip, then ask your child to colour the same amount on the others.",
            "Ask: how many small parts covered the same space as one half?",
            "Write down the pairs you found together, like 1/2 and 2/4.",
        ],
        citations=["ccss-4nf-a1", "misconception-fraction-size", "template-manipulative"],
    ),
    ("fraction_equivalence", "practicing"): ActivityDraft(
        title="Same amount, different pieces",
        why=("Your child can find equal fractions with a model in front of them. This gives them "
             "practice spotting the same idea in ordinary places, which is what makes it stick."),
        minutes=10,
        materials=["Something to share, like a sandwich, an orange or a chocolate bar", "A marker"],
        steps=[
            "Cut the food into two equal pieces and agree that one piece is one half.",
            "Now cut it into four equal pieces instead. Ask how many pieces make the same amount.",
            "Try it once more with eight pieces and let your child predict first.",
            "Ask your child to say the rule they noticed in their own words.",
        ],
        citations=["ccss-4nf-a1", "template-spot-it", "udl-reduce-load"],
    ),
    ("fraction_equivalence", "extension"): ActivityDraft(
        title="Fraction hunt in the kitchen",
        why=("Your child is secure on equal fractions with a model. Finding them in recipes and "
             "packaging stretches the idea to numbers that are not already lined up for them."),
        minutes=15,
        materials=["A recipe or a food package", "Paper", "A pencil"],
        steps=[
            "Find a measurement on the packet, like 3/4 of a cup.",
            "Ask your child to write another fraction that means the same amount.",
            "Check it together by drawing both on one strip of paper.",
            "Find two more measurements and take turns making the match.",
        ],
        citations=["ccss-4nf-a1", "template-spot-it"],
    ),
    ("main_idea", "practicing"): ActivityDraft(
        title="Say it back in one sentence",
        why=("Your child can find details in a text. Naming the one idea the whole thing is about "
             "is the next step, and saying it out loud is easier than writing it down."),
        minutes=10,
        materials=["A cereal box, a short article, or any book you have"],
        steps=[
            "Read a short piece aloud together, taking turns.",
            "Ask your child what the whole thing was about, in one sentence.",
            "Ask them to find two details that back up what they just said.",
            "Try a sentence that is only a detail and ask whether it could be the big idea.",
        ],
        citations=["ccss-ri-4-2", "misconception-main-idea-first-line", "template-read-together"],
    ),
}
