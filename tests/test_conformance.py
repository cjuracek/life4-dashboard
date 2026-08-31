"""Pins requirement wording against LIFE4's own rendered output.

This is the only test that can show the formatter is *wrong* rather than
merely *changed* -- everything else in the suite compares our output to our
output. It is what makes the generated snapshot an honest substitute for
the hand-written requirement literals this work deleted.

If it fails, fix life4/life4/ranks/wording.py. Do not edit the fixture to
make it pass.
"""

from pathlib import Path

from life4.life4.ranks.registry import load_ranks

FIXTURE = Path(__file__).parent / "fixtures/life4_rendered.txt"
SNAPSHOT = Path(__file__).parent / "fixtures/rendered_requirements.txt"


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
    assert len(generated()) == 583


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

    To accept an intended change: delete the snapshot, re-run, review the
    diff before committing.
    """
    report = rendered_report()
    if not SNAPSHOT.exists():
        SNAPSHOT.write_text(report, encoding="utf-8")
    assert report == SNAPSHOT.read_text(encoding="utf-8")
