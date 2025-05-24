from gtts import gTTS
import os
import tempfile
import pygame
from datetime import datetime

class VoiceResponse:
    def __init__(self):
        pygame.mixer.init()
        
    def speak(self, text: str) -> str:
        """
        Convert text to speech and play it
        """
        try:
            # Create a temporary file for the audio
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                # Generate speech
                tts = gTTS(text=text, lang='en')
                tts.save(fp.name)
                
                # Play the audio
                pygame.mixer.music.load(fp.name)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                    
                # Clean up
                pygame.mixer.music.unload()
                os.unlink(fp.name)
                
            return text
        except Exception as e:
            print(f"Error in text-to-speech: {e}")
            return f"Error: {str(e)}"
    
    def format_time(self, dt: datetime) -> str:
        """
        Format datetime into natural speech
        """
        return dt.strftime("%I:%M %p on %A, %B %d")
    
    def generate_booking_response(self, slot_info: dict) -> str:
        """
        Generate natural response for booking confirmation
        """
        if slot_info.get('success'):
            return f"Great! I've booked your appointment for {self.format_time(slot_info['details']['datetime'])} with {slot_info['details']['provider']}. I'll send you an email confirmation shortly."
        return "I apologize, but I couldn't book that appointment. " + slot_info.get('message', '')
    
    def generate_availability_response(self, availability_info: dict) -> str:
        """
        Generate natural response for slot availability
        """
        if availability_info.get('available'):
            slot = availability_info['slot']
            return f"Yes, I found an available slot with {slot['provider_name']} at {self.format_time(slot['start_time'])}. Would you like me to book this for you?"
        
        message = "I'm sorry, but that slot isn't available. "
        if availability_info.get('alternative_slots'):
            message += "Here are some alternative times: "
            for i, slot in enumerate(availability_info['alternative_slots'][:3], 1):
                message += f"{i}. {self.format_time(slot['start_time'])}, "
            message += "Would you like me to book any of these slots?"
        else:
            message += "There are no alternative slots available for this day. Would you like to try a different date?"
        
        return message 