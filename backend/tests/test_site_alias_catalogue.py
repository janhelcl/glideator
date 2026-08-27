import csv
from collections import defaultdict
from pathlib import Path

from app.services.site_search import normalize_site_search_text


DATA_DIR = Path(__file__).resolve().parents[1] / "app" / "data"


def _read_csv(name: str):
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_alias_catalogue_references_existing_sites_and_is_not_redundant():
    sites = {
        int(row["site_id"]): row["name"]
        for row in _read_csv("sites.csv")
    }
    aliases = _read_csv("site_aliases.csv")

    assert len(aliases) >= 90

    for row in aliases:
        site_id = int(row["site_id"])
        alias = row["alias"].strip()

        assert site_id in sites
        assert alias
        assert normalize_site_search_text(alias) != normalize_site_search_text(
            sites[site_id]
        )


def test_alias_catalogue_has_no_duplicate_or_ambiguous_exact_aliases():
    aliases = _read_csv("site_aliases.csv")
    by_site = defaultdict(set)
    exact_owner = {}

    for row in aliases:
        site_id = int(row["site_id"])
        normalized = normalize_site_search_text(row["alias"])

        assert normalized not in by_site[site_id]
        by_site[site_id].add(normalized)

        existing_owner = exact_owner.setdefault(normalized, site_id)
        assert existing_owner == site_id


def test_researched_aliases_are_present():
    aliases = {
        (int(row["site_id"]), row["alias"])
        for row in _read_csv("site_aliases.csv")
    }

    expected = {
        (22, "Mokropsy"),
        (38, "Unterberghorn"),
        (44, "Kreuzjoch"),
        (72, "Ostrý"),
        (82, "Fiescheralp"),
        (86, "First"),
        (104, "Laax"),
        (133, "Monte Grappa"),
        (135, "Monte Valinis"),
        (137, "Monte Cuarnan"),
        (142, "Monte Avena"),
        (155, "Plan de Corones"),
        (186, "Saint-Hilaire-du-Touvet"),
        (187, "Le Chalvet"),
        (197, "Pouncho d'Agast"),
        (206, "Clécy"),
        (221, "Algodonales Poniente"),
        (223, "Piedrahita"),
        (233, "Orozko"),
        (242, "Hármashatár-hegy"),
        (245, "Öregkovács-hegy"),
        (246, "Nagy-Eged-hegy"),
        (250, "Gorba-tető"),
    }

    assert expected <= aliases
