from pydantic import BaseModel, Json, Field, EmailStr, field_validator, ConfigDict
from typing import List, Optional, Literal
from datetime import date, datetime
import os

class PredictionBase(BaseModel):
    date: date
    metric: str
    value: float
    computed_at: datetime
    gfs_forecast_at: datetime

class PredictionCreate(PredictionBase):
    site_id: int

class Prediction(PredictionBase):
    site_id: int
    model_config = ConfigDict(from_attributes=True)

class PredictionValues(BaseModel):
    date: date
    values: List[float]
    computed_at: datetime
    gfs_forecast_at: datetime

class SiteBase(BaseModel):
    name: str
    latitude: float
    longitude: float
    altitude: int
    lat_gfs: float
    lon_gfs: float
    site_id: int

class SiteResponse(BaseModel):
    name: str
    latitude: float
    longitude: float
    site_id: int
    predictions: List[PredictionValues]
    tags: List[str] = []
    model_config = ConfigDict(from_attributes=True)

class Site(SiteResponse):
    pass

class SiteListItem(BaseModel):
    site_id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

class ForecastBase(BaseModel):
    date: date
    computed_at: datetime
    gfs_forecast_at: datetime
    lat_gfs: float
    lon_gfs: float
    forecast_9: Json
    forecast_12: Json
    forecast_15: Json

class ForecastCreate(ForecastBase):
    pass

class Forecast(ForecastBase):
    model_config = ConfigDict(from_attributes=True)

class FlightStatsBase(BaseModel):
    site_id: int
    month: int
    avg_days_over_0: float
    avg_days_over_10: float
    avg_days_over_20: float
    avg_days_over_30: float
    avg_days_over_40: float
    avg_days_over_50: float
    avg_days_over_60: float
    avg_days_over_70: float
    avg_days_over_80: float
    avg_days_over_90: float
    avg_days_over_100: float

class FlightStatsCreate(FlightStatsBase):
    pass

class FlightStats(FlightStatsBase):
    model_config = ConfigDict(from_attributes=True)

class SpotBase(BaseModel):
    spot_id: int
    name: str
    latitude: float
    longitude: float
    altitude: int
    type: str
    wind_direction: Optional[str] = None
    site_id: int

class SpotCreate(SpotBase):
    pass

class Spot(SpotBase):
    model_config = ConfigDict(from_attributes=True)

class SourceInfo(BaseModel):
    source_name: str
    source_link: str

class SiteInfoBase(BaseModel):
    site_id: int
    site_name: str
    country: str
    html: str

class SiteInfoCreate(SiteInfoBase):
    pass

class SiteInfo(SiteInfoBase):
    model_config = ConfigDict(from_attributes=True)

class SiteTagBase(BaseModel):
    site_id: int
    tag: str

class SiteTagCreate(SiteTagBase):
    pass

class SiteTag(SiteTagBase):
    model_config = ConfigDict(from_attributes=True)

class TripPlanRequest(BaseModel):
    start_date: date
    end_date: date
    metric: Literal['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100'] = Field(default='XC0', description="Metric to use for trip planning")
    user_latitude: Optional[float] = Field(default=None, description="User's latitude for distance filtering")
    user_longitude: Optional[float] = Field(default=None, description="User's longitude for distance filtering")
    max_distance_km: Optional[float] = Field(default=None, description="Maximum distance from user location in kilometers")
    min_altitude_m: Optional[int] = Field(default=None, description="Minimum altitude in meters")
    max_altitude_m: Optional[int] = Field(default=None, description="Maximum altitude in meters")
    required_tags: Optional[List[str]] = Field(default=None, description="List of tags that each site must include (logical AND)")
    offset: Optional[int] = Field(default=0, description="Number of sites to skip for pagination")
    limit: Optional[int] = Field(default=10, description="Maximum number of sites to return")

class DailyProbability(BaseModel):
    date: date
    probability: float
    source: Literal['forecast', 'historical']

class SiteSuggestion(BaseModel):
    site_name: str
    average_flyability: float # Based on XC0
    site_id: str
    latitude: float
    longitude: float
    altitude: int
    daily_probabilities: List[DailyProbability]
    distance_km: Optional[float] = Field(default=None, description="Distance from user location in kilometers")

class TripPlanResponse(BaseModel):
    sites: List[SiteSuggestion]
    total_count: int
    has_more: bool

# --- Auth Schemas ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        min_len = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
        if len(v) < min_len:
            raise ValueError(f"Password must be at least {min_len} characters long")
        # Require at least 3 of 4 categories: lower, upper, digit, special
        lower = any(c.islower() for c in v)
        upper = any(c.isupper() for c in v)
        digit = any(c.isdigit() for c in v)
        special = any(c in "!@#$%^&*()-_=+[]{};:'\",.<>/?|`~" for c in v)
        if sum([lower, upper, digit, special]) < 3:
            raise ValueError("Password must include at least three of: lower, upper, digit, special")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    user_id: int
    email: str
    is_active: bool
    role: str
    model_config = ConfigDict(from_attributes=True)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

# --- Profiles & Favorites ---

class UserProfileOut(BaseModel):
    user_id: int
    display_name: Optional[str] = None
    home_lat: Optional[float] = None
    home_lon: Optional[float] = None
    preferred_metric: str

class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    home_lat: Optional[float] = None
    home_lon: Optional[float] = None
    preferred_metric: Optional[str] = None

class FavoriteRequest(BaseModel):
    site_id: int


NotificationComparison = Literal['gt', 'gte', 'lt', 'lte', 'eq']


class NotificationBase(BaseModel):
    site_id: int
    metric: str
    comparison: NotificationComparison
    threshold: float
    lead_time_hours: int = Field(default=0, ge=0, le=168, description="Hours before forecasted event to notify")

    @field_validator("metric")
    @classmethod
    def metric_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Metric must not be empty")
        return v


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(BaseModel):
    metric: Optional[str] = None
    comparison: Optional[NotificationComparison] = None
    threshold: Optional[float] = None
    lead_time_hours: Optional[int] = Field(default=None, ge=0, le=168)
    active: Optional[bool] = None

    @field_validator("metric")
    @classmethod
    def metric_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Metric must not be empty")
        return v


class NotificationOut(NotificationBase):
    notification_id: int
    active: bool
    last_triggered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PushSubscriptionBase(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    client_info: Optional[dict] = None

    @field_validator("endpoint", "p256dh", "auth")
    @classmethod
    def ensure_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Value must not be empty")
        return v


class PushSubscriptionCreate(PushSubscriptionBase):
    pass


class PushSubscriptionOut(PushSubscriptionBase):
    subscription_id: int
    is_active: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class NotificationEventOut(BaseModel):
    event_id: int
    notification_id: int
    subscription_id: Optional[int]
    triggered_at: datetime
    payload: dict
    delivery_status: str
    model_config = ConfigDict(from_attributes=True)
