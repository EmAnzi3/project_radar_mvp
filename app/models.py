from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProjectRecord(BaseModel):
    source: str
    source_url: Optional[str] = None
    external_id: Optional[str] = None

    title: str
    description: Optional[str] = None

    region: Optional[str] = None
    province: Optional[str] = None
    municipality: Optional[str] = None
    address: Optional[str] = None

    sector: Optional[str] = None
    category: Optional[str] = None
    intervention_type: Optional[str] = None
    phase: Optional[str] = None

    client: Optional[str] = None
    client_type: Optional[str] = None

    designer: Optional[str] = None
    works_director: Optional[str] = None
    rup: Optional[str] = None
    contractor: Optional[str] = None

    estimated_value_eur: Optional[float] = None
    power_mw: Optional[float] = None
    surface_mq: Optional[float] = None

    cup: Optional[str] = None
    cig: Optional[str] = None
    funding: Optional[str] = None

    tender_date: Optional[str] = None
    works_start: Optional[str] = None
    works_end: Optional[str] = None

    commercial_score: int = 0
    ai_notes: Optional[str] = None

    first_seen: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    last_seen: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
