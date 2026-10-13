"""Static checks for the standalone browser demos in tools/.

The demos are single HTML files with inline JavaScript, so a typo in an element id only shows up
as a runtime error in the browser. These tests catch that, and keep the demos self-contained.
"""

import json
import re
import shutil
import subprocess
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


# BLAKE3 reference test vectors (BLAKE3-team/BLAKE3 test_vectors.json, hash mode),
# input byte i = i mod 251.
BLAKE3_VECTORS = {
    0: "af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262",
    1: "2d3adedff11b61f14c886e35afa036736dcd87a74d27b5c1510225d0f592e213",
    1024: "42214739f095a406f3fc83deb889744ac00df831c10daa55189b5d121c855af7",
    1025: "d00278ae47eb27b34faecf67b4fe263f82d5412916c1ffd97c8cb7fb814b8444",
    3073: "7124b49501012f81cc7f11ca069ec9226cecb8a2c850cfe644e327d22d3e1cd3",
    8193: "bab6c09cb8ce8cf459261398d2e7aef35700bf488116ceb94a36d0f5f1b7bc3b",
}
BLAKE3_ABC = "6437b3ac38465133ffb63b75273a8db548c558465d79db03fd359c6cd5bd9d85"
BLAKE3_PAGES = [
    TOOLS / "mission1_evacuation.html",
    TOOLS.parent / "docs" / "mission1_explainer.html",
]
BLAKE3_RUN = """
const out = {};
for (const n of LENGTHS) {
  const b = new Uint8Array(n);
  for (let i = 0; i < n; i++) b[i] = i % 251;
  out[n] = blake3.bytes(b);
}
out.abc = blake3("abc");
console.log(JSON.stringify(out));
"""


@pytest.mark.parametrize("path", BLAKE3_PAGES, ids=[p.name for p in BLAKE3_PAGES])
def test_merkle_hash_is_blake3(path):
    """The Mission 1 Merkle hash is BLAKE3-256 and matches the reference vectors."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    src = path.read_text(encoding="utf-8")
    m = re.search(r"^  const blake3 = \(\(\) => \{.*?^  \}\)\(\);$", src, re.S | re.M)
    assert m, f"{path.name}: no inline blake3()"
    script = m.group(0) + BLAKE3_RUN.replace("LENGTHS", json.dumps(sorted(BLAKE3_VECTORS)))
    run = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True)
    got = json.loads(run.stdout)
    for n, want in BLAKE3_VECTORS.items():
        assert got[str(n)] == want, f"length {n}"
    assert got["abc"] == BLAKE3_ABC
