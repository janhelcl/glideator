from pydantic import BaseModel, Json, Field
from typing import List, Optional, Literal
from datetime import date, datetime

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

    class Config:
        from_attributes = True

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

    class Config:
        orm_mode = True

class Site(SiteResponse):
    pass

class SiteListItem(BaseModel):
    site_id: int
    name: str

    class Config:
        from_attributes = True

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
    class Config:
        from_attributes = True

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
    class Config:
        from_attributes = True

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
    class Config:
        from_attributes = True

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
    class Config:
        from_attributes = True

class TripPlanRequest(BaseModel):
    start_date: date
    end_date: date
    metric: Literal['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100'] = Field(default='XC0', description="Metric to use for trip planning")
    user_latitude: Optional[float] = Field(default=None, description="User's latitude for distance filtering")
    user_longitude: Optional[float] = Field(default=None, description="User's longitude for distance filtering")
    max_distance_km: Optional[float] = Field(default=None, description="Maximum distance from user location in kilometers")
    min_altitude_m: Optional[int] = Field(default=None, description="Minimum altitude in meters")
    max_altitude_m: Optional[int] = Field(default=None, description="Maximum altitude in meters")

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
