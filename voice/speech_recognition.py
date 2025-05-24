from typing import List, Dict
import speech_recognition as sr
import pyttsx3
from typing import Optional
import time
from difflib import get_close_matches
from datetime import datetime, timedelta
from ai_agent.scheduler import SchedulingAgent
from voice.voice_response import VoiceResponse

def fuzzy_match(text, keywords):
    for keyword in keywords:
        if keyword in text:
            return keywords[keyword]
    # fallback: try matching phrases inside the text using get_close_matches on words or n-grams
    words = text.split()
    for word in words:
        matches = get_close_matches(word, keywords.keys(), n=1, cutoff=0.6)
        if matches:
            return keywords[matches[0]]
    return None

class VoiceHandler:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.scheduler = SchedulingAgent()
        self.voice_response = VoiceResponse()
        # Adjust recognition parameters for better sensitivity
        self.recognizer.energy_threshold = 100  # Even lower threshold for easier voice detection
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.3  # Shorter pause threshold
        self.recognizer.phrase_threshold = 0.1  # More sensitive to phrases
        self.recognizer.non_speaking_duration = 0.2  # Shorter duration for non-speaking detection

    def process_audio_file(self, audio_file_path: str, max_attempts: int = 3) -> str:
        """
        Process audio file and convert to text
        """
        for attempt in range(max_attempts):
            try:
                with sr.AudioFile(audio_file_path) as source:
                    audio = self.recognizer.record(source)
                    text = self.recognizer.recognize_google(audio)
                    return text.lower()
            except sr.UnknownValueError:
                if attempt < max_attempts - 1:
                    print("Trying again...")
                    continue
                return None
            except Exception as e:
                print(f"Error processing audio: {e}")
                return None

    def process_voice_command(self, audio_file_path: str = None) -> dict:
        """
        Process voice command and extract appointment details
        """
        if audio_file_path is None:
            response = "No audio detected. Please try recording again."
            self.voice_response.speak(response)
            return {
                'success': False,
                'message': response
            }
            
        if not isinstance(audio_file_path, str) or not audio_file_path.strip():
            response = "Invalid audio input. Please try recording again."
            self.voice_response.speak(response)
            return {
                'success': False,
                'message': response
            }
            
        text = self.process_audio_file(audio_file_path)
        
        if text is None:
            response = "Could not understand audio. Please speak clearly and try again."
            self.voice_response.speak(response)
            return {
                'success': False,
                'message': response
            }
            
        # Extract appointment details
        details = self.extract_appointment_details(text)
        if not details['success']:
            self.voice_response.speak(details['message'])
            return details
            
        # Check availability
        provider_id = self.scheduler.get_provider_id(details['provider'])
        if not provider_id:
            response = f"Sorry, I couldn't find {details['provider']} in our system."
            self.voice_response.speak(response)
            return {
                'success': False,
                'message': response
            }
            
        # Check slot availability
        availability = self.scheduler.suggest_slots(
            provider_id,
            details['date'],
            details['time']
        )
        
        # Generate and speak the appropriate response
        response = self.voice_response.generate_availability_response(availability)
        self.voice_response.speak(response)
        
        if availability.get('available'):
            # If slot is available, book it
            booking = self.scheduler.book_appointment(
                "User",  # Replace with actual user name
                "user@example.com",  # Replace with actual email
                provider_id,
                availability['slot']['slot_id']
            )
            
            # Generate and speak booking confirmation
            confirmation = self.voice_response.generate_booking_response(booking)
            self.voice_response.speak(confirmation)
            return booking
            
        return {
            'success': False,
            'message': response,
            'alternatives': availability.get('alternative_slots', [])
        }

    def extract_appointment_details(self, text: str) -> Dict:
        """
        Extract appointment details from text
        """
        try:
            # Common date keywords
            date_keywords = {
                'today': datetime.now().date(),
                'tomorrow': datetime.now().date() + timedelta(days=1),
                'day after tomorrow': datetime.now().date() + timedelta(days=2)
            }
            
            # Time of day mappings
            time_mappings = {
                'morning': '9 AM',
                'afternoon': '2 PM',
                'evening': '5 PM'
            }
            
            # Extract provider name
            provider = None
            if 'with' in text:
                provider = text.split('with')[1].split()[0]
                if 'dr' in provider or 'dr.' in provider:
                    provider = text.split('with')[1].split('dr')[1].strip()
                    provider = f"Dr. {provider}"
            
            if not provider:
                return {
                    'success': False,
                    'message': "Please specify a doctor's name. For example, 'Book an appointment with Dr. Smith'"
                }
            
            # Extract date
            date = None
            for keyword, value in date_keywords.items():
                if keyword in text:
                    date = value
                    break
                    
            if not date:
                # Try to find a specific date mention
                # This is a simplified version - you might want to add more sophisticated date parsing
                return {
                    'success': False,
                    'message': "Please specify a date. You can say 'today', 'tomorrow', or 'day after tomorrow'"
                }
            
            # Extract time
            time = None
            for period, default_time in time_mappings.items():
                if period in text:
                    time = default_time
                    break
                    
            if not time:
                # Try to find specific time mention
                # This is a simplified version - you might want to add more sophisticated time parsing
                return {
                    'success': False,
                    'message': "Please specify a time. You can say 'morning', 'afternoon', or 'evening'"
                }
            
            return {
                'success': True,
                'provider': provider,
                'date': date,
                'time': time
            }
            
        except Exception as e:
            print(f"Error extracting appointment details: {e}")
            return {
                'success': False,
                'message': "I couldn't understand the appointment details. Please try again with a clear provider name, date, and time."
            }

    def speak(self, text: str):
        """
        Convert text to speech with improved settings
        """
        try:
            # Configure speech properties
            self.engine.setProperty('rate', 150)  # Slower speaking rate
            self.engine.setProperty('volume', 0.9)  # Slightly lower volume
            
            print(f"🔊 System: {text}")
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"❌ Error in text-to-speech: {e}")
        
    def listen(self) -> Optional[str]:
        """
        Listen to user's voice input and convert it to text with improved reliability
        """
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                with sr.Microphone() as source:
                    print(f"\nAttempt {attempt + 1} of {max_attempts}")
                    print("Adjusting for background noise... Please wait")
                    # Longer adjustment for better noise calibration
                    self.recognizer.adjust_for_ambient_noise(source, duration=2)
                    
                    print("\n🎤 Listening... Speak now!")
                    try:
                        # Increased timeout and phrase time limit
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                        print("Processing your speech...")
                        
                        # Try multiple recognition services
                        try:
                            # Try Google's service first with explicit language and show_all
                            text = self.recognizer.recognize_google(
                                audio,
                                language='en-US',
                                show_all=True
                            )
                            
                            if isinstance(text, dict) and 'alternative' in text:
                                # Get the most confident result
                                best_result = text['alternative'][0]['transcript']
                                confidence = text['alternative'][0].get('confidence', 0)
                                
                                print(f"✅ Recognized: {best_result} (Confidence: {confidence:.2f})")
                                
                                # If confidence is too low, try again
                                if confidence < 0.6 and attempt < max_attempts - 1:
                                    print("⚠️ Low confidence in recognition. Trying again...")
                                    continue
                                    
                                return best_result
                            else:
                                print("❌ No clear speech detected. Please try again.")
                                if attempt < max_attempts - 1:
                                    continue
                                return "Could not understand audio. Please speak clearly and try again."
                                
                        except sr.UnknownValueError:
                            print("❌ Could not understand audio clearly. Please speak louder and more clearly.")
                            if attempt < max_attempts - 1:
                                print("Trying again...")
                                continue
                            return "Could not understand audio. Please speak clearly and try again."
                        except sr.RequestError as e:
                            print(f"❌ Service error: {e}")
                            return "Could not access speech recognition service. Please check your internet connection."
                            
                    except sr.WaitTimeoutError:
                        if attempt < max_attempts - 1:
                            print("⚠️ No speech detected. Please try again...")
                            continue
                        return "No speech detected. Please try again."
                        
            except Exception as e:
                print(f"❌ Error in speech recognition: {e}")
                if attempt < max_attempts - 1:
                    print("Retrying...")
                    continue
                return f"Error occurred: {str(e)}. Please try again."
        
        return "Failed to recognize speech after multiple attempts. Please try again."

    def book_from_suggestions(self, text: str, suggested_slots: List[Dict], scheduler: SchedulingAgent) -> str:
        """
        Book an appointment from suggested alternative slots
        """
        try:
            # Check if user specified a slot number
            import re
            slot_number_match = re.search(r'(?:slot|number|option)?\s*(\d+)', text.lower())
            
            if slot_number_match:
                selected_number = int(slot_number_match.group(1))
                
                # Check if the number is valid
                if 1 <= selected_number <= len(suggested_slots):
                    selected_slot = suggested_slots[selected_number - 1]
                    
                    # Book the appointment
                    booking_result = scheduler.book_appointment(
                        provider_id=selected_slot['provider_id'],
                        slot_id=selected_slot['slot_id'],
                        user_name="User",  # TODO: Get actual user name
                        user_email="user@example.com"  # TODO: Get actual user email
                    )
                    
                    if booking_result['success']:
                        return f"Great! Your appointment is confirmed for {scheduler.format_slot_suggestion(selected_slot)}."
                    else:
                        return f"Sorry, couldn't book the appointment: {booking_result['message']}"
                else:
                    return f"Please select a valid slot number between 1 and {len(suggested_slots)}."
            
            return "Please specify which slot you'd like to book by saying the slot number (e.g., 'book slot 1' or 'number 2')."
            
        except Exception as e:
            print(f"Error booking from suggestions: {e}")
            return "Sorry, there was an error booking your appointment. Please try again."

    def process_booking_request(self, text: str, scheduler: SchedulingAgent, suggested_slots: List[Dict] = None) -> str:
        """
        Process the booking request and handle scheduling
        """
        try:
            # If we have suggested slots, try to book from them
            if suggested_slots:
                return self.book_from_suggestions(text, suggested_slots, scheduler)
            
            # Extract date and time from text
            extracted_date = self.extract_date(text)
            extracted_time = self.extract_time(text)
            provider_name = self.extract_provider_name(text)
            
            if not all([extracted_date, extracted_time, provider_name]):
                return "I couldn't understand all the details. Please specify the doctor's name, date, and time for the appointment."
            
            # Get provider ID
            provider_id = scheduler.get_provider_id(provider_name)
            if not provider_id:
                return f"Sorry, I couldn't find {provider_name} in our system. Please check the name and try again."
            
            # Check availability and get suggestions
            result = scheduler.suggest_slots(provider_id, extracted_date, extracted_time)
            
            if result['available']:
                # Book the slot
                slot = result['slot']
                booking_result = scheduler.book_appointment(
                    provider_id=provider_id,
                    slot_id=slot['slot_id'],
                    user_name="User",  # TODO: Get actual user name
                    user_email="user@example.com"  # TODO: Get actual user email
                )
                
                if booking_result['success']:
                    return f"Great! Your appointment is confirmed for {scheduler.format_slot_suggestion(slot)}."
                else:
                    return booking_result['message']
            else:
                # Store suggested slots for future reference
                self.last_suggested_slots = result['alternative_slots']
                
                # Suggest alternative slots
                response = [result['message'], "\n\nHere are some alternative available slots:"]
                
                for i, slot in enumerate(result['alternative_slots'], 1):
                    response.append(f"\n{i}. {scheduler.format_slot_suggestion(slot)}")
                
                response.append("\n\nTo book a slot, just say its number (e.g., 'book slot 1' or 'number 2').")
                
                return "".join(response)
                
        except Exception as e:
            print(f"Error processing booking request: {e}")
            return "Sorry, there was an error processing your request. Please try again."
