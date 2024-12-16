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

class SiteBase(BaseModel):
    name: str
    latitude: float
    longitude: float
    altitude: int
    lat_gfs: float
    lon_gfs: float

class SiteCreate(SiteBase):
    site_id: int

class SiteResponse(SiteBase):
    site_id: int
    predictions: List[Prediction] = []

    class Config:
        from_attributes = True

class Site(SiteResponse):
    pass

class ForecastBase(BaseModel):
    date: date
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
