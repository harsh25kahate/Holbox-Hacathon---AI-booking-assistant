import gradio as gr
import datetime
from voice.speech_recognition import VoiceHandler
from ai_agent.scheduler import SchedulingAgent
from database.database import SessionLocal
from database.models import User, ServiceProvider, Appointment, TimeSlot

class AppointmentUI:
    def __init__(self):
        self.voice_handler = VoiceHandler()
        self.scheduler = SchedulingAgent()
        
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
            response_parts = ["I understood your request:"]
            
            if details['provider']:
                response_parts.append(f"Provider: {details['provider']}")
            if details['date']:
                response_parts.append(f"Date: {details['date']}")
            if details['time']:
                response_parts.append(f"Time: {details['time']}")
                
            response_parts.append("\nIs this correct? If yes, please proceed to Manual Booking tab to complete your booking.")
            
            return "\n".join(response_parts)
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
                            elem_id="voice_input"
                        )
                    
                voice_output = gr.Textbox(
                    label="Voice Recognition Result",
                    lines=5
                )
                
                process_btn = gr.Button("Process Voice Command")
                
                def initialize_mic():
                    return None
                
                # Initialize microphone on page load
                interface.load(
                    fn=initialize_mic,
                    inputs=[],
                    outputs=[audio_input]
                )
                
                process_btn.click(
                    fn=self.process_voice_booking,
                    inputs=[audio_input],
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