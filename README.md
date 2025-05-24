# Transcribe

A Flask web application that sends audio or video uploads to OpenAI's `gpt-4o-transcribe` model. Large files are automatically split into five-minute pieces and processed one by one with progress feedback.

## Setup

1. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   `pydub` and `moviepy` require `ffmpeg` to be installed on your system.
3. Set your OpenAI API key in the environment:
   ```bash
   export OPENAI_API_KEY=your_key_here
   ```
   Or create a `.env` file with the line:
   ```bash
   OPENAI_API_KEY=your_key_here
   ```
4. Run the application:
   ```bash
   flask run
   ```
   The app will be available at `http://127.0.0.1:5000`.

## Usage

1. Navigate to the homepage.
2. Upload an audio or video file (`.mp3`, `.wav`, `.m4a`, `.mp4`, `.mov`, etc.). Files of any size are supported. Large files are automatically split into 5-minute chunks and processed one by one. A progress page will show the current percentage.
3. When processing is complete, the transcript will be displayed and can be downloaded as a `.txt` file.

## Notes

Basic request information and any processing errors are logged to stdout. This project requires network access to communicate with OpenAI's API when transcribing files. MoviePy relies on `ffmpeg` being available on your system.
