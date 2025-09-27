from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import re
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import csv
from datetime import datetime, timedelta
import os
import threading
import time
import io 
from ultralytics import YOLO
import cv2
import numpy as np
import base64
import json
import uuid
import tempfile

# Create directory for storing face images if it doesn't exist
os.makedirs('face_data', exist_ok=True)
face_model = YOLO('yolov8n.pt')

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///main.db'
app.config['SQLALCHEMY_BINDS'] = {
    'admin_db': 'sqlite:///admin.db',
    'student_db': 'sqlite:///students.db',
    'room_db': 'sqlite:///rooms.db'
}
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Database Models
class Admin(db.Model):
    __bind_key__ = 'admin_db'
    id = db.Column(db.Integer, primary_key=True)
    idname = db.Column(db.String(50), nullable=False, unique=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    session_active = db.Column(db.Boolean, default=False)
    current_bssid = db.Column(db.String(100))

class Room(db.Model):
    __bind_key__ = 'room_db'
    id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(50), nullable=False, unique=True)
    admin_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    active = db.Column(db.Boolean, default=True)
    temporarily_closed = db.Column(db.Boolean, default=False)
    bssid = db.Column(db.String(100))

class RoomMember(db.Model):
    __bind_key__ = 'room_db'
    id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(50), db.ForeignKey('room.room_code'), nullable=False)
    roll_number = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    is_registered = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='Not Present')
    __table_args__ = (db.UniqueConstraint('room_code', 'roll_number', name='_room_roll_uc'),)

class Student(db.Model):
    __bind_key__ = 'student_db'
    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(50), nullable=False, unique=True)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    current_room = db.Column(db.String(50))
    current_bssid = db.Column(db.String(100))
    face_image_path = db.Column(db.String(200))
    is_logged_in = db.Column(db.Boolean, default=False)
    login_time = db.Column(db.DateTime)
    last_active_time = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

class AttendanceRecord(db.Model):
    __bind_key__ = 'student_db'
    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(50), db.ForeignKey('student.roll_number'))
    room_code = db.Column(db.String(50))
    login_time = db.Column(db.DateTime)
    logout_time = db.Column(db.DateTime)
    active_duration = db.Column(db.Float)

# Create database tables
with app.app_context():
    db.create_all()

# Utility functions
def get_wifi_bssid():
    try:
        import platform
        system = platform.system()

        if system == "Windows":
            result = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True)
            match = re.search(r'BSSID\s*:\s*([0-9A-Fa-f:-]+)', result.stdout)
            if match:
                return match.group(1)
        elif system == "Linux":
            try:
                result = subprocess.run(["iwconfig"], capture_output=True, text=True)
                match = re.search(r'Access Point: ([0-9A-Fa-f:]+)', result.stdout)
                if match:
                    return match.group(1)
            except FileNotFoundError:
                try:
                    result = subprocess.run(["iw", "dev"], capture_output=True, text=True)
                    match = re.search(r'addr ([0-9A-Fa-f:]+)', result.stdout)
                    if match:
                        return match.group(1)
                except FileNotFoundError:
                    pass
        elif system == "Darwin":
            try:
                result = subprocess.run(["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"], capture_output=True, text=True)
                match = re.search(r'BSSID: ([0-9A-Fa-f:]+)', result.stdout)
                if match:
                    return match.group(1)
            except FileNotFoundError:
                pass
        
        import socket
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return f"HOST-{hostname}-{ip}"
            
    except Exception as e:
        print(f"Error getting BSSID: {e}")
        return "BSSID-UNAVAILABLE"

def extract_face(image_data):
    try:
        encoded_data = image_data.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        results = face_model(img)
        
        if len(results[0].boxes) == 0:
            return None, "No face detected"
        
        boxes = results[0].boxes
        box = boxes[0].xyxy[0].cpu().numpy()
        x1, y1, x2, y2 = map(int, box)
        
        face = img[y1:y2, x1:x2]
        face = cv2.resize(face, (112, 112))
        
        return face, None
    except Exception as e:
        return None, str(e)

def compare_faces(face1, face2):
    try:
        if face1 is None or face2 is None:
            return False
        
        face1_resized = cv2.resize(face1, (100, 100))
        face2_resized = cv2.resize(face2, (100, 100))
        
        mse = np.mean((face1_resized - face2_resized) ** 2)
        return mse < 1000
    except Exception as e:
        print(f"Face comparison error: {e}")
        return False

