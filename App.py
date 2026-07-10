from flask import Flask, render_template, request, jsonify, session
import datetime
import time
import threading
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Secure encryption key for user sessions
app.secret_key = 'matrix_secret_protocol_99x'

# --- IN-MEMORY DATABASE ARRAYS ---
users = []  # Stores user profile dictionary objects
tasks = []  # Stores task dictionary objects with user association links

def trigger_task_alarm():
    """Background monitoring loop synchronized to Indian Standard Time (IST)"""
    global tasks
    while True:
        # Calculate UTC time, then manually add 5 hours and 30 minutes for IST
        utc_now = datetime.datetime.utcnow()
        ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
        now_str = ist_now.strftime("%I:%M %p")
        
        for task in tasks:
            # 1. Check Start Alarm
            if task.get('startTime') and not task.get('startRung'):
                if now_str == task['startTime']:
                    task['startRung'] = True
                    task['triggerStartAlert'] = True  

            # 2. Check Finish Alarm
            if task.get('endTime') and not task.get('endRung'):
                if now_str == task['endTime']:
                    task['endRung'] = True
                    task['triggerEndAlert'] = True  
        time.sleep(2)

def parse_flexible_time(raw_time_str):
    """Converts 24h or 12h inputs safely into standard '03:00 PM' string format"""
    if not raw_time_str: return None
    cleaned = raw_time_str.strip().upper()
    try:
        return datetime.datetime.strptime(cleaned, "%I:%M %p").strftime("%I:%M %p")
    except ValueError:
        pass
    try:
        return datetime.datetime.strptime(cleaned, "%H:%M").strftime("%I:%M %p")
    except ValueError:
        return None


# --- IDENTITY VERIFICATION API ENDPOINTS ---

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Checks if the client tab holds an active profile signature"""
    if 'user_id' in session:
        return jsonify({"logged_in": True, "username": session['username']})
    return jsonify({"logged_in": False})

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Registers a brand new account identity and securely hashes passwords"""
    global users
    data = request.json or {}
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"success": False, "message": "Missing credentials"}), 400

    # Ensure uniqueness
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
    """Validates login credentials against existing identity hashes"""
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
    """Clears out the active browser session layer"""
    session.clear()
    return jsonify({"success": True})


# --- WEB SERVER ROUTES (SECURED WITH USER SESSIONS) ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    if 'user_id' not in session:
        return jsonify([]), 401
    
    # ONLY return tasks owned by the currently logged-in user
    user_tasks = [t for t in tasks if t.get('user_id') == session['user_id']]
    return jsonify(user_tasks)

@app.route('/api/tasks', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.json or {}
    start_parsed = parse_flexible_time(data.get('startTime'))
    end_parsed = parse_flexible_time(data.get('endTime'))
    
    if not start_parsed or not end_parsed:
        return jsonify({
            "success": False, 
            "message": "❌ Invalid time format! Use standard patterns like '15:30' or '3:00 PM'."
        }), 400

    new_task = {
        "id": int(time.time()),
        "user_id": session['user_id'],  # Lock task to this specific user profile
        "title": data.get('title'),
        "priority": data.get('priority', 'Medium'),
        "category": data.get('category', 'School'),
        "startTime": start_parsed,
        "endTime": end_parsed,
        "completed": False,
        "startRung": False,
        "endRung": False,
        "triggerStartAlert": False,
        "triggerEndAlert": False
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
        # Ensure task matches ID and belongs to the authenticated user session
        if task['id'] == task_id and task.get('user_id') == session['user_id']:
            if action == "complete":
                task['completed'] = True
                return jsonify({"success": True})
                
            elif action == "clear_start_alert":
                task['triggerStartAlert'] = False  
                return jsonify({"success": True})
                
            elif action == "clear_end_alert":
                task['triggerEndAlert'] = False    
                return jsonify({"success": True})
                
            elif action == "extend":
                new_time_str = parse_flexible_time(data.get('newTime'))
                scope = data.get('scope', 'only_this')
                
                if not new_time_str:
                    return jsonify({"success": False, "message": "Invalid time syntax"}), 400
                
                try:
                    old_end = datetime.datetime.strptime(task['endTime'], "%I:%M %p")
                    new_end = datetime.datetime.strptime(new_time_str, "%I:%M %p")
                    delta = new_end - old_end
                    delta_minutes = int(delta.total_seconds() / 60)
                except Exception as e:
                    return jsonify({"success": False, "message": "Error processing time delta"}), 500

                task['endTime'] = new_time_str
                task['endRung'] = False 
                task['triggerEndAlert'] = False
                
                if scope in ['all', 'subsequent']:
                    for shift_idx, t in enumerate(tasks):
                        # Ensure we are only shifting tasks belonging to THIS specific user
                        if t['completed'] or t.get('user_id') != session['user_id']:
                            continue
                            
                        if scope == 'subsequent' and shift_idx <= idx:
                            continue
                            
                        if scope == 'all' and t['id'] == task_id:
                            continue

                        def shift_time(time_str, mins):
                            if not time_str: return time_str
                            t_obj = datetime.datetime.strptime(time_str, "%I:%M %p")
                            return (t_obj + datetime.timedelta(minutes=mins)).strftime("%I:%M %p")

                        t['startTime'] = shift_time(t.get('startTime'), delta_minutes)
                        t['endTime'] = shift_time(t.get('endTime'), delta_minutes)
                        t['startRung'] = False
                        t['endRung'] = False

                return jsonify({"success": True})
            break
            
    return jsonify({"success": True})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    global tasks
    # Filter list ensuring users can't delete another user's task
    tasks = [t for t in tasks if not (t['id'] == task_id and t.get('user_id') == session['user_id'])]
    return jsonify({"success": True})

if __name__ == '__main__':
    # Start the fixed daemon tracking thread background layer
    threading.Thread(target=trigger_task_alarm, daemon=True).start()
    app.run(debug=True, port=5000)