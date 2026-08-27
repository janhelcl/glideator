"""Expand the curated site alias catalogue.

Revision ID: 0014_expand_site_aliases
Revises: 0013_site_aliases
Create Date: 2026-08-27

"""
import unicodedata

from alembic import op
import sqlalchemy as sa


revision = "0014_expand_site_aliases"
down_revision = "0013_site_aliases"
branch_labels = None
depends_on = None


ALIASES = (
    ("Cukrák", "Mokropsy"),
    ("Kössen", "Unterberghorn"),
    ("Schlick 2000", "Kreuzjoch"),
    ("Osser", "Ostrý"),
    ("Osser", "Velký Ostrý"),
    ("Osser", "Großer Osser"),
    ("Osterfelder", "Osterfelderkopf"),
    ("Fiesch", "Fiescheralp"),
    ("Fiesch", "Heimat"),
    ("Fiesch", "Kühboden"),
    ("Amisbühl", "Beatenberg"),
    ("Amisbühl", "Beatenberg Amisbühl"),
    ("Grindelwald", "First"),
    ("Grindelwald", "Grindelwald First"),
    ("Rotenfluh", "Rotenflue"),
    ("Oberi Wängi", "Obere Wängi"),
    ("Crap Sogn Gion", "Laax"),
    ("Crap Sogn Gion", "Laax Crap Sogn Gion"),
    ("Tschenten", "Tschentenalp"),
    ("Niederbauen", "Emmetten Niederbauen"),
    ("Jakobshorn", "Davos Jakobshorn"),
    ("Cornizzolo", "Suello"),
    ("Cornizzolo", "Cornizzolo Suello"),
    ("Gemona", "Monte Cuarnan"),
    ("Gemona", "Cuarnan"),
    ("Col Rodella", "Campitello"),
    ("Col Rodella", "Campitello di Fassa"),
    ("Laveno", "Sasso del Ferro"),
    ("Feltre", "Monte Avena"),
    ("Piossasco", "Monte San Giorgio"),
    ("Gas Monte Belpo", "Monte Belpo"),
    ("Gas Monte Belpo", "Il Gas"),
    ("Kronplatz", "Plan de Corones"),
    ("Monte Ripoli", "Tivoli"),
    ("Monte Baldo", "Malcesine"),
    ("Monte Baldo", "Malcesine Monte Baldo"),
    ("Cà del Monte", "Cecima"),
    ("Kobala", "Tolmin"),
    ("Kobala", "Tolmin Kobala"),
    ("Lijak", "Nova Gorica"),
    ("Lijak", "Nova Gorica Lijak"),
    ("Stol", "Kobarid"),
    ("Stol", "Kobarid Stol"),
    ("Col de La Forclaz", "Annecy Forclaz"),
    ("Col de La Forclaz", "Annecy Col de la Forclaz"),
    ("Saint Hilaire", "Saint-Hilaire-du-Touvet"),
    ("St. André", "Saint-André-les-Alpes"),
    ("St. André", "Le Chalvet"),
    ("St. André", "Chalvet"),
    ("Planfait", "Annecy Planfait"),
    ("Planfait", "Talloires Planfait"),
    ("Treh", "Le Treh"),
    ("Treh", "Markstein"),
    ("Treh", "Treh Markstein"),
    ("Planpraz", "Chamonix Planpraz"),
    ("Plaine Joux", "Passy"),
    ("Plaine Joux", "Passy Plaine-Joux"),
    ("Mont Lachat", "Le Grand-Bornand"),
    ("Millau", "Puncho d'Agast"),
    ("Millau", "Pouncho d'Agast"),
    ("Chabre", "Laragne"),
    ("Chabre", "Laragne-Chabre"),
    ("St. Jean", "Saint Jean Montclar"),
    ("St. Jean", "Saint-Jean-Montclar"),
    ("St. Jean", "Montclar"),
    ("St. Jean", "Montclar-le-lac"),
    ("St. Vincent Les Forts", "Saint-Vincent-les-Forts"),
    ("Saint-Omer", "Clécy"),
    ("Saint-Omer", "Clécy Saint-Omer"),
    ("Gréolières", "Cheiron"),
    ("Semnoz", "Annecy Semnoz"),
    ("Collet d'Allevard", "Allevard"),
    ("Mauroux", "Pic des Mauroux"),
    ("Mauroux", "Targasonne"),
    ("Mauroux", "Targasonne Mauroux"),
    ("Poniente", "Algodonales Poniente"),
    ("Poniente", "Sierra de Líjar"),
    ("Peña Negra", "Piedrahita"),
    ("Peña Negra", "Puerto de Peña Negra"),
    ("Santa Marina de Orozco", "Orozko"),
    ("Santa Marina de Orozco", "Santa Marina de Orozko"),
    ("Santa Marina de Orozco", "Arrola"),
    ("Alcúdia", "Puig de Sant Martí"),
    ("Óbuda", "Hármashatár-hegy"),
    ("Óbuda", "HHH"),
    ("Csolnok", "Mókus-hegy"),
    ("Vértesszőlős", "Öregkovács-hegy"),
    ("Eged", "Nagy-Eged-hegy"),
    ("Eged", "Nagy-Eged"),
    ("Csákberény", "Orond"),
    ("Csákberény", "Csóka-hegy"),
    ("Sárhegy", "Sár-hegy"),
    ("Tardos", "Gorba-tető"),
    ("Tardos", "Tardosbánya"),
)


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().casefold())
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(without_accents.split())


def upgrade() -> None:
    connection = op.get_bind()
    statement = sa.text(
        """
        INSERT INTO site_aliases (site_id, alias, alias_normalized)
        SELECT site_id, :alias, :alias_normalized
        FROM sites
        WHERE name = :site_name
        ON CONFLICT ON CONSTRAINT uq_site_alias_site_normalized DO NOTHING
        """
    )

    for site_name, alias in ALIASES:
        connection.execute(
            statement,
            {
                "site_name": site_name,
                "alias": alias,
                "alias_normalized": _normalize(alias),
            },
        )


def downgrade() -> None:
    connection = op.get_bind()
    statement = sa.text(
        """
        DELETE FROM site_aliases
        WHERE alias_id IN (
            SELECT site_aliases.alias_id
            FROM site_aliases
            JOIN sites ON sites.site_id = site_aliases.site_id
            WHERE sites.name = :site_name
              AND site_aliases.alias_normalized = :alias_normalized
        )
        """
    )

    for site_name, alias in ALIASES:
        connection.execute(
            statement,
            {
                "site_name": site_name,
                "alias_normalized": _normalize(alias),
            },
        )
