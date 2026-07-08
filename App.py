from flask import Flask, render_template, request, jsonify
import datetime
import time
import threading

app = Flask(__name__)

# Task storage list database
tasks = []

def trigger_task_alarm():
    """Background monitoring loop running every 2 seconds"""
    global tasks
    while True:
        now_str = datetime.datetime.now().strftime("%I:%M %p")
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

# --- WEB SERVER ROUTES ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    return jsonify(tasks)

@app.route('/api/tasks', methods=['POST'])
def add_task():
    data = request.json
    start_parsed = parse_flexible_time(data.get('startTime'))
    end_parsed = parse_flexible_time(data.get('endTime'))
    
    if not start_parsed or not end_parsed:
        return jsonify({
            "success": False, 
            "message": "❌ Invalid time format! Use standard patterns like '15:30' or '3:00 PM'."
        }), 400

    new_task = {
        "id": int(time.time()),
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
    global tasks
    data = request.json
    action = data.get('action') 
    
    for idx, task in enumerate(tasks):
        if task['id'] == task_id:
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
                scope = data.get('scope', 'only_this') # 'only_this', 'all', or 'subsequent'
                
                if not new_time_str:
                    return jsonify({"success": False, "message": "Invalid time syntax"}), 400
                
                # Calculate time extension delta in minutes
                try:
                    old_end = datetime.datetime.strptime(task['endTime'], "%I:%M %p")
                    new_end = datetime.datetime.strptime(new_time_str, "%I:%M %p")
                    delta = new_end - old_end
                    delta_minutes = int(delta.total_seconds() / 60)
                except Exception as e:
                    return jsonify({"success": False, "message": "Error processing time delta"}), 500

                # Target task modification
                task['endTime'] = new_time_str
                task['endRung'] = False 
                task['triggerEndAlert'] = False
                
                # Apply cascading delay to other items if requested
                if scope in ['all', 'subsequent']:
                    for shift_idx, t in enumerate(tasks):
                        # Skip completed tasks
                        if t['completed']:
                            continue
                            
                        # 'subsequent' only delays items created *after* the current index in the list
                        if scope == 'subsequent' and shift_idx <= idx:
                            continue
                            
                        # 'all' delays everything except the task we just explicitly updated
                        if scope == 'all' and t['id'] == task_id:
                            continue

                        # Helper function to shift a standard string time by X minutes
                        def shift_time(time_str, mins):
                            if not time_str: return time_str
                            t_obj = datetime.datetime.strptime(time_str, "%I:%M %p")
                            return (t_obj + datetime.timedelta(minutes=mins)).strftime("%I:%M %p")

                        t['startTime'] = shift_time(t.get('startTime'), delta_minutes)
                        t['endTime'] = shift_time(t.get('endTime'), delta_minutes)
                        # Reset tracking flags so updated timelines alert normally
                        t['startRung'] = False
                        t['endRung'] = False

                return jsonify({"success": True})
            break
            
    return jsonify({"success": True})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    global tasks
    tasks = [t for t in tasks if t['id'] != task_id]
    return jsonify({"success": True})

if __name__ == '__main__':
    threading.Thread(target=trigger_task_alarm, daemon=True).start()
    app.run(debug=True, port=5000)