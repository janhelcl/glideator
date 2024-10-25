from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from .database import Base

class Site(Base):
    __tablename__ = 'sites'
    
    name = Column(String, primary_key=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Integer, nullable=False)
    lat_gfs = Column(Float, nullable=False)
    lon_gfs = Column(Float, nullable=False)
    
    predictions = relationship("Prediction", back_populates="site_rel")

class Prediction(Base):
    __tablename__ = 'predictions'
    
    site = Column(String, ForeignKey('sites.name'), primary_key=True)
    date = Column(Date, primary_key=True)
    metric = Column(String, primary_key=True)
    value = Column(Float, nullable=False)
    computed_at = Column(DateTime, nullable=False)
    gfs_forecast_at = Column(DateTime, nullable=False)
    
    site_rel = relationship("Site", back_populates="predictions")

class Forecast(Base):
    __tablename__ = 'forecasts'
    
    date = Column(Date, primary_key=True)
    lat_gfs = Column(Float, primary_key=True)
    lon_gfs = Column(Float, primary_key=True)
    forecast_9 = Column(JSON, nullable=False)
    forecast_12 = Column(JSON, nullable=False)
    forecast_15 = Column(JSON, nullable=False)
