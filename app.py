import os
import secrets
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
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

# Auth Config (Environment Variables)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")  # Fallback for dev
# Split by comma and strip whitespace from each email
ALLOWED_EMAILS = [e.strip() for e in os.environ.get("ALLOWED_EMAILS", "admin@example.com").split(',')]

print(f"DEBUG: Allowed Emails: {ALLOWED_EMAILS}")
print(f"DEBUG: Admin Password Configured: {'Yes' if ADMIN_PASSWORD else 'No'}")

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Core Engines
print("Initializing AI Engines...")
ocr_engine = OCREngine()
grader_engine = Grader()
firebase_mgr = FirebaseManager()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Auth Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            print("DEBUG: Access Denied. No user in session. Redirecting to login.")
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        print(f"DEBUG: Access Granted for user: {session['user']}")
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"DEBUG: Login Attempt - Email: {email}")
        
        if email in ALLOWED_EMAILS:
            if password == ADMIN_PASSWORD:
                session['user'] = email
                print("DEBUG: Login Success")
                flash("Logged in successfully.", "success")
                return redirect(url_for('staff_dashboard'))
            else:
                print("DEBUG: Password Mismatch")
                flash("Invalid password.", "error")
        else:
            print(f"DEBUG: Email {email} not in allowed list.")
            flash("Unauthorized email.", "error")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
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
def student_search():
    if request.method == 'POST':
        reg_no = request.form.get('register_number')
        if reg_no:
            result = firebase_mgr.get_result_by_reg_no(reg_no)
            if result:
                return render_template('result.html', result=result, reg_no=reg_no)
            else:
                flash("No results found for this Register Number.", "error")
    
    return render_template('student_search.html')

@app.route('/create_exam', methods=['POST'])
# @login_required
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
# @login_required  <-- DISABLED AUTHENTICATION
def staff_dashboard():
    print(f"DEBUG: Endpoint /upload accessed. Method: {request.method}")
    
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
                    student_answer=result['student_answer'],
                    key_answer=result['key_answer'],
                    score=result['similarity_score'],
                    is_correct=result['is_correct'],
                    register_number=current_reg_no,
                    image_path=ans_filename
                )
                
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7860))
    app.run(host='0.0.0.0', port=port)
