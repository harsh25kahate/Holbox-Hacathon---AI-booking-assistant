# AI-Powered Appointment Booking System

An intelligent appointment booking system with voice interface and AI-powered scheduling.

## Features

- Voice-based appointment booking
- AI-powered scheduling system
- Real-time availability management
- Interactive web interface using Gradio
- Smart conflict resolution
- Automated notifications

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Access the web interface at `http://localhost:7860`

## Project Structure

- `app.py`: Main application file
- `database/`: Database models and utilities
- `ai_agent/`: AI scheduling agent implementation
- `voice/`: Voice recognition and processing
- `ui/`: Gradio interface components
- `utils/`: Helper functions and utilities

## Technologies Used

- Python 3.9+
- Gradio (Web Interface)
- FastAPI (Backend)
- SQLite (Database)
- SpeechRecognition (Voice Processing)
- scikit-learn (Machine Learning)
- sentence-transformers (Text Processing) 