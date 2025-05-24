import os
import sys
import tempfile
import logging
from flask import Flask, request, render_template, send_file
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import openai

load_dotenv()

# Initialize OpenAI with API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
# Limit uploads to 100 MB
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

# Basic logging to stdout
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s %(levelname)s: %(message)s'
)
app.logger.setLevel(logging.INFO)

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a", "mp4", "mov"}

# In-memory store for generated transcript files
transcripts = {}

def allowed_file(filename: str) -> bool:
    """Check if a filename has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.before_request
def log_request_info():
    """Log basic request info."""
    app.logger.info("%s %s", request.method, request.path)

@app.route("/")
def index():
    """Render the upload form."""
    return render_template("index.html")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    """Handle file upload and send to OpenAI for transcription."""
    upload = request.files.get("file")
    if not upload or upload.filename == "":
        return render_template("index.html", error="No file selected")
    if not allowed_file(upload.filename):
        return render_template("index.html", error="Unsupported file type")

    try:
        # Save upload to a temporary file for sending to the API
        filename = secure_filename(upload.filename)
        suffix = os.path.splitext(filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            upload.save(tmp.name)
            tmp.seek(0)
            response = openai.audio.transcriptions.create(
                model="whisper-1",
                file=open(tmp.name, "rb")
            )

        # Extract transcript text from response
        transcript = response.get("text") if isinstance(response, dict) else getattr(response, "text", "")

        # Store transcript in a temp file for download
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tfile:
            tfile.write(transcript)
            transcript_path = tfile.name

        token = os.path.basename(transcript_path)
        transcripts[token] = transcript_path

        return render_template("result.html", transcript=transcript, filename=token)
    except Exception as exc:
        # Show the error message to the user
        app.logger.error("Error during transcription: %s", exc)
        return render_template("index.html", error=str(exc))
    finally:
        # Clean up upload temporary file
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(error):
    """Return friendly message when file is too big."""
    app.logger.error("Uploaded file too large")
    return render_template("index.html", error="File too large (limit 100 MB)"), 413

@app.route("/download")
def download():
    """Serve the transcript text file for download."""
    token = request.args.get("filename")
    path = transcripts.get(token)
    if not path or not os.path.exists(path):
        return render_template("index.html", error="Transcript not found")
    return send_file(path, as_attachment=True, download_name="transcript.txt")

if __name__ == "__main__":
    app.run(debug=True)
