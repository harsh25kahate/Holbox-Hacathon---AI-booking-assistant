import gradio as gr
import datetime
from voice.speech_recognition import VoiceHandler
from ai_agent.scheduler import SchedulingAgent
from notifications.notifier import NotificationSystem
from database.database import SessionLocal
from database.models import User, ServiceProvider, Appointment, TimeSlot

class AppointmentUI:
    def __init__(self):
        self.voice_handler = VoiceHandler()
        self.scheduler = SchedulingAgent()
        self.notifier = NotificationSystem()
        
    def process_voice_booking(self, audio):
        """
        Process voice input for booking
        """
        if audio is None:
            return "Please record your voice first."
            
        try:
            result = self.voice_handler.process_voice_command(audio)
            
            if not result['success']:
                return result['message']
                
            details = result['details']
            
            # Get provider ID
            provider_id = self.scheduler.get_provider_id(details['provider'])
            if not provider_id:
                return f"Sorry, I couldn't find {details['provider']} in our system."
            
            # Parse date
            try:
                if details['date'].lower() == 'tomorrow':
                    preferred_date = datetime.date.today() + datetime.timedelta(days=1)
                elif details['date'].lower() == 'today':
                    preferred_date = datetime.date.today()
                else:
                    # Handle "next Monday", "next Tuesday", etc.
                    day_name = details['date'].lower().replace('next ', '')
                    days = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 
                           'thursday': 3, 'friday': 4}
                    today = datetime.date.today()
                    days_ahead = days[day_name] - today.weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    preferred_date = today + datetime.timedelta(days=days_ahead)
            except:
                return "Sorry, I couldn't understand the date. Please try again."
            
            # Find optimal slot
            optimal_slot = self.scheduler.find_optimal_slot(
                provider_id, 
                preferred_date,
                details['time']
            )
            
            if not optimal_slot:
                return f"Sorry, no available slots found for {details['provider']} on {preferred_date}. Please try a different date or time."
            
            # Book the appointment
            booking_result = self.scheduler.book_appointment(
                "Voice Booking User",  # Temporary name
                "voice@example.com",   # Temporary email
                provider_id,
                optimal_slot['slot_id']
            )
            
            if booking_result['success']:
                # Send confirmation notification
                self.notifier.send_confirmation({
                    'email': "voice@example.com",  # Temporary email
                    'provider': details['provider'],
                    'date': booking_result['details']['date'],
                    'time': booking_result['details']['time']
                })
                
                return f"""Great! I've booked your appointment:
Provider: {details['provider']}
Date: {booking_result['details']['date']}
Time: {booking_result['details']['time']}

Your appointment is confirmed! You'll receive a confirmation email shortly.

Would you like to provide your email for appointment reminders? Just say 'My email is example@email.com'"""
            else:
                return f"Sorry, I couldn't book the appointment: {booking_result['message']}"
                
        except Exception as e:
            return f"Error processing voice: {str(e)}. Please try again."
    
    def get_available_slots(self, provider_id, date_str):
        """
        Get available slots for a provider on a specific date
        """
        if not provider_id:
            return ["Please select a provider first"]
            
        if not date_str:
            return ["Please enter a date"]
            
        try:
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            with SessionLocal() as db:
                slots = db.query(TimeSlot).filter(
                    TimeSlot.provider_id == provider_id,
                    TimeSlot.start_time.date() == date,
                    TimeSlot.is_available == True
                ).all()
                
                if not slots:
                    return ["No available slots for this date"]
                    
                return [
                    f"{slot.start_time.strftime('%I:%M %p')} - {slot.end_time.strftime('%I:%M %p')}"
                    for slot in slots
                ]
        except ValueError:
            return ["Please enter a valid date in YYYY-MM-DD format"]
        except Exception as e:
            print(f"Error getting slots: {e}")
            return ["Error fetching available slots. Please try again."]
    
    def create_interface(self):
        """
        Create the Gradio interface
        """
        with gr.Blocks(title="AI Appointment Booking System") as interface:
            gr.Markdown(
                """
                # AI Appointment Booking System
                Welcome to our intelligent appointment booking system. You can book appointments using voice commands or manual entry.
                """
            )
            
            with gr.Tab("Voice Booking"):
                gr.Markdown(
                    """
                    ### Voice Booking Instructions:
                    1. Click the microphone button and allow microphone access
                    2. Speak your request clearly, for example:
                       - "Book an appointment with Dr. Smith tomorrow morning"
                       - "I need to see Dr. Johnson next Monday at 2 PM"
                       - "Schedule a visit with Ms. Williams on Friday afternoon"
                    3. Wait for the system to process your request
                    4. If correct, go to Manual Booking tab to complete your booking
                    """
                )
                
                with gr.Row():
                    with gr.Column():
                        audio_input = gr.Audio(
                            sources=["microphone"],
                            type="filepath",
                            label="Click to start recording",
                            streaming=False,
                            elem_id="voice_input",
                            format="wav"  # Specify WAV format for better compatibility
                        )
                    
                voice_output = gr.Textbox(
                    label="Voice Recognition Result",
                    lines=5,
                    value="Waiting for voice input..."  # Default message
                )
                
                # Remove the separate process button and directly process on audio change
                audio_input.change(
                    fn=self.process_voice_booking,
                    inputs=[audio_input],
                    outputs=voice_output
                )
                
                # Clear message when starting new recording
                audio_input.start_recording(
                    fn=lambda: "Recording... Speak now",
                    outputs=voice_output
                )
            
            with gr.Tab("Manual Booking"):
                with gr.Row():
                    name_input = gr.Textbox(
                        label="Your Name",
                        value=""
                    )
                    email_input = gr.Textbox(
                        label="Your Email",
                        value=""
                    )
                
                with gr.Row():
                    provider_dropdown = gr.Dropdown(
                        choices=self._get_providers(),
                        label="Select Provider",
                        value=None
                    )
                    date_input = gr.Textbox(
                        label="Appointment Date (YYYY-MM-DD)",
                        value=""
                    )
                
                available_slots = gr.Dropdown(
                    choices=[],
                    label="Available Time Slots",
                    interactive=True,
                    value=None
                )
                
                book_button = gr.Button("Book Appointment")
                
                booking_status = gr.Textbox(
                    label="Booking Status",
                    lines=3,
                    value=""
                )
                
                # Update available slots when date or provider changes
                provider_dropdown.change(
                    fn=self.get_available_slots,
                    inputs=[provider_dropdown, date_input],
                    outputs=available_slots
                )
                
                date_input.change(
                    fn=self.get_available_slots,
                    inputs=[provider_dropdown, date_input],
                    outputs=available_slots
                )
                
                # Book appointment
                book_button.click(
                    fn=self.book_appointment,
                    inputs=[name_input, email_input, provider_dropdown, available_slots],
                    outputs=booking_status
                )
        
        return interface
    
    def book_appointment(self, user_name, user_email, provider_id, slot_id):
        """
        Book an appointment
        """
        if not all([user_name, user_email, provider_id, slot_id]):
            return "Please fill in all required fields"
            
        try:
            with SessionLocal() as db:
                # Create or get user
                user = db.query(User).filter(User.email == user_email).first()
                if not user:
                    user = User(name=user_name, email=user_email)
                    db.add(user)
                    db.commit()
                
                # Get slot
                slot = db.query(TimeSlot).filter(TimeSlot.id == slot_id).first()
                if not slot or not slot.is_available:
                    return "Selected slot is no longer available"
                
                # Create appointment
                appointment = Appointment(
                    user_id=user.id,
                    provider_id=provider_id,
                    datetime=slot.start_time,
                    duration_minutes=30
                )
                db.add(appointment)
                
                # Mark slot as unavailable
                slot.is_available = False
                db.commit()
                
                return f"""Appointment booked successfully!
Date: {slot.start_time.strftime('%Y-%m-%d')}
Time: {slot.start_time.strftime('%I:%M %p')}
Provider: {slot.provider.name}"""
                
        except Exception as e:
            print(f"Error booking appointment: {e}")
            return "Error booking appointment. Please try again."
    
    def _get_providers(self):
        """
        Get list of service providers
        """
        try:
            with SessionLocal() as db:
                providers = db.query(ServiceProvider).all()
                return [(p.id, f"{p.name} ({p.service_type})") for p in providers]
        except Exception as e:
            print(f"Error getting providers: {e}")
            return []

def launch_ui():
    ui = AppointmentUI()
    interface = ui.create_interface()
    interface.launch(share=True) 