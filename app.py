import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png', 'gif'}

# Simple admin credentials (in production, use a database)
ADMIN_USERNAME = 'ak'
ADMIN_PASSWORD_HASH = generate_password_hash('123')  # Change this!

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# File to store file metadata (in production, use a database)
METADATA_FILE = 'file_metadata.json'

def allowed_file(filename):
    """Check if the file extension is allowed"""
    if '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS

def load_file_metadata():
    """Load file metadata from JSON file"""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_file_metadata(metadata):
    """Save file metadata to JSON file"""
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

def add_file_record(filename, original_name, timestamp):
    """Add a new file record to metadata"""
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
    # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()  # FIXED
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    
    # Save file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Add record to metadata
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        add_file_record(unique_filename, original_filename, timestamp)
        
        flash(f'File "{original_filename}" uploaded successfully!', 'success')
        return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload PDF, Word documents, or images only.', 'error')
        return redirect(url_for('index'))

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
    # Filter out processed files or show all based on preference
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

# File preview route
@app.route('/preview/<file_id>')
def preview_file(file_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    metadata = load_file_metadata()
    file_record = next((f for f in metadata if f['id'] == file_id), None)

    if not file_record:
        flash('File not found', 'error')
        return redirect(url_for('admin_dashboard'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_record['filename'])
    extension = file_record['filename'].rsplit('.', 1)[1].lower()

    # Direct preview for images
    if extension in ['jpg', 'jpeg', 'png', 'gif']:
        return send_from_directory(app.config['UPLOAD_FOLDER'], file_record['filename'])

    # Inline preview for PDF
    if extension == 'pdf':
        return send_from_directory(app.config['UPLOAD_FOLDER'], file_record['filename'], as_attachment=False)

    # For other types (doc/docx), force download since browser can't preview easily
    return send_from_directory(app.config['UPLOAD_FOLDER'], file_record['filename'], as_attachment=True)

# QR Code generation route
import qrcode
import io
from flask import send_file

@app.route('/qrcode')
def generate_qrcode():
    try:
        # Always point to your live hosted domain
        upload_url = "https://cyber-cafe-xerox-app.onrender.com/"

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(upload_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Save to BytesIO
        img_io = io.BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)

        return send_file(img_io, mimetype='image/png')

    except Exception as e:
        print(f"QR Code generation error: {str(e)}")
        return f"Error generating QR code: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)


