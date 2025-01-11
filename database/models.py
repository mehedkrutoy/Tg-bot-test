from sqlalchemy import Column, Integer, String, Float, ForeignKey, create_engine, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    username = Column(String)
    balance = Column(Float, default=0.0)
    referrer_id = Column(Integer, nullable=True)
    total_referrals = Column(Integer, default=0)

class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    amount = Column(Float)
    status = Column(String)

class PromoCode(Base):
    __tablename__ = 'promo_codes'
    
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    amount = Column(Float)
    uses_left = Column(Integer)
    is_percentage = Column(Integer, default=0)

class UsedPromoCode(Base):
    __tablename__ = 'used_promocodes'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    promo_code = Column(String, nullable=False)
    used_at = Column(DateTime, default=datetime.utcnow)