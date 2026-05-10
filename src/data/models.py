# src/data/models.py
from __future__ import annotations
import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Boolean, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship

JST = ZoneInfo("Asia/Tokyo")

def _now_jst():
    return datetime.datetime.now(JST)

Base = declarative_base()


class ValuationCase(Base):
    __tablename__ = "valuation_cases"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    case_name       = Column(String(200), nullable=False)
    stock_price     = Column(Float, nullable=False)
    strike_price    = Column(Float, nullable=False)
    risk_free_rate  = Column(Float, nullable=False)
    volatility      = Column(Float, nullable=False)
    time_to_expiry  = Column(Float, nullable=False)
    option_type     = Column(String(10), default="call")
    dividend_yield  = Column(Float, default=0.0)
    binomial_steps  = Column(Integer, default=100)
    mc_simulations  = Column(Integer, default=10000)
    bs_price        = Column(Float)
    binomial_price  = Column(Float)
    mc_price        = Column(Float)
    weighted_price  = Column(Float)
    delta           = Column(Float)
    gamma           = Column(Float)
    theta           = Column(Float)
    vega            = Column(Float)
    rho             = Column(Float)
    created_at      = Column(DateTime(timezone=True), default=_now_jst)
    updated_at      = Column(DateTime(timezone=True), default=_now_jst,
                             onupdate=_now_jst)
    comparables     = relationship(
        "ComparableTicker",
        back_populates="case",
        cascade="all, delete-orphan",
    )


class ComparableTicker(Base):
    __tablename__ = "comparable_tickers"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    case_id       = Column(Integer, ForeignKey("valuation_cases.id",
                           ondelete="CASCADE"), nullable=False)
    ticker        = Column(String(20), nullable=False)
    company_label = Column(String(200), default="")
    volatility    = Column(Float, default=0.0)
    vol_period    = Column(String(10), default="1y")
    fetch_ok      = Column(Boolean, default=True)
    error_msg     = Column(Text, default="")
    case          = relationship("ValuationCase", back_populates="comparables")
