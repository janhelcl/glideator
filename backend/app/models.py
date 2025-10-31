from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    ForeignKey,
    DateTime,
    JSON,
    Boolean,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")
    role = Column(String, nullable=False, server_default="user")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    notifications = relationship(
        "UserNotification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    push_subscriptions = relationship(
        "PushSubscription",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    display_name = Column(String, nullable=True)
    home_lat = Column(Float, nullable=True)
    home_lon = Column(Float, nullable=True)
    preferred_metric = Column(String, nullable=False, server_default="XC0")
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class UserFavorite(Base):
    __tablename__ = "user_favorites"

    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.site_id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Site(Base):
    __tablename__ = "sites"

    site_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Integer, nullable=False)
    lat_gfs = Column(Float, nullable=False)
    lon_gfs = Column(Float, nullable=False)

    predictions = relationship("Prediction", back_populates="site_rel")
    notifications = relationship(
        "UserNotification",
        back_populates="site",
        cascade="all, delete-orphan",
    )


class Prediction(Base):
    __tablename__ = "predictions"

    site_id = Column(Integer, ForeignKey("sites.site_id"), primary_key=True)
    date = Column(Date, primary_key=True)
    metric = Column(String, primary_key=True)
    value = Column(Float, nullable=False)
    computed_at = Column(DateTime, nullable=False)
    gfs_forecast_at = Column(DateTime, nullable=False)

    site_rel = relationship("Site", back_populates="predictions")


class Forecast(Base):
    __tablename__ = "forecasts"

    date = Column(Date, primary_key=True)
    computed_at = Column(DateTime, nullable=False)
    gfs_forecast_at = Column(DateTime, nullable=False)
    lat_gfs = Column(Float, primary_key=True)
    lon_gfs = Column(Float, primary_key=True)
    forecast_9 = Column(JSON, nullable=False)
    forecast_12 = Column(JSON, nullable=False)
    forecast_15 = Column(JSON, nullable=False)


class FlightStats(Base):
    __tablename__ = "flight_stats"

    site_id = Column(Integer, ForeignKey("sites.site_id"), primary_key=True)
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
    __tablename__ = "spots"

    spot_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    wind_direction = Column(String, nullable=True)
    site_id = Column(Integer, ForeignKey("sites.site_id"), nullable=False)

    # Relationship with Site
    site = relationship("Site", backref="spots")


class SiteInfo(Base):
    __tablename__ = "sites_info"

    site_id = Column(Integer, ForeignKey("sites.site_id"), primary_key=True)
    site_name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    html = Column(String, nullable=False)

    # Relationship with Site
    site = relationship("Site", backref="site_info")


class SiteTag(Base):
    __tablename__ = "site_tags"

    site_id = Column(Integer, ForeignKey("sites.site_id"), primary_key=True)
    tag = Column(String, primary_key=True)

    # Relationship with Site
    site = relationship("Site", backref="site_tags")


class UserNotification(Base):
    __tablename__ = "user_notifications"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "site_id",
            "metric",
            "comparison",
            "threshold",
            "lead_time_hours",
            name="uq_user_notification_rule",
        ),
    )

    notification_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.site_id", ondelete="CASCADE"), nullable=False, index=True)
    metric = Column(String, nullable=False)
    comparison = Column(String, nullable=False)
    threshold = Column(Float, nullable=False)
    lead_time_hours = Column(Integer, nullable=False, server_default="0")
    active = Column(Boolean, nullable=False, server_default="true")
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", back_populates="notifications")
    site = relationship("Site", back_populates="notifications")
    events = relationship(
        "NotificationEvent",
        back_populates="notification",
        cascade="all, delete-orphan",
    )


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    subscription_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint = Column(Text, nullable=False, unique=True)
    p256dh = Column(Text, nullable=False)
    auth = Column(Text, nullable=False)
    client_info = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", back_populates="push_subscriptions")
    events = relationship("NotificationEvent", back_populates="subscription")


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    event_id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(
        Integer,
        ForeignKey("user_notifications.notification_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_id = Column(
        Integer,
        ForeignKey("push_subscriptions.subscription_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    triggered_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    payload = Column(JSON, nullable=False)
    delivery_status = Column(String, nullable=False, server_default="queued")

    notification = relationship("UserNotification", back_populates="events")
    subscription = relationship("PushSubscription", back_populates="events")


class ScaledFeature(Base):
    __tablename__ = "scaled_features"

    site_id = Column(Integer, ForeignKey("sites.site_id"), primary_key=True)
    date = Column(Date, primary_key=True)
    features = Column(ARRAY(Float), nullable=False)

    # Relationship with Site
    site = relationship("Site", backref="scaled_features")
