"""
Pydantic schemas — the contract between the FastAPI backend and the React
frontend. Keep these in sync with app/models.py by hand; this is a small
enough project that an auto-generated OpenAPI client (frontend/src/api)
is enough to keep both sides honest without extra tooling.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---- Auth ----

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str


# ---- Lookups ----

class RegionOut(BaseModel):
    id: int
    name: str
    sub_county: Optional[str] = None

    class Config:
        from_attributes = True


class SpeciesOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


# ---- Price entries ----

class PriceEntryCreate(BaseModel):
    region_id: int
    species_id: int
    price_kes: int = Field(gt=0, description="Price in Kenyan Shillings")
    market_date: date
    notes: Optional[str] = None


class PriceEntryOut(BaseModel):
    id: int
    region_id: int
    species_id: int
    agent_id: int
    price_kes: int
    market_date: date
    entered_at: datetime
    notes: Optional[str] = None
    outlier_status: str
    outlier_reason: Optional[str] = None
    outlier_score: Optional[float] = None

    class Config:
        from_attributes = True


# ---- Chat / RAG ----

class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    answer: str
    # The raw rows used to ground the answer, so officials can verify the
    # AI didn't hallucinate a number — transparency matters more than polish.
    supporting_data: list[PriceEntryOut] = []


# ---- Climate (Milestone 4) ----

class ClimateBulletinCreate(BaseModel):
    region_id: int
    bulletin_date: date
    drought_status: str = Field(
        default="normal", description="normal | alert | alarm | emergency"
    )
    rainfall_mm: Optional[float] = None
    temperature_c: Optional[float] = None
    source: str = "Field observation"
    notes: Optional[str] = None


class ClimateBulletinOut(BaseModel):
    id: int
    region_id: int
    agent_id: int
    bulletin_date: date
    drought_status: str
    rainfall_mm: Optional[float] = None
    temperature_c: Optional[float] = None
    source: str
    notes: Optional[str] = None
    entered_at: datetime

    class Config:
        from_attributes = True


# ---- Disease reports (Milestone 4) ----

class DiseaseReportCreate(BaseModel):
    region_id: int
    species_id: int
    report_date: date
    disease_name: str = Field(min_length=1, max_length=150)
    symptoms: Optional[str] = None
    affected_count: Optional[int] = Field(default=None, ge=0)
    severity: str = Field(default="medium", description="low | medium | high | critical")


class DiseaseReportOut(BaseModel):
    id: int
    region_id: int
    species_id: int
    agent_id: int
    report_date: date
    disease_name: str
    symptoms: Optional[str] = None
    affected_count: Optional[int] = None
    severity: str
    review_status: str
    review_notes: Optional[str] = None
    entered_at: datetime

    class Config:
        from_attributes = True


# ---- Alerts (Milestone 4) ----
# A computed feed, not a stored table — see rag/retriever.py-style reasoning
# in app/alerts.py for why this stays derived rather than duplicated.

class AlertOut(BaseModel):
    type: str          # 'drought' | 'disease'
    severity: str       # normal | alert | alarm | emergency (drought) or low..critical (disease)
    region_id: int
    region_name: str
    title: str
    detail: str
    date: date
