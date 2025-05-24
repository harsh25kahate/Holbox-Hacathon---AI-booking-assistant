import numpy as np
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database.database import SessionLocal
from database.models import User, ServiceProvider, Appointment, TimeSlot

class SchedulingAgent:
    def __init__(self):
        self.scaler = StandardScaler()
        self.learning_data = {}  # Store learning patterns
        
    def get_available_slots(self, provider_schedule: List[Dict], duration_minutes: int = 30) -> List[Dict]:
        """
        Get available time slots for a provider
        """
        available_slots = []
        current_time = datetime.now()
        
        for slot in provider_schedule:
            slot_start = slot['start_time']
            slot_end = slot['end_time']
            
            if slot['is_available'] and slot_start > current_time:
                # Calculate number of possible appointments in this slot
                slot_duration = (slot_end - slot_start).total_seconds() / 60
                num_possible_appointments = int(slot_duration / duration_minutes)
                
                # Create individual appointment slots
                for i in range(num_possible_appointments):
                    appointment_start = slot_start + timedelta(minutes=i * duration_minutes)
                    appointment_end = appointment_start + timedelta(minutes=duration_minutes)
                    
                    if appointment_end <= slot_end:
                        available_slots.append({
                            'start_time': appointment_start,
                            'end_time': appointment_end,
                            'duration': duration_minutes
                        })
        
        return available_slots
    
    def rank_slots(self, available_slots: List[Dict], user_preferences: Dict) -> List[Dict]:
        """
        Rank available slots based on user preferences
        """
        if not available_slots:
            return []
            
        # Simple scoring based on time preferences
        preferred_time = user_preferences.get('preferred_time')
        if preferred_time:
            for slot in available_slots:
                # Calculate how close the slot is to preferred time
                time_diff = abs((slot['start_time'].hour * 60 + slot['start_time'].minute) - 
                              (preferred_time.hour * 60 + preferred_time.minute))
                slot['score'] = 1 / (1 + time_diff)  # Higher score for closer times
        
        # Sort by score
        ranked_slots = sorted(available_slots, key=lambda x: x.get('score', 0), reverse=True)
        return ranked_slots
    
    def suggest_alternative_slots(self, unavailable_slot: Dict, available_slots: List[Dict]) -> List[Dict]:
        """
        Suggest alternative slots when requested slot is unavailable
        """
        requested_time = unavailable_slot['start_time']
        
        # Score slots based on proximity to requested time
        for slot in available_slots:
            time_diff = abs((slot['start_time'] - requested_time).total_seconds() / 3600)  # difference in hours
            slot['alternative_score'] = 1 / (1 + time_diff)
        
        # Return top 3 alternatives
        alternatives = sorted(available_slots, key=lambda x: x['alternative_score'], reverse=True)[:3]
        return alternatives
    
    def handle_conflicts(self, appointments: List[Dict]) -> List[Dict]:
        """
        Handle scheduling conflicts
        """
        # Sort appointments by priority/time
        sorted_appointments = sorted(appointments, key=lambda x: x['priority'], reverse=True)
        
        # Check for overlaps and resolve conflicts
        resolved_appointments = []
        for appt in sorted_appointments:
            conflict = False
            for resolved in resolved_appointments:
                if self._check_overlap(appt, resolved):
                    conflict = True
                    break
            
            if not conflict:
                resolved_appointments.append(appt)
        
        return resolved_appointments
    
    def _check_overlap(self, appt1: Dict, appt2: Dict) -> bool:
        """
        Check if two appointments overlap
        """
        return (appt1['start_time'] < appt2['end_time'] and 
                appt2['start_time'] < appt1['end_time']) 
    
    def find_optimal_slot(self, provider_id: int, preferred_date: datetime.date, 
                         preferred_time: str) -> Optional[Dict]:
        """
        Find the optimal available slot based on preferences and patterns
        """
        try:
            with SessionLocal() as db:
                # Get all available slots for the day
                slots = db.query(TimeSlot).filter(
                    TimeSlot.provider_id == provider_id,
                    TimeSlot.start_time.date() == preferred_date,
                    TimeSlot.is_available == True
                ).all()
                
                if not slots:
                    return None
                
                # Convert preferred time to datetime objects for comparison
                time_ranges = {
                    'morning': (datetime.time(9, 0), datetime.time(12, 0)),
                    'afternoon': (datetime.time(13, 0), datetime.time(17, 0)),
                    'evening': (datetime.time(17, 0), datetime.time(20, 0))
                }
                
                # Parse specific time if given (e.g., "2 PM" or "14:00")
                specific_time = None
                try:
                    if 'am' in preferred_time.lower() or 'pm' in preferred_time.lower():
                        time_str = preferred_time.replace('(', '').replace(')', '')
                        specific_time = datetime.strptime(time_str, '%I %p').time()
                    else:
                        # Try 24-hour format
                        specific_time = datetime.strptime(preferred_time, '%H:%M').time()
                except:
                    # If parsing fails, treat as a time range
                    pass
                
                # Score and rank available slots
                scored_slots = []
                for slot in slots:
                    score = 0
                    slot_time = slot.start_time.time()
                    
                    # Match specific time if provided
                    if specific_time:
                        time_diff = abs(
                            datetime.combine(datetime.date.today(), slot_time) - 
                            datetime.combine(datetime.date.today(), specific_time)
                        ).seconds / 3600  # Convert to hours
                        score = 1 / (1 + time_diff)  # Higher score for closer times
                    else:
                        # Match time range (morning/afternoon/evening)
                        for range_name, (start, end) in time_ranges.items():
                            if range_name.lower() in preferred_time.lower():
                                if start <= slot_time <= end:
                                    score = 1
                                break
                        
                        # If no specific range mentioned, give all slots a base score
                        if score == 0:
                            score = 0.5
                    
                    scored_slots.append((slot, score))
                
                # Sort by score and get the best match
                scored_slots.sort(key=lambda x: x[1], reverse=True)
                if scored_slots:
                    best_slot = scored_slots[0][0]
                    return {
                        'slot_id': best_slot.id,
                        'provider_id': provider_id,
                        'start_time': best_slot.start_time,
                        'end_time': best_slot.end_time,
                        'score': scored_slots[0][1]
                    }
                
                return None
                
        except Exception as e:
            print(f"Error finding optimal slot: {e}")
            return None
            
    def book_appointment(self, user_name: str, user_email: str, 
                        provider_id: int, slot_id: int) -> Dict:
        """
        Book the appointment and handle the transaction
        """
        try:
            with SessionLocal() as db:
                # Create or get user
                user = db.query(User).filter(User.email == user_email).first()
                if not user:
                    user = User(name=user_name, email=user_email)
                    db.add(user)
                    db.commit()
                
                # Get and verify slot
                slot = db.query(TimeSlot).filter(
                    TimeSlot.id == slot_id,
                    TimeSlot.is_available == True
                ).first()
                
                if not slot:
                    return {
                        'success': False,
                        'message': "Selected slot is no longer available"
                    }
                
                # Create appointment
                appointment = Appointment(
                    user_id=user.id,
                    provider_id=provider_id,
                    datetime=slot.start_time,
                    duration_minutes=30
                )
                db.add(appointment)
                
                # Mark slot as booked
                slot.is_available = False
                db.commit()
                
                return {
                    'success': True,
                    'message': "Appointment booked successfully!",
                    'details': {
                        'date': slot.start_time.strftime('%Y-%m-%d'),
                        'time': slot.start_time.strftime('%I:%M %p'),
                        'provider': slot.provider.name
                    }
                }
                
        except Exception as e:
            print(f"Error booking appointment: {e}")
            return {
                'success': False,
                'message': f"Error booking appointment: {str(e)}"
            }
            
    def get_provider_id(self, provider_name: str) -> Optional[int]:
        """
        Get provider ID from name
        """
        try:
            with SessionLocal() as db:
                provider = db.query(ServiceProvider).filter(
                    ServiceProvider.name.ilike(f"%{provider_name}%")
                ).first()
                return provider.id if provider else None
        except Exception as e:
            print(f"Error getting provider ID: {e}")
            return None

    def find_alternative_slots(self, provider_id: int, preferred_date: datetime.date, 
                           preferred_time: datetime.time, window_days: int = 7) -> List[Dict]:
        """
        Find alternative slots within a window of days
        """
        alternative_slots = []
        
        try:
            with SessionLocal() as db:
                # Look for slots in the next few days
                start_date = preferred_date
                end_date = start_date + timedelta(days=window_days)
                
                slots = db.query(TimeSlot).filter(
                    TimeSlot.provider_id == provider_id,
                    TimeSlot.start_time >= datetime.combine(start_date, datetime.min.time()),
                    TimeSlot.start_time <= datetime.combine(end_date, datetime.max.time()),
                    TimeSlot.is_available == True
                ).order_by(TimeSlot.start_time).all()
                
                for slot in slots:
                    alternative_slots.append({
                        'slot_id': slot.id,
                        'provider_id': provider_id,
                        'start_time': slot.start_time,
                        'end_time': slot.end_time
                    })
                    
                    # Limit to 5 alternative slots
                    if len(alternative_slots) >= 5:
                        break
                        
        except Exception as e:
            print(f"Error finding alternative slots: {e}")
            
        return alternative_slots

    def suggest_slots(self, provider_id: int, preferred_date: datetime.date, 
                   preferred_time: datetime.time) -> Dict:
        """
        Suggest available slots for a provider
        """
        try:
            # Try to find optimal slot for preferred date/time
            optimal_slot = self.find_optimal_slot(provider_id, preferred_date, preferred_time)
            
            if optimal_slot and optimal_slot['score'] > 0.8:
                return {
                    'available': True,
                    'slot': optimal_slot,
                    'message': 'Found an available slot!'
                }
            
            # If no optimal slot found or score is low, find alternatives
            alternative_slots = self.find_alternative_slots(
                provider_id, 
                preferred_date,
                preferred_time
            )
            
            if alternative_slots:
                return {
                    'available': False,
                    'message': f"Sorry, no available slots found for your preferred time.",
                    'alternative_slots': alternative_slots
                }
            
            return {
                'available': False,
                'message': f"Sorry, no available slots found. Please try a different date or provider.",
                'alternative_slots': []
            }
            
        except Exception as e:
            print(f"Error suggesting slots: {e}")
            return {
                'available': False,
                'message': "An error occurred while searching for slots.",
                'alternative_slots': []
            }

    def format_slot_suggestion(self, slot: Dict) -> str:
        """
        Format a slot suggestion for display
        """
        try:
            with SessionLocal() as db:
                provider = db.query(ServiceProvider).filter_by(id=slot['provider_id']).first()
                provider_name = provider.name if provider else "Unknown Provider"
                
                start_time = slot['start_time']
                return f"{provider_name} on {start_time.strftime('%A, %B %d')} at {start_time.strftime('%I:%M %p')}"
        except Exception as e:
            print(f"Error formatting slot suggestion: {e}")
            return "Error formatting slot details" 