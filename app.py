from flask import Flask, request, render_template, redirect, url_for
import subprocess
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'  # Folder to store uploaded files

# Ensure the uploads folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'video' not in request.files or 'srt' not in request.files:
        return "No file part"

    video_file = request.files['video']
    srt_file = request.files['srt']

    if video_file.filename == '' or srt_file.filename == '':
        return "No selected file"

    # Save the uploaded files
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_file.filename)
    srt_path = os.path.join(app.config['UPLOAD_FOLDER'], srt_file.filename)
    video_file.save(video_path)
    srt_file.save(srt_path)

    # Run your original Python script
    subprocess.Popen(['python', 'sinkit.py', srt_path, video_path])

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
