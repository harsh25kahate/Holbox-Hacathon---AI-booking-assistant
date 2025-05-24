import numpy as np
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class SchedulingAgent:
    def __init__(self):
        self.scaler = StandardScaler()
        
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