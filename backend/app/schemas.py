from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class PredictionBase(BaseModel):
    date: date
    metric: str
    value: float

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