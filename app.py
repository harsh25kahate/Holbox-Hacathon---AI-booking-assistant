import pandas as pd
from fastapi import FastAPI
from gradio import Interface
import gradio as gr
import pyttsx3
import threading
import uvicorn
from datetime import datetime, timedelta
import re

# Initialize FastAPI app
app = FastAPI(title="AI Appointment Booking System")

# Initialize text-to-speech engine
engine = pyttsx3.init()

def load_appointments():
    """Load appointments from CSV file"""
    try:
        return pd.read_csv('demo.csv')
    except:
        return pd.DataFrame(columns=[
            'booking_number', 'service_name', 'service_provider_name', 
            'user_name', 'booking_status', 'time_slot', 
            'service_provider_number', 'user_number'
        ])

def save_appointments(df):
    """Save appointments to CSV file"""
    df.to_csv('demo.csv', index=False)

def speak_response(text):
    """Convert text to speech"""
    engine.say(text)
    engine.runAndWait()

def get_next_available_slot(df, provider, current_slot):
    """Find the next available time slot"""
    current_dt = datetime.strptime(current_slot, "%Y-%m-%d %I:%M %p")
    all_slots = []
    
    # Generate slots for next 7 days
    for i in range(7):
        date = current_dt.date() + timedelta(days=i)
        for hour in [9, 10, 11, 14, 15, 16]:  # 9 AM to 5 PM, excluding lunch
            slot = datetime.combine(date, datetime.min.time().replace(hour=hour))
            slot_str = slot.strftime("%Y-%m-%d %I:%M %p")
            if not df[(df['service_provider_name'] == provider) & 
                     (df['time_slot'] == slot_str) & 
                     (df['booking_status'] == 'Confirmed')].empty:
                continue
            all_slots.append(slot_str)
    
    return all_slots[0] if all_slots else None

def get_available_slots(df, provider, date):
    """Get all available slots for a given date and provider"""
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    all_slots = []
    
    for hour in [9, 10, 11, 14, 15, 16]:  # 9 AM to 5 PM, excluding lunch
        slot = datetime.combine(date_obj, datetime.min.time().replace(hour=hour))
        slot_str = slot.strftime("%Y-%m-%d %I:%M %p")
        if df[(df['service_provider_name'] == provider) & 
             (df['time_slot'] == slot_str) & 
             (df['booking_status'] == 'Confirmed')].empty:
            all_slots.append(slot_str)
    
    return all_slots

