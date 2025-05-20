# TechJoint Transcription

This repository provides a Python script for transcribing large audio files with OpenAI. The audio is automatically split into five-minute chunks before each chunk is sent to the OpenAI API for transcription. The final output is the combined text from all chunks.

## Getting Started in GitHub Codespaces

1. **Create a Codespace** – In GitHub, choose **Code → Codespaces → Create codespace on main**.
2. Dependencies are installed automatically by the `postCreateCommand` in `.devcontainer/devcontainer.json`.
3. Add a `.env` file in the project root with your OpenAI API key:
   ```bash
   echo "OPENAI_API_KEY=YOUR_KEY_HERE" > .env
   ```
   The `.env` file is ignored by Git, so your key remains private.
4. From the terminal, run the transcription script:
   ```bash
   python transcribe.py path/to/audio.mp3 -o output.txt
   ```
   Replace `path/to/audio.mp3` with your file. The optional `-o` flag writes the result to `output.txt`.

5. Alternatively, launch the Flask web interface:
   ```bash
   python app.py
   ```
   Then open `http://localhost:5000` in your browser and upload an audio file (up to 100&nbsp;MB by default).

## Security Notes

- Keep your API key inside the `.env` file and **never** commit it.
- Temporary audio chunks are deleted after transcription.
- Review OpenAI's data policies to ensure your usage complies with their terms.

## Requirements

- Python 3.10+
- `ffmpeg` installed (required by `pydub`)

The web interface requires Flask, which is installed automatically in Codespaces.

All Python dependencies are listed in `requirements.txt`.
