from pathlib import Path
import tempfile

from flask import Flask, request, render_template_string

from transcribe import setup_openai, transcribe_audio_file

app = Flask(__name__)
setup_openai()

HTML_FORM = """
<!doctype html>
<title>Transcribe Audio</title>
<h1>Upload audio file</h1>
<form method=post enctype=multipart/form-data>
  <input type=file name=audio required>
  <input type=submit value=Transcribe>
</form>
{% if transcription %}
<h2>Transcription</h2>
<pre>{{ transcription }}</pre>
{% endif %}
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    transcription = None
    if request.method == 'POST':
        uploaded = request.files.get('audio')
        if uploaded:
            suffix = Path(uploaded.filename).suffix
            with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
                uploaded.save(tmp.name)
                transcription = transcribe_audio_file(Path(tmp.name))
    return render_template_string(HTML_FORM, transcription=transcription)


if __name__ == '__main__':
    app.run(debug=True)
