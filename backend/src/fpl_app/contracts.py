from typing import Any, Literal

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(allow_inf_nan=False)


class Player(BaseModel):
    player_id: int
    name: str
    club: int
    position: Literal[1, 2, 3, 4]
    market_price_units: int = Field(ge=0, strict=True)
    points_per_game: float = 0
    minutes: int = 0
    appearances: int = 0
    availability: float | None = Field(default=None, ge=0, le=1)
    goals: int = 0
    assists: int = 0
    clean_sheets: int = 0
    status: str = "a"


class Pick(BaseModel):
    player_id: int
    purchase_price_units: int | None = Field(default=None, ge=0, strict=True)
    selling_price_units: int | None = Field(default=None, ge=0, strict=True)
    selling_price_market_units: int | None = Field(default=None, ge=0, strict=True)
    selling_price_provenance: str = "unknown"
    confirmed_at: str | None = None
    acquisition_id: str | None = None
    position: int = Field(default=1, ge=1, le=15)
    is_captain: bool = False
    is_vice_captain: bool = False


class ManagerState(BaseModel):
    team_id: int
    state_version: int = 1
    season: str = "2026/27"
    next_event: int = Field(default=8, ge=1, le=38)
    public_source_event: int | None = None
    data_mode: Literal["demo", "live"] = "demo"
    snapshot_id: str
    bank_units: int | None = Field(default=None, ge=0, strict=True)
    free_transfers_at_event_start: int | None = Field(default=None, ge=1, le=5)
    transfers_made_this_event: int | None = Field(default=None, ge=0, strict=True)
    confirmed_hit_points: int | None = Field(default=None, ge=0)
    financial_provenance: dict[str, str] = Field(default_factory=dict)
    financial_confirmed_at: str | None = None
    transfer_ledger: list[dict[str, Any]] = Field(default_factory=list)
    current_chip_confirmed: bool = False
    club_limit_exception: bool = False
    current_chip: str | None = None
    chips: dict[str, bool | None] = Field(default_factory=dict)
    previous_free_hit_event: int | None = None
    persistent_picks: list[Pick] | None = None
    event_start_picks: list[Pick] | None = None
    event_start_bank_units: int | None = Field(default=None, ge=0, strict=True)
    picks: list[Pick]
    warnings: list[str] = Field(default_factory=list)


class Fixture(BaseModel):
    fixture_id: int
    event: int | None
    home_club: int
    away_club: int
    kickoff: str | None = None
    home_difficulty: int = 3
    away_difficulty: int = 3


class Projection(BaseModel):
    player_id: int
    fixture_id: int
    event: int
    expected_points: float
    expected_minutes: float = Field(ge=0, le=90)
    appearance_probability: float | None = Field(default=None, ge=0, le=1)
    start_probability: float | None = Field(default=None, ge=0, le=1)
    minutes_60_probability: float | None = Field(default=None, ge=0, le=1)
    point_quantiles: dict[str, float] | None = None
    components: dict[str, float | None] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)


class ProjectionRun(BaseModel):
    projection_run_id: str
    snapshot_id: str
    source_cutoff: str
    model_family: str = "baseline"
    model_status: str = "baseline"
    data_mode: Literal["demo", "live"]
    rules_version: str = "2026-27-v1"
    horizon_events: int = Field(ge=1, le=8)
    projections: list[Projection]
    fixtures: list[Fixture] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Settings(BaseModel):
    horizon_events: int = Field(default=6, ge=1, le=8)
    max_additional_hit_points: int = Field(default=4, ge=0, le=80)
    max_transfers_this_event: int | None = Field(default=None, ge=0, le=20)
    locked_player_ids: list[int] = Field(default_factory=list)
    excluded_player_ids: list[int] = Field(default_factory=list)
    chip_policy: Literal["none", "wildcard", "free_hit", "bench_boost", "triple_captain"] = "none"
    solver_time_limit_seconds: float = Field(default=15, gt=0, le=60)


class AnalysisRequest(BaseModel):
    analysis_mode: Literal["lineup", "transfers"] = "transfers"
    team_id: int
    expected_state_version: int
    projection_run_id: str
    settings: Settings = Field(default_factory=Settings)


class Plan(BaseModel):
    plan_id: str
    state_version: int
    projection_run_id: str
    input_fingerprint: str
    name: str
    actions: list[dict[str, Any]] = Field(default_factory=list)
    weeks: list[dict[str, Any]] = Field(default_factory=list)
    gross_points: float
    total_hits: int
    incremental_hits: int
    net_points: float
    delta_to_baseline: float = 0
    bank_units: int | None = None
    free_transfers_next: int | None = None
    lineup: dict[str, Any]
    chip: str | None = None
    this_week_net: float | None = None
    this_week_delta: float | None = None
    assumptions: list[str] = Field(default_factory=list)
    solver: dict[str, Any] = Field(default_factory=dict)


class ChipAdvice(BaseModel):
    chip: Literal["wildcard", "free_hit", "bench_boost", "triple_captain"]
    status: Literal["used", "unavailable", "save", "play_this_week", "not_evaluated"]
    this_week_points: float | None = None
    comparison_points: float | None = None
    reason: str


class Recommendation(BaseModel):
    recommendation_id: str
    baseline_plan: Plan
    alternatives: list[Plan]
    gameweek_optimum: Plan | None = None
    chip_advice: list[ChipAdvice] = Field(default_factory=list)
    source_cutoff: str
    rules_version: str
    state_version: int
    projection_run_id: str
    warnings: list[str] = Field(default_factory=list)
