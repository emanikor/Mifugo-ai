"""
Retriever for the RAG pipeline.

Deliberate design choice: this is NOT a vector-embedding retriever. Livestock
price data is structured (region, species, date, price) — turning it into
text chunks and embedding it would throw away the exact structure that makes
it queryable, and would risk the LLM "reading" approximate semantic matches
instead of exact numbers. Officials asking "average camel price in Lodwar
this week" need an exact number, not a plausible-sounding one.

Instead: we do lightweight keyword extraction against known regions/species
in the database, then run a direct, parameterized SQL query. The LLM's job
(see rag/pipeline.py) is to phrase the answer in natural language, not to
compute the numbers.

TODO: this keyword-matching intent parser is intentionally simple to start.
Real natural-language questions will have more variety than these examples
handle — expand region/species matching (spelling variants, Swahili/Turkana
names) as real usage surfaces gaps.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ClimateBulletin, DiseaseReport, PriceEntry, Region, Species


@dataclass
class RetrievedContext:
    region_name: str | None
    species_name: str | None
    date_from: date | None
    date_to: date | None
    rows: list[PriceEntry] = field(default_factory=list)
    average_price: float | None = None


@dataclass
class ClimateContext:
    region_name: str | None
    bulletins: list[ClimateBulletin] = field(default_factory=list)


@dataclass
class DiseaseContext:
    region_name: str | None
    species_name: str | None
    reports: list[DiseaseReport] = field(default_factory=list)


# Keyword sets for routing a question to the right retriever. Deliberately
# simple (see module docstring) — expand as real usage surfaces gaps in
# what pastoralists/officials actually ask.
_CLIMATE_KEYWORDS = (
    "drought", "rain", "rainfall", "weather", "climate", "dry", "water",
)
_DISEASE_KEYWORDS = (
    "disease", "sick", "sickness", "outbreak", "dying", "died", "illness",
    "symptom", "infected", "infection",
)


def classify_intent(question: str) -> str:
    """Returns 'climate' | 'disease' | 'price' — used by rag/pipeline.py to
    pick which retriever(s) to run."""
    q_lower = question.lower()
    if any(kw in q_lower for kw in _CLIMATE_KEYWORDS):
        return "climate"
    if any(kw in q_lower for kw in _DISEASE_KEYWORDS):
        return "disease"
    return "price"


def _extract_region(db: Session, question: str) -> Region | None:
    q_lower = question.lower()
    for region in db.query(Region).all():
        if region.name.lower() in q_lower:
            return region
    return None


def _extract_species(db: Session, question: str) -> Species | None:
    q_lower = question.lower()
    for sp in db.query(Species).all():
        # naive plural handling (goats -> goat, camels -> camel, etc.)
        if sp.name.lower() in q_lower or f"{sp.name.lower()}s" in q_lower:
            return sp
    return None


def _extract_date_range(question: str) -> tuple[date, date]:
    """
    Very small stub for time-range parsing. Recognizes a few common phrases;
    defaults to the last 30 days if nothing matches.

    TODO: replace with a proper lightweight date parser (e.g. dateparser)
    once we confirm it can run fully offline (no external data fetch for
    timezone/locale databases at import time).
    """
    today = date.today()
    q_lower = question.lower()

    if "today" in q_lower:
        return today, today
    if "yesterday" in q_lower:
        y = today - timedelta(days=1)
        return y, y
    if "last week" in q_lower or "past week" in q_lower:
        return today - timedelta(days=7), today
    if "last month" in q_lower or "past month" in q_lower:
        return today - timedelta(days=30), today

    return today - timedelta(days=30), today


def retrieve(db: Session, question: str) -> RetrievedContext:
    region = _extract_region(db, question)
    species = _extract_species(db, question)
    date_from, date_to = _extract_date_range(question)

    query = db.query(PriceEntry).filter(
        PriceEntry.outlier_status == "valid",
        PriceEntry.market_date >= date_from,
        PriceEntry.market_date <= date_to,
    )
    if region is not None:
        query = query.filter(PriceEntry.region_id == region.id)
    if species is not None:
        query = query.filter(PriceEntry.species_id == species.id)

    rows = query.order_by(PriceEntry.market_date.desc()).limit(50).all()

    avg_price = None
    if rows:
        avg_price = float(
            db.query(func.avg(PriceEntry.price_kes))
            .filter(PriceEntry.id.in_([r.id for r in rows]))
            .scalar()
        )

    return RetrievedContext(
        region_name=region.name if region else None,
        species_name=species.name if species else None,
        date_from=date_from,
        date_to=date_to,
        rows=rows,
        average_price=avg_price,
    )


def retrieve_climate(db: Session, question: str) -> ClimateContext:
    """Latest bulletin per region matching the question (or all regions'
    latest bulletins if none is named) — mirrors the "read most recent
    synced data" pattern described in app/models.py ClimateBulletin."""
    region = _extract_region(db, question)

    query = db.query(ClimateBulletin)
    if region is not None:
        query = query.filter(ClimateBulletin.region_id == region.id)

    bulletins = query.order_by(ClimateBulletin.bulletin_date.desc()).limit(20).all()

    return ClimateContext(region_name=region.name if region else None, bulletins=bulletins)


def retrieve_disease(db: Session, question: str) -> DiseaseContext:
    """Disease reports not yet dismissed as false alarms — a question about
    disease shouldn't be answered using reports an official already ruled
    out, but SHOULD include unreviewed ones (better to over-inform here
    than suppress a real early warning)."""
    region = _extract_region(db, question)
    species = _extract_species(db, question)

    query = db.query(DiseaseReport).filter(DiseaseReport.review_status != "false_alarm")
    if region is not None:
        query = query.filter(DiseaseReport.region_id == region.id)
    if species is not None:
        query = query.filter(DiseaseReport.species_id == species.id)

    reports = query.order_by(DiseaseReport.report_date.desc()).limit(20).all()

    return DiseaseContext(
        region_name=region.name if region else None,
        species_name=species.name if species else None,
        reports=reports,
    )
