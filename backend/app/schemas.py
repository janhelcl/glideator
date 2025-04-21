from pydantic import BaseModel, Json
from typing import List, Optional
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
