import os
import uuid
import tempfile
import threading
import logging
from flask import Flask, request, render_template, send_file, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from pydub import AudioSegment
import openai

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a", "mp4", "mov"}

# Store job progress and results
jobs = {}

logging.basicConfig(level=logging.INFO)

@app.before_request
def log_request():
    app.logger.info("%s %s", request.method, request.path)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/transcribe", methods=["POST"])
def transcribe():
    upload = request.files.get("file")
    if not upload or upload.filename == "":
        return render_template("index.html", error="No file selected")
    if not allowed_file(upload.filename):
        return render_template("index.html", error="Unsupported file type")

    filename = secure_filename(upload.filename)
    tmpdir = tempfile.mkdtemp()
    filepath = os.path.join(tmpdir, filename)
    upload.save(filepath)

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "progress": 0.0}
    thread = threading.Thread(target=process_file, args=(job_id, filepath, tmpdir))
    thread.start()

    return render_template("progress.html", job_id=job_id)


def process_file(job_id: str, path: str, tmpdir: str):
    try:
        audio = AudioSegment.from_file(path)
        chunk_ms = 5 * 60 * 1000  # five minutes
        total_chunks = (len(audio) + chunk_ms - 1) // chunk_ms
        parts = []
        for i, start in enumerate(range(0, len(audio), chunk_ms)):
            chunk = audio[start:start + chunk_ms]
            chunk_path = os.path.join(tmpdir, f"chunk_{i}.mp3")
            chunk.export(chunk_path, format="mp3")
            with open(chunk_path, "rb") as cfile:
                resp = openai.audio.transcriptions.create(
                    model="gpt-4o-transcribe",
                    file=cfile
                )
            text = resp.get("text") if isinstance(resp, dict) else getattr(resp, "text", "")
            parts.append(text)
            jobs[job_id]["progress"] = (i + 1) / total_chunks
        transcript = "\n".join(parts)
        tpath = os.path.join(tmpdir, "transcript.txt")
        with open(tpath, "w", encoding="utf-8") as tfile:
            tfile.write(transcript)
        jobs[job_id].update({"status": "done", "transcript": transcript, "tpath": tpath})
    except Exception as exc:
        jobs[job_id].update({"status": "error", "error": str(exc)})
        app.logger.exception("Error processing job %s", job_id)
    finally:
        try:
            os.remove(path)
        except Exception:
            pass


@app.route("/progress/<job_id>")
def progress(job_id):
    if job_id not in jobs:
        return render_template("index.html", error="Job not found")
    return render_template("progress.html", job_id=job_id)


@app.route("/progress_status/<job_id>")
def progress_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"status": "error", "error": "Job not found"})
    return jsonify(job)


@app.route("/result/<job_id>")
def result(job_id):
    job = jobs.get(job_id)
    if not job:
        return render_template("index.html", error="Job not found")
    if job.get("status") != "done":
        return render_template("progress.html", job_id=job_id)
    return render_template("result.html", transcript=job.get("transcript"), job_id=job_id)


@app.route("/download/<job_id>")
def download(job_id):
    job = jobs.get(job_id)
    if not job or job.get("status") != "done":
        return render_template("index.html", error="Transcript not available")
    return send_file(job["tpath"], as_attachment=True, download_name="transcript.txt")


if __name__ == "__main__":
    app.run(debug=True)
