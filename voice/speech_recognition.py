import speech_recognition as sr
import pyttsx3
from typing import Optional
import time
from difflib import get_close_matches

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
        # Adjust recognition parameters for better sensitivity
        self.recognizer.energy_threshold = 100  # Even lower threshold for easier voice detection
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.3  # Shorter pause threshold
        self.recognizer.phrase_threshold = 0.1  # More sensitive to phrases
        self.recognizer.non_speaking_duration = 0.2  # Shorter duration for non-speaking detection

    def process_audio_file(self, audio_file_path: str) -> Optional[str]:
        """
        Process audio file from Gradio and convert it to text
        """
        try:
            with sr.AudioFile(audio_file_path) as source:
                print("Processing audio file...")
                audio = self.recognizer.record(source)
                
                try:
                    # Try Google's service with explicit language
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
                        return best_result
                    else:
                        print("❌ No clear speech detected in the audio file.")
                        return None
                        
                except sr.UnknownValueError:
                    print("❌ Could not understand audio clearly. Please speak louder and more clearly.")
                    return None
                except sr.RequestError as e:
                    print(f"❌ Service error: {e}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error processing audio file: {e}")
            return None

    def process_voice_command(self, audio_file_path: str = None) -> dict:
        """
        Process voice command and extract appointment details
        """
        if audio_file_path is None:
            return {
                'success': False,
                'message': "No audio file provided"
            }
            
        text = self.process_audio_file(audio_file_path)
        
        if text is None:
            return {
                'success': False,
                'message': "Could not understand audio. Please speak clearly and try again."
            }
            
        # Process the recognized text
        text = text.lower()
        details = {
            'provider': None,
            'date': None,
            'time': None
        }
        
        # Extract provider with more flexible matching
        provider_keywords = {
            'smith': 'Dr. Smith',
            'dr smith': 'Dr. Smith',
            'doctor smith': 'Dr. Smith',
            'johnson': 'Dr. Johnson',
            'dr johnson': 'Dr. Johnson',
            'doctor johnson': 'Dr. Johnson',
            'williams': 'Ms. Williams',
            'ms williams': 'Ms. Williams',
            'miss williams': 'Ms. Williams'
        }
        
        # Try exact matches first
        for keyword, provider in provider_keywords.items():
            if keyword in text:
                details['provider'] = provider
                break
                
        # If no exact match, try fuzzy matching
        if not details['provider']:
            words = text.split()
            matches = fuzzy_match(text, provider_keywords)
            if matches:
                details['provider'] = matches
            
        # Extract date with more flexible matching
        date_keywords = {
            'tomorrow': 'tomorrow',
            'today': 'today',
            'next monday': 'next Monday',
            'next tuesday': 'next Tuesday',
            'next wednesday': 'next Wednesday',
            'next thursday': 'next Thursday',
            'next friday': 'next Friday',
            'monday': 'next Monday',
            'tuesday': 'next Tuesday',
            'wednesday': 'next Wednesday',
            'thursday': 'next Thursday',
            'friday': 'next Friday'
        }
        
        # Try exact matches first
        for keyword, date in date_keywords.items():
            if keyword in text:
                details['date'] = date
                break
                
        # If no exact match, try fuzzy matching
        if not details['date']:
            words = text.split()
            matches = fuzzy_match(text, date_keywords)
            if matches:
                details['date'] = matches
            
        # Extract time with more flexible matching
        time_keywords = {
            'morning': 'morning (9 AM - 12 PM)',
            'afternoon': 'afternoon (1 PM - 5 PM)',
            'evening': 'evening (5 PM - 8 PM)',
            'am': 'morning (9 AM - 12 PM)',
            'pm': 'afternoon (1 PM - 5 PM)'
        }
        
        # Try exact matches first
        for keyword, time in time_keywords.items():
            if keyword in text:
                details['time'] = time
                break
                
        # If no exact match, try fuzzy matching
        if not details['time']:
            words = text.split()
            matches = fuzzy_match(text, time_keywords)
            if matches:
                details['time'] = matches
            
        # Try to find specific time
        import re
        time_match = re.search(r'(\d{1,2})(?:\s*:\s*\d{2})?\s*(am|pm)', text)
        if time_match:
            time_str = time_match.group()
            print(f"Extracted time from regex: {time_str}")
            details['time'] = time_str
                
        # Check if we got any details
        if not any(details.values()):
            return {
                'success': False,
                'message': "Could not understand appointment details. Please include provider name, date, and time."
            }
            
        return {
            'success': True,
            'message': "Successfully processed your request",
            'details': details
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
