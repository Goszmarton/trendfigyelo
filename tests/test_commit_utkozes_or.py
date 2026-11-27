"""Minden workflow commit-lépése: a `git pull --rebase --autostash` UTÁN azonnal ütközés-őr.

Élő eset (2026-11-26 20:05Z): a késve futó reggeli backup és az esti napi gyűjtés ugyanazt a
docs/data/kulcsszo_nyers.json-t írta; az autostash-pop ütközött, a `git pull` 0-val tért vissza,
a `git add` a konfliktusjelölős fájlt commitolta → minden további gyűjtés JSONDecodeError-ral bukott.
Az őr (`git ls-files -u`) ilyenkor hibával megállítja a lépést, mielőtt bármi commitolódna.
"""
from pathlib import Path

import pytest

PULL = "git pull --rebase --autostash"
OR = 'if [ -n "$(git ls-files -u)" ]; then'

WORKFLOWOK = sorted(p for p in Path(".github/workflows").glob("*.yml") if PULL in p.read_text(encoding="utf-8"))


def test_van_mit_ellenorizni():
    assert len(WORKFLOWOK) >= 9


@pytest.mark.parametrize("wf", WORKFLOWOK, ids=lambda p: p.name)
def test_pull_utan_utkozes_or_a_git_add_elott(wf):
    sorok = wf.read_text(encoding="utf-8").splitlines()
    for i, sor in enumerate(sorok):
        if PULL in sor:
            kovetkezo = [s.strip() for s in sorok[i + 1:i + 12] if not s.strip().startswith("#")][:5]
            assert OR in kovetkezo[0], f"{wf.name}:{i + 2} — hiányzik az ütközés-őr a pull után"
            assert "exit 1" in " ".join(kovetkezo), wf.name
