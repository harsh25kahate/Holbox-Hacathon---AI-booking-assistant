from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    phone = Column(String)
    
    appointments = relationship("Appointment", back_populates="user")

class ServiceProvider(Base):
    __tablename__ = "service_providers"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    service_type = Column(String)
    email = Column(String)
    phone = Column(String)
    
    appointments = relationship("Appointment", back_populates="provider")
    time_slots = relationship("TimeSlot", back_populates="provider")

class TimeSlot(Base):
    __tablename__ = "time_slots"
    
    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey('service_providers.id'))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    is_available = Column(Boolean, default=True)
    
    provider = relationship("ServiceProvider", back_populates="time_slots")

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    provider_id = Column(Integer, ForeignKey('service_providers.id'))
    datetime = Column(DateTime)
    duration_minutes = Column(Integer)
    status = Column(String, default='booked')  # 'booked' or 'cancelled'
    
    user = relationship("User", back_populates="appointments")
    provider = relationship("ServiceProvider", back_populates="appointments") 