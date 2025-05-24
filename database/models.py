from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())
    appointments = relationship("Appointment", back_populates="user")

class ServiceProvider(Base):
    __tablename__ = 'service_providers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    service_type = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20))
    appointments = relationship("Appointment", back_populates="provider")

class Appointment(Base):
    __tablename__ = 'appointments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    provider_id = Column(Integer, ForeignKey('service_providers.id'))
    datetime = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    status = Column(String(20), default='scheduled')  # scheduled, completed, cancelled
    notes = Column(String(500))
    created_at = Column(DateTime, server_default=func.now())
    
    user = relationship("User", back_populates="appointments")
    provider = relationship("ServiceProvider", back_populates="appointments")

class TimeSlot(Base):
    __tablename__ = 'time_slots'
    
    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey('service_providers.id'))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_available = Column(Boolean, default=True)
    
    provider = relationship("ServiceProvider") 