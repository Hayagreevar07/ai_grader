import os
import secrets
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from ocr_engine import OCREngine
from grader import Grader
from firebase_manager import FirebaseManager

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Auth Config (Environment Variables)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")  # Fallback for dev
ALLOWED_EMAILS = os.environ.get("ALLOWED_EMAILS", "admin@example.com").split(',')

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
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
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
        
        if email in ALLOWED_EMAILS and password == ADMIN_PASSWORD:
            session['user'] = email
            flash("Logged in successfully.", "success")
            return redirect(url_for('staff_dashboard'))
        else:
            flash("Invalid credentials or unauthorized email.", "error")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out.", "info")
    return redirect(url_for('index'))

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

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def staff_dashboard():
    if request.method == 'POST':
        if 'question_paper' not in request.files or 'answer_sheet' not in request.files:
            flash('No file part', "error")
            return redirect(request.url)
        
        qp_file = request.files['question_paper']
        ans_file = request.files['answer_sheet']
        reg_no = request.form.get('register_number') # Required
        expected_ans_text = request.form.get('expected_answer')

        if qp_file.filename == '' or ans_file.filename == '':
            flash('No selected file', "error")
            return redirect(request.url)

        if not reg_no:
            flash('Register Number is required!', "error")
            return redirect(request.url)

        if qp_file and allowed_file(qp_file.filename) and ans_file and allowed_file(ans_file.filename):
            qp_filename = secure_filename(qp_file.filename)
            ans_filename = secure_filename(ans_file.filename)
            
            qp_path = os.path.join(app.config['UPLOAD_FOLDER'], qp_filename)
            ans_path = os.path.join(app.config['UPLOAD_FOLDER'], ans_filename)
            
            qp_file.save(qp_path)
            ans_file.save(ans_path)

            # --- PROCESS ---
            try:
                # 1. OCR (Assuming we just need the answer for now, but in real app we'd process QP too)
                print("Processing Images...")
                # processed_qp = ocr_engine.process_image(qp_path, "printed") 
                processed_ans = ocr_engine.process_image(ans_path, "handwritten")

                # 2. Grade
                result = grader_engine.grade_answer(processed_ans, expected_ans_text)
                
                # 3. Save to Cloud
                doc_id = firebase_mgr.save_result(
                    student_answer=result['student_answer'],
                    key_answer=result['key_answer'],
                    score=result['similarity_score'],
                    is_correct=result['is_correct'],
                    register_number=reg_no
                )

                flash("Paper Graded Successfully!", "success")
                return render_template('result.html', 
                                       result=result, 
                                       doc_id=doc_id, 
                                       reg_no=reg_no,
                                       is_staff=True) # Staff view might have more options
            except Exception as e:
                flash(f"An error occurred during processing: {e}", "error")
                return redirect(request.url)

    return render_template('staff_dashboard.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7860))
    app.run(host='0.0.0.0', port=port)
