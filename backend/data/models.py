"""SQLAlchemy ORM models for F1 Points Engine."""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text
)
from sqlalchemy.orm import relationship
from backend.db.database import Base


class Constructor(Base):
    __tablename__ = "constructors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    color_hex = Column(String(7), default="#FF0000")
    price = Column(Float, nullable=False)  # in dollars

    drivers = relationship("Driver", back_populates="constructor")
    race_results = relationship("RaceResult", back_populates="constructor")


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String(5), unique=True, nullable=False)
    team_id = Column(Integer, ForeignKey("constructors.id"), nullable=False)
    price = Column(Float, nullable=False)  # in dollars
    nationality = Column(String, default="")
    image_url = Column(String, default="")

    constructor = relationship("Constructor", back_populates="drivers")
    race_results = relationship("RaceResult", back_populates="driver")
    fantasy_points = relationship("FantasyPoints", back_populates="driver")
    score_validations = relationship("ScoreValidation", back_populates="driver")


class Race(Base):
    __tablename__ = "races"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    circuit = Column(String, nullable=False)
    country = Column(String, nullable=False)
    date = Column(String, nullable=False)  # ISO date string
    session_type = Column(String, default="race")  # race | sprint_race
    round_number = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False)
    circuit_type = Column(String, default="balanced")  # street | power | balanced

    results = relationship("RaceResult", back_populates="race")
    fantasy_points = relationship("FantasyPoints", back_populates="race")
    score_validations = relationship("ScoreValidation", back_populates="race")


class RaceResult(Base):
    __tablename__ = "race_results"

    id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    constructor_id = Column(Integer, ForeignKey("constructors.id"), nullable=False)

    qualifying_pos = Column(Integer, nullable=True)
    race_pos = Column(Integer, nullable=True)
    sprint_pos = Column(Integer, nullable=True)
    grid_pos = Column(Integer, nullable=True)

    dnf = Column(Boolean, default=False)
    dsq = Column(Boolean, default=False)
    fastest_lap = Column(Boolean, default=False)
    driver_of_day = Column(Boolean, default=False)

    pit_duration_ms = Column(Integer, nullable=True)

    positions_gained_quali = Column(Integer, default=0)
    positions_gained_race = Column(Integer, default=0)
    overtakes = Column(Integer, default=0)
    q2_reached = Column(Boolean, default=False)
    q3_reached = Column(Boolean, default=False)

    race = relationship("Race", back_populates="results")
    driver = relationship("Driver", back_populates="race_results")
    constructor = relationship("Constructor", back_populates="race_results")


class FantasyPoints(Base):
    __tablename__ = "fantasy_points"

    id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)

    qualifying_pts = Column(Float, default=0.0)
    sprint_pts = Column(Float, default=0.0)
    race_pts = Column(Float, default=0.0)
    total_pts = Column(Float, default=0.0)
    xp_score = Column(Float, default=0.0)

    race = relationship("Race", back_populates="fantasy_points")
    driver = relationship("Driver", back_populates="fantasy_points")


class ScoreValidation(Base):
    __tablename__ = "score_validations"

    id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)

    our_score = Column(Float, nullable=False)
    official_score = Column(Float, nullable=True)
    delta = Column(Float, nullable=True)
    validated_at = Column(DateTime, default=datetime.utcnow)

    race = relationship("Race", back_populates="score_validations")
    driver = relationship("Driver", back_populates="score_validations")
