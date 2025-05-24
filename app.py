import os
import uuid
import logging
import tempfile
import threading

from flask import Flask, request, render_template, send_file, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from pydub import AudioSegment
from moviepy.editor import VideoFileClip, AudioFileClip
import openai

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

logging.basicConfig(level=logging.INFO)

jobs = {}

@app.before_request
def log_request():
    logging.info("%s %s from %s", request.method, request.path, request.remote_addr)

ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a", "mp4", "mov"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def transcribe_chunk(path: str) -> str:
    with open(path, "rb") as audio_file:
        resp = openai.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=audio_file,
            response_format="text",
        )
    return resp.get("text") if isinstance(resp, dict) else getattr(resp, "text", "")


def background_job(job_id: str, file_path: str) -> None:
    try:
        ext = os.path.splitext(file_path)[1].lower()
        audio_path = file_path
        if ext in {".mp4", ".mov"}:
            clip = VideoFileClip(file_path)
            audio_path = os.path.join(tempfile.gettempdir(), job_id + ".wav")
            clip.audio.write_audiofile(audio_path, logger=None)
            clip.close()

        sound = AudioSegment.from_file(audio_path)
        chunk_ms = 5 * 60 * 1000
        chunks = list(range(0, len(sound), chunk_ms))
        transcripts = []
        for i, start in enumerate(chunks):
            end = min(start + chunk_ms, len(sound))
            chunk = sound[start:end]
            chunk_file = os.path.join(tempfile.gettempdir(), f"{job_id}_{i}.mp3")
            chunk.export(chunk_file, format="mp3")
            text = transcribe_chunk(chunk_file)
            transcripts.append(text.strip())
            os.remove(chunk_file)
            jobs[job_id]["progress"] = int(((i + 1) / len(chunks)) * 100)

        full_text = "\n".join(transcripts)
        txt_path = os.path.join(tempfile.gettempdir(), job_id + ".txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        jobs[job_id].update(done=True, path=txt_path, transcript=full_text)

        if audio_path != file_path:
            os.remove(audio_path)
        os.remove(file_path)
    except Exception as exc:  # pragma: no cover - network calls
        logging.exception("Transcription failed")
        jobs[job_id].update(done=True, error=str(exc))


@app.route("/")
def index():
    return render_template("index.html", error=request.args.get("error"))


@app.route("/transcribe", methods=["POST"])
def transcribe():
    upload = request.files.get("file")
    if not upload or upload.filename == "":
        return render_template("index.html", error="No file selected")
    if not allowed_file(upload.filename):
        return render_template("index.html", error="Unsupported file type")

    filename = secure_filename(upload.filename)
    saved_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4().hex}_{filename}")
    upload.save(saved_path)

    job_id = uuid.uuid4().hex
    jobs[job_id] = {"progress": 0, "done": False}
    threading.Thread(target=background_job, args=(job_id, saved_path), daemon=True).start()
    return redirect(url_for("progress", job_id=job_id))


@app.route("/progress/<job_id>")
def progress(job_id):
    job = jobs.get(job_id)
    if not job:
        return render_template("index.html", error="Invalid job ID")
    if request.args.get("json"):
        return jsonify(progress=job.get("progress", 0), done=job.get("done", False), error=job.get("error"))
    if job.get("done"):
        if job.get("error"):
            return render_template("index.html", error=job["error"])
        return redirect(url_for("result", job_id=job_id))
    return render_template("progress.html", progress=job.get("progress", 0), job_id=job_id)


@app.route("/result/<job_id>")
def result(job_id):
    job = jobs.get(job_id)
    if not job or not job.get("done"):
        return redirect(url_for("progress", job_id=job_id))
    return render_template("result.html", transcript=job.get("transcript", ""), job_id=job_id)


@app.route("/download/<job_id>")
def download(job_id):
    job = jobs.get(job_id)
    if not job or not job.get("path"):
        return render_template("index.html", error="Transcript not found")
    return send_file(job["path"], as_attachment=True, download_name="transcript.txt")


if __name__ == "__main__":  # pragma: no cover - manual execution
    app.run(debug=True)
