from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import os
import uuid
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = '/tmp/uploads'
CONVERTED_FOLDER = '/tmp/converted'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

records = {}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'version': '1.0'})

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file'}), 400
    
    f = request.files['file']
    if f.filename == '':
        return jsonify({'success': False, 'error': 'Empty filename'}), 400
    
    file_id = hashlib.sha256(f"{uuid.uuid4()}{time.time()}".encode()).hexdigest()[:16]
    ext = Path(f.filename).suffix.lower().lstrip('.')
    filename = f"{file_id}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    f.save(filepath)
    
    records[file_id] = {
        'file_id': file_id,
        'original_name': f.filename,
        'path': filepath,
        'size': os.path.getsize(filepath),
        'ext': ext,
        'expires': datetime.utcnow() + timedelta(hours=1)
    }
    
    return jsonify({
        'success': True,
        'file': {
            'file_id': file_id,
            'original_name': f.filename,
            'size': os.path.getsize(filepath),
            'download_url': f'/api/download/{file_id}'
        }
    })

@app.route('/api/download/<file_id>')
def download(file_id):
    if file_id not in records:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    
    rec = records[file_id]
    if not os.path.exists(rec['path']):
        return jsonify({'success': False, 'error': 'File missing'}), 404
    
    return send_file(rec['path'], as_attachment=True, download_name=rec['original_name'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)    
    file_id = hashlib.sha256(f"{uuid.uuid4()}{time.time()}".encode()).hexdigest()[:16]
    ext = Path(f.filename).suffix.lower().lstrip('.')
    filename = f"{file_id}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    f.save(filepath)
    
    records[file_id] = {
        'file_id': file_id,
        'original_name': f.filename,
        'path': filepath,
        'size': os.path.getsize(filepath),
        'ext': ext,
        'expires': datetime.utcnow() + timedelta(hours=1)
    }
    
    return jsonify({
        'success': True,
        'file': {
            'file_id': file_id,
            'original_name': f.filename,
            'size': os.path.getsize(filepath),
            'download_url': f'/api/download/{file_id}'
        }
    })

@app.route('/api/download/<file_id>')
def download(file_id):
    if file_id not in records:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    
    rec = records[file_id]
    if not os.path.exists(rec['path']):
        return jsonify({'success': False, 'error': 'File missing'}), 404
    
    return send_file(rec['path'], as_attachment=True, download_name=rec['original_name'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)    'tiff': ['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp', 'pdf'],
    'svg': ['png', 'jpg', 'jpeg', 'webp', 'pdf'],
    'heic': ['jpg', 'jpeg', 'png', 'webp'],
    'pdf': ['png', 'jpg', 'jpeg', 'webp'],
}

# ========== DATA MODEL ==========
class Status(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class FileRecord:
    file_id: str
    original_name: str
    file_path: str
    file_size: int
    extension: str
    status: Status
    converted_path: str = None
    converted_name: str = None
    target_format: str = None
    error: str = None
    expires_at: datetime = None
    
    def to_dict(self):
        return {
            'file_id': self.file_id,
            'original_name': self.original_name,
            'file_size': self.file_size,
            'extension': self.extension,
            'status': self.status.value,
            'target_format': self.target_format,
            'converted_name': self.converted_name,
            'download_url': f'/api/download/{self.file_id}' if self.status == Status.COMPLETED else None,
            'expires_in': max(0, (self.expires_at - datetime.utcnow()).total_seconds()) if self.expires_at else 0
        }

# ========== STORAGE ==========
records = {}

def cleanup_expired():
    """Delete old files"""
    now = datetime.utcnow()
    expired = [fid for fid, rec in records.items() if now > rec.expires_at]
    for fid in expired:
        rec = records[fid]
        if os.path.exists(rec.file_path):
            os.remove(rec.file_path)
        if rec.converted_path and os.path.exists(rec.converted_path):
            os.remove(rec.converted_path)
        del records[fid]

def generate_id():
    return hashlib.sha256(f"{uuid.uuid4()}{time.time()}".encode()).hexdigest()[:16]

# ========== APP ==========
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
CORS(app)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

# ========== ROUTES ==========
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'version': '1.0.0', 'features': ['image_conversion']})

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file'}), 400
    
    files = request.files.getlist('file')
    results = []
    
    for f in files:
        if f.filename == '':
            continue
            
        ext = Path(f.filename).suffix.lower().lstrip('.')
        if ext not in ALLOWED_EXTENSIONS:
            results.append({'success': False, 'error': f'Unsupported: .{ext}'})
            continue
        
        cleanup_expired()
        
        file_id = generate_id()
        stored_name = f"{file_id}.{ext}"
        file_path = os.path.join(UPLOAD_FOLDER, stored_name)
        f.save(file_path)
        
        record = FileRecord(
            file_id=file_id,
            original_name=f.filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            extension=ext,
            status=Status.PENDING,
            expires_at=datetime.utcnow() + timedelta(seconds=RETENTION_SECONDS)
        )
        records[file_id] = record
        
        results.append({
            'success': True,
            'file': record.to_dict(),
            'conversion_options': CONVERSION_MAP.get(ext, [])
        })
    
    return jsonify({'success': True, 'files': results})

