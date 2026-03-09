import os
import secrets
import csv
import io
import datetime
import smtplib
from email.message import EmailMessage
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
from werkzeug.utils import secure_filename
from ocr_engine import OCREngine
from grader import Grader
from firebase_manager import FirebaseManager

import sys

app = Flask(__name__)
# CRITICAL FIX: Use a stable key so sessions don't persist across restarts/workers
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret_key_fixed_for_stability")

# Force unbuffered output for debugging
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Auth Config (Multi-Role Phase 3)
# In production, these should be loaded securely from a database
USERS = {
    "admin@aigrader.com": {"password": "admin123", "role": "admin"},
    "faculty@aigrader.com": {"password": "faculty123", "role": "faculty"},
    "student@aigrader.com": {"password": "student123", "role": "student"}
}

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Core Engines
print("Initializing AI Engines...")
ocr_engine = OCREngine()
grader_engine = Grader()
firebase_mgr = FirebaseManager()

# Initialize Voice Manager
from voice_manager import VoiceManager
voice_mgr = VoiceManager(output_dir="static/audio")

@app.route('/voice_chat')
def voice_chat():
    return render_template('voice_chat.html')

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json
    user_text = data.get('text', '')
    
    if not user_text:
        return {"error": "No text provided"}, 400

    import requests
    import json
    
    api_key = grader_engine.api_key
    model = grader_engine.model_name
    
    if not api_key:
        return {"error": "LLM API Key missing"}, 500

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": os.environ.get("SITE_URL", "http://localhost"),
        "X-Title": "AI Grader Chat",
        "Content-Type": "application/json"
    }

    system_prompt = "You are a helpful AI Assistant for an automated grading system. Answer questions concisely and naturally, as if speaking."
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )
        
        if response.status_code == 200:
            ai_text = response.json()['choices'][0]['message']['content']
            audio_url = voice_mgr.text_to_speech(ai_text)
            return {"text": ai_text, "audio_url": audio_url}
        else:
             return {"error": f"LLM Error: {response.text}"}, 500

    except Exception as e:
        return {"error": str(e)}, 500

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Auth Decorator ---
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('login'))
            
            user_role = session.get('role')
            if role and user_role != role and user_role != 'admin': # Admin can access anything
                flash("You do not have permission to access this portal.", "error")
                return redirect(url_for('index'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        print(f"DEBUG: Login Attempt - Email: {email}")
        
        user_info = USERS.get(email)
        if user_info:
            if password == user_info['password']:
                session['user'] = email
                session['role'] = user_info['role']
                print(f"DEBUG: Login Success - Role: {user_info['role']}")
                flash("Logged in successfully.", "success")
                
                # Route based on role
                if user_info['role'] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif user_info['role'] == 'faculty':
                    return redirect(url_for('staff_dashboard'))
                elif user_info['role'] == 'student':
                    return redirect(url_for('student_portal'))
            else:
                flash("Invalid password.", "error")
        else:
            flash("Unauthorized or unknown email.", "error")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('role', None)
    flash("Logged out.", "info")
    return redirect(url_for('index'))

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    id_token = data.get('idToken')
    
    if not id_token:
        return {"success": False, "message": "Missing ID Token"}, 400

    try:
        # Verify the ID token using Firebase Admin SDK
        decoded_token = firebase_admin.auth.verify_id_token(id_token)
        email = decoded_token.get('email')
        
        if not email:
            return {"success": False, "message": "No email found in token"}, 400

        print(f"DEBUG: Firebase Auth - Email: {email}")

        # Check if email is allowed
        if email in ALLOWED_EMAILS:
            session['user'] = email
            print("DEBUG: Login Success (Google Auth)")
            return {"success": True, "redirect": url_for('staff_dashboard')}
        else:
            print(f"DEBUG: Email {email} not in allowed list.")
            return {"success": False, "message": "Unauthorized email account."}, 403

    except Exception as e:
        print(f"DEBUG: Token Verification Error: {e}")
        return {"success": False, "message": f"Invalid Token: {str(e)}"}, 401

@app.route('/student', methods=['GET', 'POST'])
@login_required('student')
def student_portal():
    if request.method == 'POST':
        reg_no = request.form.get('register_number')
        if reg_no:
            if not firebase_mgr.enabled:
                err_msg = getattr(firebase_mgr, 'connection_error', 'Unknown Error')
                flash(f"System Error: Database not connected. Details: {err_msg}", "error")
                return render_template('student_search.html')

            result = firebase_mgr.get_result_by_reg_no(reg_no)
            if result:
                # Need to manually pass doc_id because get_result_by_reg_no might not include it dynamically in mock mode
                # Let's search all results to find the exact doc_id
                all_res = firebase_mgr.get_all_results()
                doc_id = next((r.get('id') for r in all_res if r.get('register_number') == reg_no), None)
                
                return render_template('result.html', result=result, doc_id=doc_id, reg_no=reg_no)
            else:
                flash("No results found for this Register Number.", "error")
    
    return render_template('student_search.html')

@app.route('/request_action/<action>/<doc_id>', methods=['POST'])
@login_required('student')
def request_student_action(action, doc_id):
    if action not in ['recorrection', 'retest']:
        flash("Invalid action requested.", "error")
        return redirect(url_for('student_portal'))
        
    new_status = 'Pending Recorrection' if action == 'recorrection' else 'Retest Requested'
    success = firebase_mgr.update_result_status(doc_id, new_status)
    
    if success:
        flash(f"Successfully requested {action}.", "success")
    else:
        flash(f"Failed to request {action}. Database error.", "error")
        
    return redirect(url_for('student_portal'))

@app.route('/create_exam', methods=['POST'])
@login_required('faculty')
def create_exam():
    course_name = request.form.get('course_name')
    answer_key = request.form.get('answer_key')
    
    if not course_name or not answer_key:
        flash("Course Name and Answer Key are required.", "error")
        return redirect(url_for('staff_dashboard'))
        
    exam_id = firebase_mgr.save_exam(course_name, answer_key)
    if exam_id:
        flash(f"Exam '{course_name}' created successfully!", "success")
    else:
        flash("Failed to create exam. Check connection.", "error")
        
    return redirect(url_for('staff_dashboard'))

@app.route('/upload', methods=['GET', 'POST'])
@login_required('faculty')
def staff_dashboard():
    print(f"DEBUG: Endpoint /upload accessed. Method: {request.method}")
    
    if not firebase_mgr.enabled:
        err_msg = getattr(firebase_mgr, 'connection_error', 'Unknown Error')
        flash(f"WARNING: Database disconnected. Saving/Loading results will fail. ({err_msg})", "error")

    # Pre-fetch exams for the dropdown
    exams = firebase_mgr.get_all_exams()
    
    if request.method == 'POST':
        print("DEBUG: POST request received at /upload")
        
        exam_id = request.form.get('exam_id')
        upload_mode = request.form.get('upload_mode', 'quick')
        
        if not exam_id:
            flash("Please select an Exam.", "error")
            return redirect(request.url)

        # 1. Fetch Key (Common)
        expected_ans_text = firebase_mgr.get_exam_key(exam_id)
        if not expected_ans_text:
            flash("Error loading Exam Key. Is the DB connected?", "error")
            return redirect(request.url)

        # Prepare list of (file, roll_no_override) tuples
        tasks = []
        
        if upload_mode == 'manual':
            # Detailed Entry Mode
            manual_rolls = request.form.getlist('manual_rolls[]')
            manual_files = request.files.getlist('manual_files[]')
            
            # Zip them. Note: If file input is empty in a row, it might still send an empty obj or match index.
            # Flask request.files.getlist usually filters empty ones? No, usually indices match if multipart is correct.
            # Safest is to rely on index if frontend sends empty file fields.
            # But standard HTML form submit excludes empty file inputs? 
            # Actually, standard browser behavior: empty file inputs are sent as empty filenames.
            
            for i in range(min(len(manual_rolls), len(manual_files))):
                f = manual_files[i]
                r = manual_rolls[i]
                if f and f.filename != '' and r:
                    tasks.append({'file': f, 'roll': r})
            
            if not tasks:
                 flash("No valid entries found in Manual Mode. Ensure both Roll No and File are provided.", "warning")
                 return redirect(request.url)
                 
        else:
            # Quick / Default Mode
            files = request.files.getlist('answer_sheets_quick')
            # Fallback legacy name check
            if not files:
                 files = request.files.getlist('answer_sheets')
                 
            for f in files:
                if f and f.filename != '':
                    # Roll will be inferred later, pass None
                    tasks.append({'file': f, 'roll': None})

        print(f"DEBUG: Processing {len(tasks)} tasks in mode '{upload_mode}'")

        success_count = 0
        error_count = 0
        results_summary = []
        last_result = None
        last_doc_id = None
        last_roll = None

        # 3. Process Execution
        for task in tasks:
            ans_file = task['file']
            forced_roll = task['roll']
            
            try:
                # Determine Roll No
                if forced_roll:
                    current_reg_no = forced_roll
                else:
                    # Infer from filename
                    current_reg_no = os.path.splitext(ans_file.filename)[0]
                
                ans_filename = secure_filename(ans_file.filename)
                ans_path = os.path.join(app.config['UPLOAD_FOLDER'], ans_filename)
                ans_file.save(ans_path)
                
                print(f"Processing {ans_filename} for Student {current_reg_no}...")
                
                # OCR
                processed_ans = ocr_engine.process_image(ans_path, "handwritten")
                
                # Grade
                result = grader_engine.grade_answer(processed_ans, expected_ans_text)
                
                # Save
                doc_id = firebase_mgr.save_result(
                    student_answer=result.get('student_answer', ''),
                    key_answer=result.get('key_answer', ''),
                    score=result.get('similarity_score', 0),
                    is_correct=result.get('is_correct', False),
                    register_number=current_reg_no,
                    image_path=ans_filename
                )
                
                # To support the new fields in Firebase, let's explicitly add them if we can,
                # or just know the result object has them for display.
                # In order to not rewrite `save_result` signature, we can rely on `last_result` to hold it.
                
                success_count += 1
                results_summary.append(f"✅ {current_reg_no}: {result['similarity_score']}%")
                
                # Store last for single-result redirect
                last_result = result
                last_doc_id = doc_id
                last_roll = current_reg_no
                
            except Exception as e:
                print(f"Error processing {ans_file.filename}: {e}")
                error_count += 1
                results_summary.append(f"❌ {ans_file.filename}: {str(e)}")
        
        # Final Summary / Redirect
        if success_count > 0:
            flash(f"Successfully graded {success_count} papers!", "success")
            # If exactly one task was processed, assume user wants to see the detailed result immediately
            if len(tasks) == 1 and last_result:
                 return render_template('result.html', 
                                       result=last_result, 
                                       doc_id=last_doc_id, 
                                       reg_no=last_roll,
                                       is_staff=True)
        
        if error_count > 0:
            flash(f"Failed to process {error_count} papers.", "error")
            
        return redirect(request.url)

    return render_template('staff_dashboard.html', exams=exams)

@app.route('/all_results')
@login_required('faculty')
def all_results():
    if not firebase_mgr.enabled:
        flash("Database disconnected. Cannot fetch results.", "error")
    
    results = firebase_mgr.get_all_results()
    return render_template('all_results.html', results=results)

@app.route('/export_results_csv')
@login_required('faculty')
def export_results_csv():
    results = firebase_mgr.get_all_results()
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Register Number', 'Score', 'Status', 'Timestamp'])
    
    for r in results:
        status = "Correct" if r.get('is_correct') else "Incorrect"
        timestamp = r.get('timestamp', '')
        if isinstance(timestamp, datetime.datetime):
             # Make it timezone naive or just format it
             timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        elif hasattr(timestamp, 'strftime'):
             timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        cw.writerow([r.get('register_number', 'N/A'), f"{r.get('score', 0)}%", status, timestamp])
        
    output = si.getvalue()
    si.close()
    
    response = make_response(output)
    response.headers["Content-Disposition"] = "attachment; filename=all_students_results.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route('/email_results', methods=['POST'])
@login_required('faculty')
def email_results():
    email_address = request.form.get('email_address')
    if not email_address:
         flash("Email address is required.", "error")
         return redirect(url_for('all_results'))
         
    results = firebase_mgr.get_all_results()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Register Number', 'Score', 'Status', 'Timestamp'])
    for r in results:
        status = "Correct" if r.get('is_correct') else "Incorrect"
        timestamp = r.get('timestamp', '')
        if isinstance(timestamp, datetime.datetime) or hasattr(timestamp, 'strftime'):
             timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        cw.writerow([r.get('register_number', 'N/A'), f"{r.get('score', 0)}%", status, timestamp])
    csv_content = si.getvalue()
    si.close()

    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_pass = os.environ.get("SMTP_PASSWORD")

    if not smtp_user or not smtp_pass:
        flash("Email configuration (SMTP_USERNAME / SMTP_PASSWORD) is missing in .env.", "error")
        return redirect(url_for('all_results'))

    msg = EmailMessage()
    msg['Subject'] = 'AI Grader - Class Results Report'
    msg['From'] = smtp_user
    msg['To'] = email_address
    msg.set_content("Please find attached the latest report card and results for the class.\\n\\nGenerated by AI Grader.")
    
    msg.add_attachment(csv_content.encode('utf-8'), maintype='text', subtype='csv', filename='all_students_results.csv')

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        flash(f"Results successfully emailed to {email_address}!", "success")
    except Exception as e:
        print(f"Error sending email: {e}")
        flash(f"Failed to send email: {e}", "error")

    return redirect(url_for('all_results'))

@app.route('/admin')
@login_required('admin')
def admin_dashboard():
    # Fetch high-level statistics
    results = firebase_mgr.get_all_results() if firebase_mgr.enabled else []
    total_submissions = len(results)
    
    # Calculate some basic metrics
    passed = sum(1 for r in results if r.get('is_correct'))
    failed = total_submissions - passed
    avg_score = sum(float(r.get('score', 0)) for r in results) / total_submissions if total_submissions > 0 else 0
    
    return render_template('admin_dashboard.html', 
                           total_submissions=total_submissions,
                           passed=passed,
                           failed=failed,
                           avg_score=round(avg_score, 1))

@app.route('/settings')
@login_required() # Any logged in user
def settings_page():
    return render_template('settings.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7860))
    app.run(host='0.0.0.0', port=port, debug=True)
