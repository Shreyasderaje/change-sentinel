from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, UniqueConstraint, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False, default='officer')
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class ProjectAccess(Base):
    __tablename__ = 'project_access'
    __table_args__ = (UniqueConstraint('project_id', 'user_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)

class Imagery(Base):
    __tablename__ = 'imagery'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    acquisition_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    crs: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict | None] = mapped_column(JSON)

class Analysis(Base):
    __tablename__ = 'analyses'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    before_imagery_id: Mapped[str | None] = mapped_column(ForeignKey('imagery.id'))
    after_imagery_id: Mapped[str | None] = mapped_column(ForeignKey('imagery.id'))
    status: Mapped[str] = mapped_column(String(24), default='pending')
    parameters_json: Mapped[dict | None] = mapped_column(JSON)
    results_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class CandidateRegion(Base):
    __tablename__ = 'candidate_regions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    analysis_id: Mapped[str] = mapped_column(ForeignKey('analyses.id'), index=True)
    region_label: Mapped[str] = mapped_column(String(128))
    bbox_pixels: Mapped[dict | None] = mapped_column(JSON)
    area_pixels: Mapped[int | None] = mapped_column(Integer)
    area_m2: Mapped[float | None] = mapped_column(Float)
    geometry_geojson: Mapped[dict | None] = mapped_column(JSON)  # only verified, georeferenced geometry

class Investigation(Base):
    __tablename__ = 'investigations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    region_id: Mapped[str] = mapped_column(ForeignKey('candidate_regions.id'))
    assigned_to_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'))
    status: Mapped[str] = mapped_column(String(32), default='open')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class AnalystDecision(Base):
    __tablename__ = 'analyst_decisions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    investigation_id: Mapped[str] = mapped_column(ForeignKey('investigations.id'), index=True)
    reviewer_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Report(Base):
    __tablename__ = 'reports'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    analysis_id: Mapped[str] = mapped_column(ForeignKey('analyses.id'), index=True)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