@app.route('/api/convert/<file_id>', methods=['POST'])
def convert(file_id):
    if file_id not in records:
        return jsonify({'success': False, 'error': 'File not found'}), 404
    
    data = request.get_json() or {}
    target = data.get('target_format')
    
    if not target:
        return jsonify({'success': False, 'error': 'Target format required'}), 400
    
    record = records[file_id]
    available = CONVERSION_MAP.get(record.extension, [])
    
    if target not in available:
        return jsonify({'success': False, 'error': f'Cannot convert to {target}', 'available': available}), 400
    
    record.status = Status.PROCESSING
    record.target_format = target
    
    try:
        output_path = os.path.join(CONVERTED_FOLDER, f"{file_id}.{target}")
        
        with Image.open(record.file_path) as img:
            # Handle transparency
            if target in ['jpg', 'jpeg'] and img.mode in ('RGBA', 'LA', 'P'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                bg.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = bg
            
            # Save
            kwargs = {}
            if target in ['jpg', 'jpeg']:
                kwargs = {'quality': 95, 'optimize': True}
            elif target == 'png':
                kwargs = {'optimize': True}
            elif target == 'webp':
                kwargs = {'quality': 90}
            
            fmt = 'JPEG' if target in ['jpg', 'jpeg'] else target.upper()
            img.save(output_path, format=fmt, **kwargs)
        
        record.status = Status.COMPLETED
        record.converted_path = output_path
        record.converted_name = f"{Path(record.original_name).stem}.{target}"
        
        return jsonify({'success': True, 'file': record.to_dict()})
        
    except Exception as e:
        record.status = Status.FAILED
        record.error = str(e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/status/<file_id>', methods=['GET'])
def status(file_id):
    if file_id not in records:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    return jsonify({'success': True, 'file': records[file_id].to_dict()})

@app.route('/api/download/<file_id>', methods=['GET'])
def download(file_id):
    if file_id not in records:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    
    record = records[file_id]
    if record.status != Status.COMPLETED or not record.converted_path:
        return jsonify({'success': False, 'error': 'Not ready'}), 400
    
    if not os.path.exists(record.converted_path):
        return jsonify({'success': False, 'error': 'File missing'}), 404
    
    mime = {
        'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        'webp': 'image/webp', 'gif': 'image/gif', 'bmp': 'image/bmp',
        'tiff': 'image/tiff', 'pdf': 'application/pdf'
    }.get(target := Path(record.converted_name).suffix.lower().lstrip('.'), 'application/octet-stream')
    
    return send_file(record.converted_path, mimetype=mime, as_attachment=True, download_name=record.converted_name)

@app.route('/api/delete/<file_id>', methods=['DELETE'])
def delete(file_id):
    if file_id not in records:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    
    record = records[file_id]
    if os.path.exists(record.file_path):
        os.remove(record.file_path)
    if record.converted_path and os.path.exists(record.converted_path):
        os.remove(record.converted_path)
    del records[file_id]
    
    return jsonify({'success': True, 'message': 'Deleted'})

@app.route('/api/formats', methods=['GET'])
def formats():
    return jsonify({
        'success': True,
        'categories': {
            'image': {
                'name': 'Images',
                'formats': list(ALLOWED_EXTENSIONS),
                'conversions': CONVERSION_MAP
            }
        },
        'max_file_size': '500MB',
        'batch_limit': 10
    })

# ========== MAIN ==========
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
