"""Typed domain models for the Querido Diário API.

These mirror the response shapes defined by the upstream FastAPI application
(`api/api.py` in https://github.com/okfn-brasil/querido-diario-api) so that the rest
of this package never has to work with raw, untyped dictionaries.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class SortBy(StrEnum):
    """How the `/gazettes` search results should be ordered."""

    RELEVANCE = "relevance"
    DESCENDING_DATE = "descending_date"
    ASCENDING_DATE = "ascending_date"


class City(BaseModel):
    """A Brazilian municipality known to Querido Diário."""

    model_config = ConfigDict(extra="ignore")

    territory_id: str
    territory_name: str
    state_code: str
    publication_urls: list[str] | None = None
    level: str | None = None
    availability_date: str | None = None


class CitiesResponse(BaseModel):
    """Response body of `GET /cities`."""

    model_config = ConfigDict(extra="ignore")

    cities: list[City]


class CityResponse(BaseModel):
    """Response body of `GET /cities/{territory_id}`."""

    model_config = ConfigDict(extra="ignore")

    city: City


class Gazette(BaseModel):
    """A single official gazette matching a search, with excerpts of matched text."""

    model_config = ConfigDict(extra="ignore")

    territory_id: str
    territory_name: str
    state_code: str
    date: date
    scraped_at: datetime
    url: str
    excerpts: list[str] = []
    edition: str | None = None
    is_extra_edition: bool | None = None
    txt_url: str | None = None


class GazetteSearchResponse(BaseModel):
    """Response body of `GET /gazettes`."""

    model_config = ConfigDict(extra="ignore")

    total_gazettes: int
    gazettes: list[Gazette]
