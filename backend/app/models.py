from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from .database import Base

class Site(Base):
    __tablename__ = 'sites'
    
    site_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Integer, nullable=False)
    lat_gfs = Column(Float, nullable=False)
    lon_gfs = Column(Float, nullable=False)
    
    predictions = relationship("Prediction", back_populates="site_rel")

class Prediction(Base):
    __tablename__ = 'predictions'
    
    site_id = Column(Integer, ForeignKey('sites.site_id'), primary_key=True)
    date = Column(Date, primary_key=True)
    metric = Column(String, primary_key=True)
    value = Column(Float, nullable=False)
    computed_at = Column(DateTime, nullable=False)
    gfs_forecast_at = Column(DateTime, nullable=False)
    
    site_rel = relationship("Site", back_populates="predictions")

class Forecast(Base):
    __tablename__ = 'forecasts'
    
    date = Column(Date, primary_key=True)
    computed_at = Column(DateTime, nullable=False)
    gfs_forecast_at = Column(DateTime, nullable=False)
    lat_gfs = Column(Float, primary_key=True)
    lon_gfs = Column(Float, primary_key=True)
    forecast_9 = Column(JSON, nullable=False)
    forecast_12 = Column(JSON, nullable=False)
    forecast_15 = Column(JSON, nullable=False)

class FlightStats(Base):
    __tablename__ = 'flight_stats'
    
    site_id = Column(Integer, ForeignKey('sites.site_id'), primary_key=True)
    month = Column(Integer, primary_key=True)
    avg_days_over_0 = Column(Float, nullable=False)
    avg_days_over_10 = Column(Float, nullable=False)
    avg_days_over_20 = Column(Float, nullable=False)
    avg_days_over_30 = Column(Float, nullable=False)
    avg_days_over_40 = Column(Float, nullable=False)
    avg_days_over_50 = Column(Float, nullable=False)
    avg_days_over_60 = Column(Float, nullable=False)
    avg_days_over_70 = Column(Float, nullable=False)
    avg_days_over_80 = Column(Float, nullable=False)
    avg_days_over_90 = Column(Float, nullable=False)
    avg_days_over_100 = Column(Float, nullable=False)
    
    # Relationship with Site
    site = relationship("Site", backref="flight_stats")

class Spot(Base):
    __tablename__ = 'spots'
    
    spot_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    wind_direction = Column(String, nullable=True)
    site_id = Column(Integer, ForeignKey('sites.site_id'), nullable=False)
    
    # Relationship with Site
    site = relationship("Site", backref="spots")

class SiteInfo(Base):
    __tablename__ = 'sites_info'
    
    site_id = Column(Integer, ForeignKey('sites.site_id'), primary_key=True)
    site_name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    description = Column(String, nullable=False)
    facilities = Column(String, nullable=False)
    access = Column(String, nullable=False)
    seasonality = Column(String, nullable=False)
    risks = Column(String, nullable=False)
    sources = Column(JSON, nullable=False)
    
    # Relationship with Site
    site = relationship("Site", backref="site_info")
