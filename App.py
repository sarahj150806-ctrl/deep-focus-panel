from flask import Flask, render_template, request, jsonify, session
import time
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'matrix_secret_protocol_99x'

# IN-MEMORY STORAGE
users = []  
tasks = []  

def parse_flexible_time(raw_time_str):
    """Cleans time text patterns safely"""
    if not raw_time_str: return None
    return raw_time_str.strip().upper()

# --- IDENTITY VERIFICATION API ENDPOINTS ---

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    if 'user_id' in session:
        return jsonify({"logged_in": True, "username": session['username']})
    return jsonify({"logged_in": False})

@app.route('/api/auth/register', methods=['POST'])
def register():
    global users
    data = request.json or {}
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"success": False, "message": "Missing credentials"}), 400

    for u in users:
        if u['username'] == username:
            return jsonify({"success": False, "message": "Username already taken!"}), 400
    
    user_id = int(time.time())
    new_user = {
        "id": user_id,
        "username": username,
        "password": generate_password_hash(password)
    }
    users.append(new_user)
    
    session['user_id'] = user_id
    session['username'] = username
    return jsonify({"success": True})

@app.route('/api/auth/login', methods=['POST'])
def login():
    global users
    data = request.json or {}
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')

    for u in users:
        if u['username'] == username and check_password_hash(u['password'], password):
            session['user_id'] = u['id']
            session['username'] = u['username']
            return jsonify({"success": True})
            
    return jsonify({"success": False, "message": "Invalid username or password."}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

# --- WEB SERVER ROUTES ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    if 'user_id' not in session:
        return jsonify([]), 401
    user_tasks = [t for t in tasks if t.get('user_id') == session['user_id']]
    return jsonify(user_tasks)

@app.route('/api/tasks', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.json or {}
    
    new_task = {
        "id": int(time.time()),
        "user_id": session['user_id'],
        "title": data.get('title'),
        "priority": data.get('priority', 'Medium'),
        "category": data.get('category', 'School'),
        "startTime": parse_flexible_time(data.get('startTime')),
        "endTime": parse_flexible_time(data.get('endTime')),
        "completed": False,
        "startRung": False,
        "endRung": False
    }
    tasks.append(new_task)
    return jsonify({"success": True, "task": new_task})

@app.route('/api/tasks/<int:task_id>/action', methods=['POST'])
def task_action(task_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    global tasks
    data = request.json or {}
    action = data.get('action') 
    
    for idx, task in enumerate(tasks):
        if task['id'] == task_id and task.get('user_id') == session['user_id']:
            if action == "complete":
                task['completed'] = True
                return jsonify({"success": True})
                
            elif action == "mark_start_rung":
                task['startRung'] = True
                return jsonify({"success": True})
                
            elif action == "mark_end_rung":
                task['endRung'] = True
                return jsonify({"success": True})
                
            elif action == "extend":
                task['endTime'] = parse_flexible_time(data.get('newTime'))
                task['endRung'] = False 
                return jsonify({"success": True})
            break
            
    return jsonify({"success": True})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    global tasks
    tasks = [t for t in tasks if not (t['id'] == task_id and t.get('user_id') == session['user_id'])]
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)