def monitor_student_activity():
    while True:
        try:
            current_time = datetime.now()
            timeout_minutes = 5
            
            inactive_students = Student.query.filter(
                Student.is_logged_in == True,
                Student.last_active_time < current_time - timedelta(minutes=timeout_minutes)
            ).all()
            
            for student in inactive_students:
                student.is_logged_in = False
                student.is_active = False
                
                if student.current_room:
                    room_member = RoomMember.query.filter_by(
                        room_code=student.current_room,
                        roll_number=student.roll_number
                    ).first()
                    
                    if room_member:
                        room_member.status = 'Not Present'
                
                record = AttendanceRecord.query.filter_by(
                    roll_number=student.roll_number,
                    logout_time=None
                ).first()
                
                if record:
                    record.logout_time = current_time
                    if record.login_time:
                        duration = (current_time - record.login_time).total_seconds() / 60
                        record.active_duration = duration
            
            db.session.commit()
            time.sleep(60)
            
        except Exception as e:
            print(f"Activity monitor error: {e}")
            time.sleep(60)

# Start the activity monitoring thread
activity_thread = threading.Thread(target=monitor_student_activity, daemon=True)
activity_thread.start()

# Basic API Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'bssid': get_wifi_bssid()})

@app.route('/api/test', methods=['GET'])
def test_api():
    return jsonify({'message': 'API is working'})

# Admin Authentication Routes
@app.route('/api/admin/register', methods=['POST'])
def register_admin():
    try:
        data = request.json
        idname = data.get('idname')
        username = data.get('username')
        password = data.get('password')
        
        if not all([idname, username, password]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
            
        existing_admin = Admin.query.filter_by(username=username).first()
        if existing_admin:
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
            
        existing_idname = Admin.query.filter_by(idname=idname).first()
        if existing_idname:
            return jsonify({'success': False, 'message': 'ID name already exists'}), 400
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_admin = Admin(idname=idname, username=username, password=hashed_password)
        
        db.session.add(new_admin)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Registration successful'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/login', methods=['POST'])
