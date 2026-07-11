"""
ORM models. These mirror migrations/schema.sql exactly — schema.sql is the
source of truth (applied directly by Postgres on first container start),
these classes are how the Python app reads/writes that same structure.
"""
from datetime import date, datetime

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text, func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    sub_county = Column(String(100))

    price_entries = relationship("PriceEntry", back_populates="region")


class Species(Base):
    __tablename__ = "species"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)

    price_entries = relationship("PriceEntry", back_populates="species")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(150), nullable=False)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="agent")  # agent | official | admin
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    price_entries = relationship("PriceEntry", back_populates="agent")


class PriceEntry(Base):
    __tablename__ = "price_entries"
    __table_args__ = (
        CheckConstraint("price_kes > 0", name="price_kes_positive"),
        CheckConstraint(
            "outlier_status IN ('valid', 'flagged', 'rejected')",
            name="valid_outlier_status",
        ),
    )

    id = Column(Integer, primary_key=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    species_id = Column(Integer, ForeignKey("species.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)

    price_kes = Column(Integer, nullable=False)
    market_date = Column(Date, nullable=False, default=date.today)
    entered_at = Column(DateTime(timezone=True), server_default=func.now())

    notes = Column(Text)

    outlier_status = Column(String(20), nullable=False, default="valid")
    outlier_reason = Column(Text)
    outlier_score = Column(Numeric)

    region = relationship("Region", back_populates="price_entries")
    species = relationship("Species", back_populates="price_entries")
    agent = relationship("Agent", back_populates="price_entries")


class ClimateBulletin(Base):
    """
    Sync-when-online, use-offline: whatever was last logged here (a field
    observation, or a bulletin transcribed from NDMA/Kenya Met during a
    connectivity window) is what the dashboard and AI read. Nothing here
    fetches live over the network.
    """
    __tablename__ = "climate_bulletins"
    __table_args__ = (
        CheckConstraint(
            "drought_status IN ('normal', 'alert', 'alarm', 'emergency')",
            name="valid_drought_status",
        ),
    )

    id = Column(Integer, primary_key=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)

    bulletin_date = Column(Date, nullable=False)
    drought_status = Column(String(20), nullable=False, default="normal")
    rainfall_mm = Column(Numeric)
    temperature_c = Column(Numeric)

    source = Column(String(200), nullable=False, default="Field observation")
    notes = Column(Text)

    entered_at = Column(DateTime(timezone=True), server_default=func.now())

    region = relationship("Region")
    agent = relationship("Agent")


class DiseaseReport(Base):
    """
    Same never-delete, always-reviewable pattern as PriceEntry — a
    wrongly-suppressed real outbreak is far more dangerous than a false
    alarm sitting flagged for review.
    """
    __tablename__ = "disease_reports"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="valid_severity",
        ),
        CheckConstraint(
            "review_status IN ('reported', 'confirmed', 'false_alarm')",
            name="valid_review_status",
        ),
    )

    id = Column(Integer, primary_key=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    species_id = Column(Integer, ForeignKey("species.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)

    report_date = Column(Date, nullable=False)
    disease_name = Column(String(150), nullable=False)
    symptoms = Column(Text)
    affected_count = Column(Integer)
    severity = Column(String(20), nullable=False, default="medium")

    review_status = Column(String(20), nullable=False, default="reported")
    review_notes = Column(Text)

    entered_at = Column(DateTime(timezone=True), server_default=func.now())

    region = relationship("Region")
    species = relationship("Species")
    agent = relationship("Agent")
