from flask import Flask, request, render_template_string
from pathlib import Path
from werkzeug.utils import secure_filename

from transcribe import setup_openai, transcribe_audio_file

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB upload limit

@app.route('/', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            return 'No file uploaded', 400
        filename = secure_filename(file.filename)
        temp_path = Path('/tmp') / filename
        file.save(temp_path)
        setup_openai()
        text = transcribe_audio_file(temp_path)
        temp_path.unlink(missing_ok=True)
        return render_template_string('<pre>{{text}}</pre>', text=text)
    return '''
    <!doctype html>
    <title>Upload Audio File</title>
    <h1>Upload Audio File for Transcription</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
