import os
import tempfile
import uuid
import threading
import logging
from flask import Flask, request, render_template, send_file, jsonify
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import openai
from moviepy.editor import AudioFileClip, VideoFileClip

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
logger = logging.getLogger(__name__)

# Initialize OpenAI with API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# Track async transcription tasks
tasks = {}

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a", "mp4", "mov"}

# In-memory store for generated transcript files
transcripts = {}


def split_into_chunks(path: str) -> list:
    """Split an audio/video file into 5-minute chunks and return list of paths."""
    chunks = []
    audio_clip = None
    video_clip = None
    try:
        try:
            audio_clip = AudioFileClip(path)
        except Exception:
            video_clip = VideoFileClip(path)
            audio_clip = video_clip.audio

        duration = int(audio_clip.duration)
        for start in range(0, duration, 300):
            end = min(start + 300, duration)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            audio_clip.subclip(start, end).write_audiofile(tmp.name, logger=None)
            chunks.append(tmp.name)
    finally:
        if audio_clip:
            audio_clip.close()
        if video_clip:
            video_clip.close()

    return chunks


def process_task(token: str):
    """Background worker to transcribe uploaded file."""
    info = tasks[token]
    path = info["file"]
    try:
        chunks = split_into_chunks(path)
        total = len(chunks)
        transcript_parts = []
        for i, chunk_path in enumerate(chunks, start=1):
            tasks[token]["progress"] = int((i - 1) / total * 100)
            tasks[token]["status"] = f"Transcribing chunk {i} of {total}"
            with open(chunk_path, "rb") as f:
                resp = openai.audio.transcriptions.create(model="whisper-1", file=f)
            text = resp.get("text") if isinstance(resp, dict) else getattr(resp, "text", "")
            transcript_parts.append(text)
            os.unlink(chunk_path)

        full_text = "\n".join(transcript_parts)
        info["progress"] = 100
        info["status"] = "done"
        info["transcript"] = full_text

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tfile:
            tfile.write(full_text)
            transcripts[token] = tfile.name
    except Exception as exc:
        info["status"] = "error"
        info["error"] = str(exc)
        logger.exception("Error processing file: %s", exc)
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass

def allowed_file(filename: str) -> bool:
    """Check if a filename has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.before_request
def log_request_info():
    logger.info("%s %s", request.method, request.path)

@app.route("/")
def index():
    """Render the upload form."""
    return render_template("index.html")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    """Handle file upload and start background transcription."""
    upload = request.files.get("file")
    if not upload or upload.filename == "":
        return render_template("index.html", error="No file selected")
    if not allowed_file(upload.filename):
        return render_template("index.html", error="Unsupported file type")

    filename = secure_filename(upload.filename)

    # Save upload to a temporary file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1])
    upload.save(tmp.name)

    token = uuid.uuid4().hex
    tasks[token] = {"progress": 0, "status": "queued", "file": tmp.name}

    thread = threading.Thread(target=process_task, args=(token,))
    thread.daemon = True
    thread.start()

    return render_template("progress.html", task_id=token)

@app.route("/download")
def download():
    """Serve the transcript text file for download."""
    token = request.args.get("filename")
    path = transcripts.get(token)
    if not path or not os.path.exists(path):
        return render_template("index.html", error="Transcript not found")
    return send_file(path, as_attachment=True, download_name="transcript.txt")


@app.route("/progress")
def progress():
    """Return JSON progress for a given task."""
    token = request.args.get("task_id")
    info = tasks.get(token)
    if not info:
        return jsonify({"status": "unknown", "progress": 0})
    return jsonify({"status": info.get("status"), "progress": info.get("progress", 0)})


@app.route("/result")
def result():
    """Show the final transcript."""
    token = request.args.get("task_id")
    info = tasks.get(token)
    if not info:
        return render_template("index.html", error="Invalid task")
    if info.get("status") != "done":
        error = info.get("error", "Transcription not complete")
        return render_template("index.html", error=error)

    transcript = info.get("transcript", "")
    return render_template("result.html", transcript=transcript, filename=token)

if __name__ == "__main__":
    app.run(debug=True)
