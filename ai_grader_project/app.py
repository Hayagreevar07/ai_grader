import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'question_paper' not in request.files or 'answer_sheet' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        qp_file = request.files['question_paper']
        ans_file = request.files['answer_sheet']
        expected_ans_text = request.form.get('expected_answer')

        if qp_file.filename == '' or ans_file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if qp_file and allowed_file(qp_file.filename) and ans_file and allowed_file(ans_file.filename):
            qp_filename = secure_filename(qp_file.filename)
            ans_filename = secure_filename(ans_file.filename)
            
            qp_path = os.path.join(app.config['UPLOAD_FOLDER'], qp_filename)
            ans_path = os.path.join(app.config['UPLOAD_FOLDER'], ans_filename)
            
            qp_file.save(qp_path)
            ans_file.save(ans_path)

            # --- PROCESS ---
            # 1. OCR
            print("Processing Images...")
            # For simplicity in this demo, we might rely on the form for expected answer 
            # OR process the QP to find it. Here we trust the form or process QP if needed.
            
            # processed_qp = ocr_engine.process_image(qp_path, "printed") 
            processed_ans = ocr_engine.process_image(ans_path, "handwritten")

            # 2. Grade
            result = grader_engine.grade_answer(processed_ans, expected_ans_text)
            
            # 3. Save to Cloud
            doc_id = firebase_mgr.save_result(
                student_answer=result['student_answer'],
                key_answer=result['key_answer'],
                score=result['similarity_score'],
                is_correct=result['is_correct']
            )

            return render_template('result.html', 
                                   result=result, 
                                   doc_id=doc_id, 
                                   qp_image=qp_filename,
                                   ans_image=ans_filename)

    return render_template('upload.html')

@app.route('/view/<doc_id>')
def view_result(doc_id):
    data = firebase_mgr.get_result(doc_id)
    if not data:
        return "Result not found", 404
    
    # Reconstruct result dict for template compatibility
    result = {
        'student_answer': data.get('student_answer'),
        'key_answer': data.get('key_answer'),
        'similarity_score': data.get('score'),
        'is_correct': data.get('is_correct')
    }
    
    return render_template('result.html', result=result, doc_id=doc_id, view_only=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7860)) # Default to 7860 for HF Spaces
    app.run(host='0.0.0.0', port=port)
