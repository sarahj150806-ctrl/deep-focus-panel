from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
import datetime
import time
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Typing hints to make VS Code's red lines go away
from typing import Type

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'matrix_secret_protocol_99x')

# Fallback to local sqlite if DATABASE_URL isn't found locally during testing
db_url = os.environ.get('DATABASE_URL', 'sqlite:///local_fallback.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- DATABASE MODELS ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    tasks = db.relationship('Task', backref='owner', lazy=True)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    startTime = db.Column(db.String(50), nullable=False)
    endTime = db.Column(db.String(50), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    startAlertTriggered = db.Column(db.Boolean, default=False)
    endAlertTriggered = db.Column(db.Boolean, default=False)

# Auto-build tables inside the cloud instance
with app.app_context():
    db.create_all()

def parse_flexible_time(raw_time_str):
    if not raw_time_str: 
        return None
    cleaned = raw_time_str.strip().upper()
    try:
        return datetime.datetime.strptime(cleaned, "%I:%M %p").strftime("%I:%M %p")
    except ValueError:
        pass
    try:
        return datetime.datetime.strptime(cleaned, "%H:%M").strftime("%I:%M %p")
    except ValueError:
        return None

# --- AUTHENTICATION API ENDPOINTS ---
@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    if 'user_id' in session:
        return jsonify({"logged_in": True, "username": session['username']})
    return jsonify({"logged_in": False})

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"success": False, "message": "Missing credentials"}), 400

    hashed_password = generate_password_hash(password)
    
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"success": False, "message": "Username already taken!"}), 400
    
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    session['user_id'] = new_user.id
    session['username'] = new_user.username
    return jsonify({"success": True})

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        session['username'] = user.username
        return jsonify({"success": True})
    
    return jsonify({"success": False, "message": "Invalid username or password."}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})


# --- CORE TASK API ENDPOINTS ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    if 'user_id' not in session:
        return jsonify([]), 401
        
    tasks = Task.query.filter_by(user_id=session['user_id']).all()
    tasks_list = []
    for t in tasks:
        tasks_list.append({
            "id": t.id,
            "title": t.title,
            "priority": t.priority,
            "category": t.category,
            "startTime": t.startTime,
            "endTime": t.endTime,
            "completed": t.completed,
            "startAlertTriggered": t.startAlertTriggered,
            "endAlertTriggered": t.endAlertTriggered
        })
    return jsonify(tasks_list)

@app.route('/api/tasks', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.json
    start_parsed = parse_flexible_time(data.get('startTime'))
    end_parsed = parse_flexible_time(data.get('endTime'))
    
    if not start_parsed or not end_parsed:
        return jsonify({"success": False, "message": "❌ Invalid time format syntax!"}), 400

    task_id = int(time.time())
    
    new_task = Task(
        id=task_id,
        user_id=session['user_id'],
        title=data.get('title'),
        priority=data.get('priority', 'Medium'),
        category=data.get('category', 'School'),
        startTime=start_parsed,
        endTime=end_parsed
    )
    db.session.add(new_task)
    db.session.commit()

    return jsonify({"success": True})

@app.route('/api/tasks/<int:task_id>/action', methods=['POST'])
def task_action(task_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.json
    action = data.get('action') 
    
    task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first()
    if not task:
        return jsonify({"success": False, "message": "Task not found"}), 404

    if action == "complete":
        task.completed = True
        db.session.commit()
        return jsonify({"success": True})
    
    elif action == "mark_start_triggered":
        task.startAlertTriggered = True
        db.session.commit()
        return jsonify({"success": True})
    
    elif action == "mark_end_triggered":
        task.endAlertTriggered = True
        db.session.commit()
        return jsonify({"success": True})
    
    elif action == "extend":
        try:
            minutes_to_add = int(data.get('minutes', 10))
        except:
            minutes_to_add = 10
            
        scope = data.get('scope', 'only_this')
        
        try:
            old_end_obj = datetime.datetime.strptime(task.endTime, "%I:%M %p")
            new_end_obj = old_end_obj + datetime.timedelta(minutes=minutes_to_add)
            task.endTime = new_end_obj.strftime("%I:%M %p")
            task.endAlertTriggered = False
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
        
        if scope in ['all', 'subsequent']:
            all_tasks = Task.query.filter_by(user_id=session['user_id']).order_by(Task.id.asc()).all()
            target_idx = -1
            for idx, t in enumerate(all_tasks):
                if t.id == task_id:
                    target_idx = idx
                    break

            for shift_idx, t in enumerate(all_tasks):
                if t.completed: 
                    continue
                if scope == 'subsequent' and shift_idx <= target_idx: 
                    continue
                if scope == 'all' and t.id == task_id: 
                    continue

                def shift_time_str(time_str, mins):
                    if not time_str: return time_str
                    t_obj = datetime.datetime.strptime(time_str, "%I:%M %p")
                    return (t_obj + datetime.timedelta(minutes=mins)).strftime("%I:%M %p")

                t.startTime = shift_time_str(t.startTime, minutes_to_add)
                t.endTime = shift_time_str(t.endTime, minutes_to_add)
                t.startAlertTriggered = False
                t.endAlertTriggered = False

        db.session.commit()
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "Invalid Action"}), 400

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first()
    if task:
        db.session.delete(task)
        db.session.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)