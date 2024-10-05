from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime

class PredictionBase(BaseModel):
    date: date
    metric: str
    value: float
    computed_at: datetime
    gfs_forecast_at: datetime

class PredictionCreate(PredictionBase):
    site: str

class Prediction(PredictionBase):
    site: str

    class Config:
        orm_mode = True

class SiteBase(BaseModel):
    name: str
    latitude: float
    longitude: float
    altitude: int
    lat_gfs: float
    lon_gfs: float

class SiteCreate(SiteBase):
    pass

class Site(SiteBase):
    predictions: List[Prediction] = []

    class Config:
        orm_mode = True