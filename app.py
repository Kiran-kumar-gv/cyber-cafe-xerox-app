import os
import uuid
import io
import json
import mimetypes
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_from_directory, send_file
)
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
import qrcode
from PIL import Image

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'doc', 'txt',
    'jpg', 'jpeg', 'png', 'gif',
    'webp', 'bmp', 'tif', 'tiff',
    'svg', 'ico', 'jfif', 'avif', 'heic'
}

# Extensions considered previewable images
IMAGE_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'webp',
    'bmp', 'tif', 'tiff', 'svg', 'ico',
    'jfif', 'avif', 'heic'
}

# Simple admin credentials (use DB in production)
ADMIN_USERNAME = 'ak'
ADMIN_PASSWORD_HASH = generate_password_hash('123')

# Ensure uploads & thumbs directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbs'), exist_ok=True)

# File metadata storage
METADATA_FILE = 'file_metadata.json'


def allowed_file(filename):
    """Check if file extension is allowed"""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def load_file_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return []


def save_file_metadata(metadata):
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)


def add_file_record(filename, original_name, timestamp):
    metadata = load_file_metadata()
    metadata.append({
        'id': str(uuid.uuid4()),
        'filename': filename,
        'original_name': original_name,
        'timestamp': timestamp,
        'processed': False
    })
    save_file_metadata(metadata)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"

        # Save file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)

        # Create thumbnail if image
        if file_extension in IMAGE_EXTENSIONS:
            try:
                img = Image.open(file_path)
                img.thumbnail((400, 400))
                thumb_path = os.path.join(app.config['UPLOAD_FOLDER'], 'thumbs', unique_filename)
                img.save(thumb_path)
            except Exception as e:
                app.logger.warning(f"Thumbnail creation failed: {e}")

        # Add record to metadata
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        add_file_record(unique_filename, original_filename, timestamp)

        flash(f'File "{original_filename}" uploaded successfully!', 'success')
        return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload PDF, Word, or images only.', 'error')
        return redirect(url_for('index'))


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/preview/<file_id>')
def preview_file(file_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    metadata = load_file_metadata()
    file_record = next((f for f in metadata if f['id'] == file_id), None)

    if not file_record:
        flash('File not found', 'error')
        return redirect(url_for('admin_dashboard'))

    filename = file_record['filename']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        flash('File not found on disk', 'error')
        return redirect(url_for('admin_dashboard'))

    ext = filename.rsplit('.', 1)[1].lower()
    mimetype, _ = mimetypes.guess_type(file_path)

    if ext in IMAGE_EXTENSIONS or ext == 'pdf' or (mimetype and mimetype.startswith('image/')):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)
    else:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/admin')
def admin_login():
    if 'admin_logged_in' in session:
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')


@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    username = request.form['username']
    password = request.form['password']

    if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
        session['admin_logged_in'] = True
        flash('Login successful!', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Invalid credentials', 'error')
        return redirect(url_for('admin_login'))


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))


@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    metadata = load_file_metadata()
    files = [f for f in metadata if not f.get('processed', False)]
    return render_template('admin_dashboard.html', files=files)


@app.route('/admin/download/<file_id>')
def download_file(file_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    metadata = load_file_metadata()
    file_record = next((f for f in metadata if f['id'] == file_id), None)

    if file_record:
        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            file_record['filename'],
            as_attachment=True,
            download_name=file_record['original_name']
        )
    else:
        flash('File not found', 'error')
        return redirect(url_for('admin_dashboard'))


@app.route('/admin/mark_processed/<file_id>')
def mark_processed(file_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    metadata = load_file_metadata()
    for file_record in metadata:
        if file_record['id'] == file_id:
            file_record['processed'] = True
            break

    save_file_metadata(metadata)
    flash('File marked as processed', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/qrcode')
def generate_qrcode():
    try:
        # Dynamic: works locally and in Render
        upload_url = request.url_root

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(upload_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img_io = io.BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)

        return send_file(img_io, mimetype='image/png')
    except Exception as e:
        print(f"QR Code generation error: {str(e)}")
        return f"Error generating QR code: {str(e)}", 500


if __name__ == '__main__':
    app.run(debug=True)
