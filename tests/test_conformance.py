"""Pins requirement wording against LIFE4's own rendered output.

This is the only test that can show the formatter is *wrong* rather than
merely *changed* -- everything else in the suite compares our output to our
output. It is what makes the generated snapshot an honest substitute for
the hand-written requirement literals this work deleted.

If it fails, fix life4/life4/ranks/wording.py. Do not edit the fixture to
make it pass.
"""

import json
from importlib.resources import files
from pathlib import Path

from life4.life4.ranks.registry import IN_SCOPE, load_ranks

FIXTURE = Path(__file__).parent / "fixtures/life4_rendered.txt"
SNAPSHOT = Path(__file__).parent / "fixtures/rendered_requirements.txt"


def in_scope_goal_count() -> int:
    """Goals in the vendored snapshot, counted without parsing them.

    Deliberately re-reads ranks.json rather than measuring load_ranks():
    counting the parser's own output against itself could not notice the
    parser dropping a goal, which is the thing this count exists to catch.
    """
    payload = json.loads(
        files("life4.life4.ranks").joinpath("data/ranks.json").read_text("utf-8")
    )
    in_scope_names = {tier.name for tier in IN_SCOPE}
    return sum(
        len(entry["requirements"]["goals"])
        + len(entry["requirements"].get("substitutions") or [])
        for entry in payload
        if entry["name"] in in_scope_names
    )


def life4_strings() -> set[str]:
    return set(FIXTURE.read_text(encoding="utf-8").splitlines())


def generated() -> list[str]:
    return [
        str(requirement)
        for subranks in load_ranks().values()
        for rank in subranks
        for requirement in (*rank.requirements, *rank.substitutions)
    ]


def test_every_generated_string_is_one_life4_actually_prints():
    published = life4_strings()
    strings = generated()
    assert strings, "no requirements were generated"
    unpublished = sorted({s for s in strings if s not in published})
    assert not unpublished, (
        "these renderings appear nowhere in LIFE4's output:\n  "
        + "\n  ".join(unpublished)
    )


def test_conformance_covers_every_in_scope_goal():
    """Every in-scope goal became a string -- none silently dropped.

    Derived from the snapshot, not pinned to a literal, so widening
    IN_SCOPE stays the one-line change registry.py advertises instead of
    ambushing the next reader with `assert 719 == 583`.
    """
    assert len(generated()) == in_scope_goal_count()


def rendered_report() -> str:
    lines = []
    for tier, subranks in load_ranks().items():
        for rank in subranks:
            lines.append(f"## {tier.name} {rank.subrank}")
            lines.extend(f"  req: {r}" for r in rank.requirements)
            lines.extend(f"  sub: {s}" for s in rank.substitutions)
    return "\n".join(lines) + "\n"


def test_rendered_requirements_match_the_committed_snapshot():
    """Pins goal-to-string mapping, which membership alone cannot.

    Membership would let a swap through -- rendering goal A's string for
    goal B -- since both are legitimate strings somewhere in the fixture.

    To accept an intended change, regenerate the snapshot deliberately:

        uv run scripts/write_rendered_snapshot.py

    then review the diff before committing. The test never writes the file
    itself -- an expectation the code under test can author is one that
    cannot fail on a fresh checkout.
    """
    assert SNAPSHOT.exists(), (
        f"{SNAPSHOT} is missing. It is committed ground truth, not a cache; "
        f"regenerate it with `uv run scripts/write_rendered_snapshot.py` and "
        f"review the diff."
    )
    assert rendered_report() == SNAPSHOT.read_text(encoding="utf-8")
