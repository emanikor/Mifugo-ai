"""
Glues the retriever (exact DB rows) and the local LLM (natural language
phrasing) together.

The prompt is deliberately strict: the LLM is told to only use the numbers
it's given, and to say so plainly if there isn't enough data, rather than
estimate or use outside knowledge. This matters a lot here — a hallucinated
price, drought status, or disease claim could directly cost a pastoralist
money or cause needless panic.

Milestone 4 note: questions are routed by simple keyword intent
(see rag/retriever.classify_intent) to one of three prompt builders below,
rather than always going through the price path. This keeps each prompt
focused on one kind of data instead of dumping everything into one giant
context the small model has to sort through.
"""
from sqlalchemy.orm import Session

from app.rag.llm_client import OllamaUnavailableError, generate
from app.rag.retriever import (
    classify_intent,
    retrieve,
    retrieve_climate,
    retrieve_disease,
)
from app.schemas import ChatResponse, PriceEntryOut

SYSTEM_PROMPT = """You are a market and field-conditions assistant for \
pastoralists, NGO workers, and county officials in Turkana County, Kenya. \
You answer questions about livestock prices, climate/drought conditions, \
and livestock disease reports using ONLY the data provided to you below. \
Do not use any outside knowledge. If the provided data does not answer the \
question, say so clearly instead of guessing. Keep answers short, concrete, \
and in plain language — many users are reading this on a small screen with \
limited literacy in technical English. If disease data is unverified \
("reported" but not "confirmed"), say so explicitly rather than stating it \
as fact."""


def _build_price_prompt(question: str, context) -> str:
    if not context.rows:
        data_summary = "No matching validated price records were found."
    else:
        lines = [
            f"- {row.market_date}: {row.price_kes} KES "
            f"({context.species_name or 'species'} in "
            f"{context.region_name or 'region'})"
            for row in context.rows[:20]  # cap what we feed the small model
        ]
        avg_line = (
            f"\nAverage across these {len(context.rows)} records: "
            f"{context.average_price:.0f} KES"
            if context.average_price is not None
            else ""
        )
        data_summary = "\n".join(lines) + avg_line

    return (
        f"Question: {question}\n\n"
        f"Relevant validated price records "
        f"({context.date_from} to {context.date_to}):\n{data_summary}\n\n"
        "Answer the question using only the data above."
    )


def _build_climate_prompt(question: str, context) -> str:
    if not context.bulletins:
        data_summary = "No climate bulletins on record for this region."
    else:
        lines = [
            f"- {b.bulletin_date} ({b.region.name if b.region else 'unknown region'}): "
            f"drought status = {b.drought_status.upper()}, "
            f"rainfall = {b.rainfall_mm if b.rainfall_mm is not None else 'not reported'} mm, "
            f"source: {b.source}"
            for b in context.bulletins[:20]
        ]
        data_summary = "\n".join(lines)

    return (
        f"Question: {question}\n\n"
        f"Climate bulletins on record:\n{data_summary}\n\n"
        "Answer the question using only the data above. Note that this data "
        "reflects the last time it was synced, not necessarily today."
    )


def _build_disease_prompt(question: str, context) -> str:
    if not context.reports:
        data_summary = "No disease reports on record for this region/species."
    else:
        lines = [
            f"- {r.report_date} ({r.disease_name}, "
            f"status: {r.review_status}): "
            f"{r.affected_count if r.affected_count is not None else 'unknown'} animals affected. "
            f"Symptoms: {r.symptoms or 'not described'}"
            for r in context.reports[:20]
        ]
        data_summary = "\n".join(lines)

    return (
        f"Question: {question}\n\n"
        f"Disease reports on record:\n{data_summary}\n\n"
        "Answer the question using only the data above, and clearly "
        "distinguish 'confirmed' reports from unverified ones."
    )


def answer_question(db: Session, question: str) -> ChatResponse:
    intent = classify_intent(question)

    if intent == "climate":
        context = retrieve_climate(db, question)
        prompt = _build_climate_prompt(question, context)
        supporting_data = []  # TODO: add ClimateBulletinOut support to
                               # ChatResponse if the frontend should show
                               # structured climate evidence, not just prose.
    elif intent == "disease":
        context = retrieve_disease(db, question)
        prompt = _build_disease_prompt(question, context)
        supporting_data = []  # same TODO as above, for DiseaseReportOut.
    else:
        context = retrieve(db, question)
        prompt = _build_price_prompt(question, context)
        supporting_data = [PriceEntryOut.model_validate(r) for r in context.rows]

    try:
        answer_text = generate(prompt, system=SYSTEM_PROMPT)
    except OllamaUnavailableError as exc:
        # Surface this clearly to the frontend rather than a generic 500 —
        # "the AI is down" is actionable info for an official in the field.
        answer_text = f"[AI engine unavailable] {exc}"

    return ChatResponse(answer=answer_text, supporting_data=supporting_data)
