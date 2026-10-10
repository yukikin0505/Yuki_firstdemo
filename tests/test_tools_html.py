"""Static checks for the standalone browser demos in tools/.

The demos are single HTML files with inline JavaScript, so a typo in an element id only shows up
as a runtime error in the browser. These tests catch that, and keep the demos self-contained.
"""

import re
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
DEMOS = sorted(TOOLS.glob("*.html"))


def _ids_used(src: str) -> set[str]:
    used = set(re.findall(r'\$\("([\w-]+)"\)', src))
    # ui lookup tables: ["a", "b", ...].forEach((id) => (ui[id] = $(id)))
    for block in re.findall(r"\[([^\[\]]*)\]\.forEach\(\(id\) => \(ui\[id\] = \$\(id\)\)\)", src):
        used |= set(re.findall(r'"([\w-]+)"', block))
    return used


@pytest.mark.parametrize("path", DEMOS, ids=[p.name for p in DEMOS])
def test_every_referenced_id_exists(path):
    src = path.read_text(encoding="utf-8")
    defined = set(re.findall(r'id="([\w-]+)"', src))
    missing = _ids_used(src) - defined
    assert not missing, f"{path.name}: script looks up ids with no element: {sorted(missing)}"


@pytest.mark.parametrize("path", DEMOS, ids=[p.name for p in DEMOS])
def test_demo_is_self_contained(path):
    src = path.read_text(encoding="utf-8")
    assert "<title>" in src[:8192]
    assert not re.search(r"<script[^>]+src=", src), "demos inline their JavaScript"


def test_mission1_demo_exists():
    assert (TOOLS / "mission1_evacuation.html").exists()