def process_query(user_input):
    """Process user query and return voice response"""
    df = load_appointments()
    
    # Convert user input to lowercase for better matching
    user_input = user_input.lower()
    response = ""

    # Check for booking-related queries
    if 'book' in user_input or 'schedule' in user_input:
        # Extract date and time using regex
        date_pattern = r'\d{4}-\d{2}-\d{2}'
        time_pattern = r'\d{1,2}(?::\d{2})?\s*(?:am|pm)'
        provider_pattern = r'(?:with|for)\s+(dr\.\s*\w+|ms\.\s*\w+)'
        
        dates = re.findall(date_pattern, user_input, re.IGNORECASE)
        times = re.findall(time_pattern, user_input, re.IGNORECASE)
        providers = re.findall(provider_pattern, user_input, re.IGNORECASE)
        
        if not (dates and times and providers):
            response = "I need the date, time, and provider name to book an appointment. Could you please provide these details?"
        else:
            slot = f"{dates[0]} {times[0].upper()}"
            provider = providers[0].title()
            
            # Check if slot is available
            if df[(df['service_provider_name'] == provider) & 
                 (df['time_slot'] == slot) & 
                 (df['booking_status'] == 'Confirmed')].empty:
                # Generate new booking number
                new_booking = f"B{str(len(df) + 1).zfill(3)}"
                
                # Add new booking
                new_row = {
                    'booking_number': new_booking,
                    'service_name': 'General Checkup',  # Default service
                    'service_provider_name': provider,
                    'user_name': 'New Patient',  # Default name
                    'booking_status': 'Confirmed',
                    'time_slot': slot,
                    'service_provider_number': df[df['service_provider_name'] == provider]['service_provider_number'].iloc[0],
                    'user_number': '+1-555-NEW-USER'  # Default number
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_appointments(df)
                response = f"Thank you for booking! Your appointment is confirmed for {slot} with {provider}. Your booking number is {new_booking}."
            else:
                next_slot = get_next_available_slot(df, provider, slot)
                if next_slot:
                    response = f"Sorry, the selected time slot is already booked. The next available slot is on {next_slot}. Would you like to book that instead?"
                else:
                    response = "Sorry, no available slots found in the next 7 days."

    # Check for cancellation queries
    elif 'cancel' in user_input:
        booking_numbers = re.findall(r'B\d{3}', user_input.upper())
        if booking_numbers:
            booking = df[df['booking_number'] == booking_numbers[0]]
            if not booking.empty:
                df.loc[df['booking_number'] == booking_numbers[0], 'booking_status'] = 'Cancelled'
                save_appointments(df)
                response = f"Your appointment {booking_numbers[0]} has been cancelled."
            else:
                response = f"Booking {booking_numbers[0]} not found."
        else:
            response = "Please provide the booking number to cancel your appointment."

    # Check for available slots query
    elif 'available' in user_input and 'slot' in user_input:
        date_pattern = r'\d{4}-\d{2}-\d{2}'
        provider_pattern = r'(?:with|for)\s+(dr\.\s*\w+|ms\.\s*\w+)'
        
        dates = re.findall(date_pattern, user_input)
        providers = re.findall(provider_pattern, user_input, re.IGNORECASE)
        
        if dates and providers:
            available_slots = get_available_slots(df, providers[0].title(), dates[0])
            if available_slots:
                response = f"Available slots for {dates[0]} with {providers[0].title()} are: {', '.join(available_slots)}"
            else:
                response = f"No available slots found for {dates[0]} with {providers[0].title()}"
        else:
            response = "Please specify the date and provider name to check available slots."

    # Handle other queries
    elif 'booking' in user_input and 'status' in user_input:
        booking_numbers = re.findall(r'B\d{3}', user_input.upper())
        if booking_numbers:
            booking = df[df['booking_number'] == booking_numbers[0]]
            if not booking.empty:
                response = f"Booking {booking_numbers[0]} is {booking['booking_status'].iloc[0]}"
            else:
                response = f"Booking {booking_numbers[0]} not found"
        else:
            response = "Please provide a booking number"
    
    elif 'appointments' in user_input or 'bookings' in user_input:
        total = len(df)
        confirmed = len(df[df['booking_status'] == 'Confirmed'])
        response = f"There are {total} total bookings, {confirmed} are confirmed"
    
    else:
        response = """I can help you with:
1. Booking appointments (e.g., 'book appointment with Dr. Smith on 2024-03-20 10:00 AM')
2. Cancelling appointments (e.g., 'cancel booking B001')
3. Checking booking status (e.g., 'what's the status of booking B001')
4. Finding available slots (e.g., 'show available slots for Dr. Smith on 2024-03-20')
Please let me know what you'd like to do."""

    # Convert response to speech
    threading.Thread(target=speak_response, args=(response,)).start()
    return response

def create_ui():
    """Create Gradio interface"""
    iface = Interface(
        fn=process_query,
        inputs=gr.Textbox(label="How can I help you? (I'll respond with voice!)"),
        outputs=gr.Textbox(label="Response"),
        title="AI Appointment Assistant",
        description="""I can help you with:
- Booking appointments
- Cancelling appointments
- Checking booking status
- Finding available slots
Just tell me what you need!""",
        examples=[
            ["Book an appointment with Dr. Smith on 2024-03-20 10:00 AM"],
            ["Cancel booking B001"],
            ["What's the status of booking B001?"],
            ["Show available slots for Dr. Smith on 2024-03-20"]
        ]
    )
    return iface

def run_fastapi():
    """Run the FastAPI server"""
    uvicorn.run(app, host="0.0.0.0", port=8000)

def main():
    # Start FastAPI in a separate thread
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    
    # Launch Gradio UI
    ui = create_ui()
    ui.launch(share=True)

if __name__ == "__main__":
    main() 