def login_admin():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not all([username, password]):
            return jsonify({'success': False, 'message': 'Username and password are required'}), 400
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and bcrypt.check_password_hash(admin.password, password):
            current_bssid = get_wifi_bssid()
            admin.current_bssid = current_bssid
            admin.session_active = True
            db.session.commit()
            
            return jsonify({
                'success': True,
                'admin': {
                    'id': admin.id,
                    'username': admin.username,
                    'idname': admin.idname,
                    'bssid': current_bssid
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/logout/<int:admin_id>', methods=['POST'])
def logout_admin(admin_id):
    try:
        admin = Admin.query.get(admin_id)
        if admin:
            admin.session_active = False
            db.session.commit()
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Room Management Routes
@app.route('/api/admin/<int:admin_id>/rooms', methods=['GET'])
def get_admin_rooms(admin_id):
    try:
        rooms = Room.query.filter_by(admin_id=admin_id).all()
        room_list = []
        
        for room in rooms:
            member_count = RoomMember.query.filter_by(room_code=room.room_code).count()
            present_count = RoomMember.query.filter_by(room_code=room.room_code, status='Present').count()
            
            status = "Active"
            if room.temporarily_closed:
                status = "Temporarily Closed"
            elif not room.active:
                status = "Inactive"
                
            room_list.append({
                'id': room.id,
                'room_code': room.room_code,
                'created_at': room.created_at.strftime('%Y-%m-%d %H:%M'),
                'status': status,
                'member_count': member_count,
                'present_count': present_count,
                'bssid': room.bssid
            })
        
        return jsonify({'success': True, 'rooms': room_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/rooms', methods=['POST'])
def create_room():
    try:
        data = request.json
        room_code = data.get('room_code')
        admin_id = data.get('admin_id')
        
        if not all([room_code, admin_id]):
            return jsonify({'success': False, 'message': 'Room code and admin ID are required'}), 400
        
        existing_room = Room.query.filter_by(room_code=room_code).first()
        if existing_room:
            if existing_room.admin_id == admin_id:
                current_bssid = get_wifi_bssid()
                existing_room.bssid = current_bssid
                existing_room.active = True
                existing_room.temporarily_closed = False
                db.session.commit()
                return jsonify({'success': True, 'message': f'Room {room_code} reopened successfully'})
            else:
                return jsonify({'success': False, 'message': 'Room code already exists'}), 400
        
        current_bssid = get_wifi_bssid()
        new_room = Room(
            room_code=room_code,
            admin_id=admin_id,
            bssid=current_bssid,
            active=True,
            temporarily_closed=False
        )
        
        db.session.add(new_room)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Room {room_code} created successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/rooms/<room_code>/members', methods=['GET'])
def get_room_members(room_code):
    try:
        room = Room.query.filter_by(room_code=room_code).first()
        if not room:
            return jsonify({'success': False, 'message': 'Room not found'}), 404
        
        members = RoomMember.query.filter_by(room_code=room_code).all()
        member_list = []
        
        for member in members:
            student = Student.query.filter_by(roll_number=member.roll_number).first()
            member_list.append({
                'id': member.id,
                'roll_number': member.roll_number,
                'username': member.username,
                'status': member.status,
                'is_registered': member.is_registered,
                'is_active': student.is_active if student else False,
                'login_time': student.login_time.strftime('%Y-%m-%d %H:%M:%S') if student and student.login_time else None
            })
        
        return jsonify({'success': True, 'members': member_list, 'room_status': 'active' if room.active else 'inactive'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/rooms/<room_code>/members', methods=['POST'])
def add_room_member():
    try:
        data = request.json
        room_code = data.get('room_code')
        roll_number = data.get('roll_number')
        username = data.get('username')
        
        if not all([room_code, roll_number, username]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        room = Room.query.filter_by(room_code=room_code).first()
        if not room:
            return jsonify({'success': False, 'message': 'Room not found'}), 404
        
        existing_member = RoomMember.query.filter_by(room_code=room_code, roll_number=roll_number).first()
        if existing_member:
            return jsonify({'success': False, 'message': 'Student already in room'}), 400
        
        new_member = RoomMember(
            room_code=room_code,
            roll_number=roll_number,
            username=username,
            is_registered=False,
            status='Not Present'
        )
        
        db.session.add(new_member)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Member added successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/members/status', methods=['POST'])
def update_member_status():
    try:
        data = request.json
        room_code = data.get('room_code')
        roll_number = data.get('roll_number')
        status = data.get('status')
        
        if not all([room_code, roll_number, status]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        member = RoomMember.query.filter_by(room_code=room_code, roll_number=roll_number).first()
        if not member:
            return jsonify({'success': False, 'message': 'Member not found'}), 404
        
        member.status = status
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Status updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/rooms/<room_code>/close', methods=['POST'])
def close_room(room_code):
    try:
        room = Room.query.filter_by(room_code=room_code).first()
        if not room:
            return jsonify({'success': False, 'message': 'Room not found'}), 404
        
        room.temporarily_closed = True
        
        # Log out all students in the room
        students_in_room = Student.query.filter_by(current_room=room_code).all()
        current_time = datetime.now()
        
        for student in students_in_room:
            student.current_room = None
            student.is_logged_in = False
            student.is_active = False
            
            # Update attendance record
            record = AttendanceRecord.query.filter_by(
                roll_number=student.roll_number,
                logout_time=None
            ).first()
            
            if record:
                record.logout_time = current_time
                if record.login_time:
                    duration = (current_time - record.login_time).total_seconds() / 60
                    record.active_duration = duration
        
        # Update room members status
        RoomMember.query.filter_by(room_code=room_code).update({'status': 'Not Present'})
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Room closed successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/rooms/<room_code>/attendance/download', methods=['GET'])
def download_attendance(room_code):
    try:
        room = Room.query.filter_by(room_code=room_code).first()
        if not room:
            return jsonify({'success': False, 'message': 'Room not found'}), 404
        
        # Get all attendance records for this room
        records = AttendanceRecord.query.filter_by(room_code=room_code).all()
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Roll Number', 'Login Time', 'Logout Time', 'Duration (minutes)', 'Status'])
        
        for record in records:
            status = 'Complete' if record.logout_time else 'Ongoing'
            duration = record.active_duration if record.active_duration else 'N/A'
            
            writer.writerow([
                record.roll_number,
                record.login_time.strftime('%Y-%m-%d %H:%M:%S') if record.login_time else 'N/A',
                record.logout_time.strftime('%Y-%m-%d %H:%M:%S') if record.logout_time else 'N/A',
                f"{duration:.2f}" if isinstance(duration, float) else duration,
                status
            ])
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv', prefix=f'attendance_{room_code}_')
        temp_file.write(output.getvalue())
        temp_file.close()
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=f'attendance_{room_code}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mimetype='text/csv'
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Student Authentication Routes
@app.route('/api/student/register', methods=['POST'])
def register_student():
    try:
        data = request.json
        roll_number = data.get('roll_number')
        username = data.get('username')
        password = data.get('password')
        face_image = data.get('face_image')
        
        if not all([roll_number, username, password, face_image]):
            return jsonify({'success': False, 'message': 'All fields including face image are required'}), 400
        
        existing_student = Student.query.filter_by(roll_number=roll_number).first()
        if existing_student:
            return jsonify({'success': False, 'message': 'Roll number already exists'}), 400
        
        # Extract and save face image
        face, error = extract_face(face_image)
        if face is None:
            return jsonify({'success': False, 'message': f'Face extraction failed: {error}'}), 400
        
        # Save face image
        face_filename = f"face_{roll_number}_{uuid.uuid4().hex}.jpg"
        face_path = os.path.join('face_data', face_filename)
        cv2.imwrite(face_path, face)
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_student = Student(
            roll_number=roll_number,
            username=username,
            password=hashed_password,
            face_image_path=face_path
        )
        
        db.session.add(new_student)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Registration successful'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/student/login', methods=['POST'])
def login_student():
    try:
        data = request.json
        roll_number = data.get('roll_number')
        password = data.get('password')
        
        if not all([roll_number, password]):
            return jsonify({'success': False, 'message': 'Roll number and password are required'}), 400
        
        student = Student.query.filter_by(roll_number=roll_number).first()
        
        if student and bcrypt.check_password_hash(student.password, password):
            current_time = datetime.now()
            current_bssid = get_wifi_bssid()
            
            student.is_logged_in = True
            student.login_time = current_time
            student.last_active_time = current_time
            student.current_bssid = current_bssid
            student.is_active = True
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'student': {
                    'id': student.id,
                    'roll_number': student.roll_number,
                    'username': student.username,
                    'current_room': student.current_room,
                    'bssid': current_bssid
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/student/eligibility', methods=['POST'])
def check_student_eligibility():
    try:
        data = request.json
        roll_number = data.get('roll_number')
        room_code = data.get('room_code')
        
        if not all([roll_number, room_code]):
            return jsonify({'success': False, 'message': 'Roll number and room code are required'}), 400
        
        # Check if student is logged in
        student = Student.query.filter_by(roll_number=roll_number, is_logged_in=True).first()
        if not student:
            return jsonify({'success': False, 'message': 'Student not logged in'}), 401
        
        # Check if room exists and is active
        room = Room.query.filter_by(room_code=room_code, active=True).first()
        if not room:
            return jsonify({'success': False, 'message': 'Room not found or inactive'}), 404
        
        if room.temporarily_closed:
            return jsonify({'success': False, 'message': 'Room is temporarily closed'}), 400
        
        # Check if student is a member of the room
        member = RoomMember.query.filter_by(room_code=room_code, roll_number=roll_number).first()
        if not member:
            return jsonify({'success': False, 'message': 'Student not registered for this room'}), 403
        
        # Check WiFi BSSID
        current_bssid = get_wifi_bssid()
        if room.bssid != current_bssid:
            return jsonify({
                'success': False, 
                'message': 'Not connected to correct WiFi network',
                'expected_bssid': room.bssid,
                'current_bssid': current_bssid
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Eligible for face verification',
            'member': {
                'roll_number': member.roll_number,
                'username': member.username,
                'status': member.status,
                'is_registered': member.is_registered
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/student/face/verify', methods=['POST'])
def verify_student_face():
    try:
        data = request.json
        roll_number = data.get('roll_number')
        room_code = data.get('room_code')
        face_image = data.get('face_image')
        
        if not all([roll_number, room_code, face_image]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        student = Student.query.filter_by(roll_number=roll_number).first()
        if not student:
            return jsonify({'success': False, 'message': 'Student not found'}), 404
        
        # Load stored face image
        if not student.face_image_path or not os.path.exists(student.face_image_path):
            return jsonify({'success': False, 'message': 'No registered face image found'}), 400
        
        stored_face = cv2.imread(student.face_image_path)
        
        # Extract current face
        current_face, error = extract_face(face_image)
        if current_face is None:
            return jsonify({'success': False, 'message': f'Face extraction failed: {error}'}), 400
        
        # Compare faces
        if compare_faces(stored_face, current_face):
            # Update student status
            current_time = datetime.now()
            student.current_room = room_code
            student.last_active_time = current_time
            student.is_active = True
            
            # Update room member status
            member = RoomMember.query.filter_by(room_code=room_code, roll_number=roll_number).first()
            if member:
                member.status = 'Present'
                member.is_registered = True
            
            # Create attendance record
            existing_record = AttendanceRecord.query.filter_by(
                roll_number=roll_number,
                room_code=room_code,
                logout_time=None
            ).first()
            
            if not existing_record:
                new_record = AttendanceRecord(
                    roll_number=roll_number,
                    room_code=room_code,
                    login_time=current_time
                )
                db.session.add(new_record)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Face verification successful',
                'status': 'Present'
            })
        else:
            return jsonify({'success': False, 'message': 'Face verification failed'}), 401
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/student/rooms/active', methods=['GET'])
def get_active_rooms():
    try:
        rooms = Room.query.filter_by(active=True, temporarily_closed=False).all()
        room_list = []
        
        for room in rooms:
            admin = Admin.query.get(room.admin_id)
            room_list.append({
                'room_code': room.room_code,
                'admin_name': admin.username if admin else 'Unknown',
                'created_at': room.created_at.strftime('%Y-%m-%d %H:%M'),
                'member_count': RoomMember.query.filter_by(room_code=room.room_code).count()
            })
        
        return jsonify({'success': True, 'rooms': room_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/student/activity', methods=['POST'])
def update_student_activity():
    try:
        data = request.json
        roll_number = data.get('roll_number')
        
        if not roll_number:
            return jsonify({'success': False, 'message': 'Roll number is required'}), 400
        
        student = Student.query.filter_by(roll_number=roll_number).first()
        if student:
            student.last_active_time = datetime.now()
            db.session.commit()
            
        return jsonify({'success': True, 'message': 'Activity updated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/student/logout', methods=['POST'])
def logout_student():
    try:
        data = request.json
        roll_number = data.get('roll_number')
        
        if not roll_number:
            return jsonify({'success': False, 'message': 'Roll number is required'}), 400
        
        student = Student.query.filter_by(roll_number=roll_number).first()
        if student:
            current_time = datetime.now()
            
            # Update student status
            room_code = student.current_room
            student.current_room = None
            student.is_logged_in = False
            student.is_active = False
            
            # Update room member status
            if room_code:
                member = RoomMember.query.filter_by(room_code=room_code, roll_number=roll_number).first()
                if member:
                    member.status = 'Not Present'
            
            # Update attendance record
            record = AttendanceRecord.query.filter_by(
                roll_number=roll_number,
                logout_time=None
            ).first()
            
            if record:
                record.logout_time = current_time
                if record.login_time:
                    duration = (current_time - record.login_time).total_seconds() / 60
                    record.active_duration = duration
            
            db.session.commit()
            
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/student/<roll_number>/attendance', methods=['GET'])
def get_student_attendance(roll_number):
    try:
        records = AttendanceRecord.query.filter_by(roll_number=roll_number).order_by(AttendanceRecord.login_time.desc()).all()
        attendance_list = []
        
        for record in records:
            attendance_list.append({
                'room_code': record.room_code,
                'login_time': record.login_time.strftime('%Y-%m-%d %H:%M:%S') if record.login_time else None,
                'logout_time': record.logout_time.strftime('%Y-%m-%d %H:%M:%S') if record.logout_time else None,
                'duration': f"{record.active_duration:.2f} minutes" if record.active_duration else 'Ongoing',
                'status': 'Complete' if record.logout_time else 'Ongoing'
            })
        
        return jsonify({'success': True, 'attendance': attendance_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Statistics Routes
@app.route('/api/admin/stats/<int:admin_id>', methods=['GET'])
def get_admin_stats(admin_id):
    try:
        total_rooms = Room.query.filter_by(admin_id=admin_id).count()
        active_rooms = Room.query.filter_by(admin_id=admin_id, active=True, temporarily_closed=False).count()
        
        admin_rooms = Room.query.filter_by(admin_id=admin_id).all()
        total_members = 0
        present_members = 0
        
        for room in admin_rooms:
            total_members += RoomMember.query.filter_by(room_code=room.room_code).count()
            present_members += RoomMember.query.filter_by(room_code=room.room_code, status='Present').count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_rooms': total_rooms,
                'active_rooms': active_rooms,
                'total_members': total_members,
                'present_members': present_members
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'success': False, 'message': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
