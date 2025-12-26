import firebase_admin
from firebase_admin import credentials, firestore
import os
import datetime

import json

class FirebaseManager:
    def __init__(self, cred_path="serviceAccountKey.json"):
        self.db = None
        self.enabled = False
        
        # Check for environment variable first (Cloud Deployment)
        firebase_json = os.environ.get("FIREBASE_CREDENTIALS")

        if firebase_json:
            try:
                print("Found FIREBASE_CREDENTIALS env var. Initializing...")
                cred_dict = json.loads(firebase_json)
                cred = credentials.Certificate(cred_dict)
                # Check if app already initialized to avoid error on reload
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.enabled = True
                print("Firebase initialized successfully (from Environment).")
            except Exception as e:
                print(f"Error initializing Firebase from Env: {e}")
        
        # Fallback to local file (Local Development)
        elif os.path.exists(cred_path):
            try:
                cred = credentials.Certificate(cred_path)
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.enabled = True
                print("Firebase initialized successfully (from File).")
            except Exception as e:
                print(f"Error initializing Firebase from File: {e}")
        else:
            print(f"Warning: {cred_path} not found and FIREBASE_CREDENTIALS not set. Firebase features disabled.")

    def save_result(self, student_answer, key_answer, score, is_correct, register_number, image_path=None):
        """
        Saves the grading result to Firestore.
        Returns the document ID.
        """
        if not self.enabled:
            print("Firebase disabled, cannot save.")
            return None

        try:
            # CLEANUP: Ensure register_number is a clean string
            reg_no_clean = str(register_number).strip()
            
            doc_ref = self.db.collection('graded_papers').document()
            data = {
                'timestamp': datetime.datetime.now(),
                'register_number': reg_no_clean,  # Store clean
                'student_answer': student_answer,
                'key_answer': key_answer,
                'score': score,
                'is_correct': is_correct,
                'image_path': image_path if image_path else "Not uploaded"
            }
            doc_ref.set(data)
            print(f"DEBUG: Saved result for Reg No: '{reg_no_clean}' with ID: {doc_ref.id}")
            return doc_ref.id
        except Exception as e:
            print(f"Error saving to Firestore: {e}")
            return None

    def get_result(self, doc_id):
        """
        Retrieves a result by ID.
        """
        if not self.enabled:
            return None
        
        try:
            doc = self.db.collection('graded_papers').document(doc_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"Error reading from Firestore: {e}")
            return None

    def get_result_by_reg_no(self, register_number):
        """
        Retrieves the most recent result for a specific register number.
        """
        if not self.enabled:
            return None

        try:
            reg_no_clean = str(register_number).strip()
            print(f"DEBUG: Searching Firestore for Reg No: '{reg_no_clean}'")
            
            # Query the collection
            # Use 'timestamp' ordering - requires a composite index in Firestore sometimes
            # If search fails, try removing order_by temporarily to debug index issues
            docs = self.db.collection('graded_papers')\
                .where('register_number', '==', reg_no_clean)\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(1)\
                .stream()
            
            for doc in docs:
                print(f"DEBUG: Found document {doc.id}")
                return doc.to_dict() # Return the first (most recent) match
            
            print("DEBUG: No documents found for this query.")
            return None
        except Exception as e:
            print(f"Error searching Firestore: {e}")
            # Fallback: Try without ordering if index is missing
            try:
                print("DEBUG: Retrying search without sorting (Index might be missing)...")
                docs = self.db.collection('graded_papers')\
                    .where('register_number', '==', reg_no_clean)\
                    .limit(1)\
                    .stream()
                for doc in docs:
                    return doc.to_dict()
            except Exception as e2:
                print(f"Error on fallback search: {e2}")
            return None

    # --- EXAM MANAGEMENT ---
    def save_exam(self, course_name, key_text):
        if not self.enabled: return None
        try:
            doc_ref = self.db.collection('exams').document()
            doc_ref.set({
                'course_name': course_name.strip(),
                'answer_key': key_text.strip(),
                'created_at': datetime.datetime.now()
            })
            return doc_ref.id
        except Exception as e:
            print(f"Error saving exam: {e}")
            return None

    def get_all_exams(self):
        if not self.enabled: return []
        try:
            exams = self.db.collection('exams').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in exams]
        except Exception as e:
            print(f"Error fetching exams: {e}")
            return []
    
    def get_exam_key(self, exam_id):
        if not self.enabled: return None
        try:
            doc = self.db.collection('exams').document(exam_id).get()
            if doc.exists:
                return doc.to_dict().get('answer_key')
            return None
        except Exception as e:
            print(f"Error fetching exam key: {e}")
            return None
