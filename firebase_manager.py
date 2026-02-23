import firebase_admin
from firebase_admin import credentials, firestore
import os
import datetime
import json
import uuid

class LocalDB:
    """
    A simple JSON-based mock database for local development when Firebase is not configured.
    """
    def __init__(self, db_file="local_db.json"):
        self.db_file = db_file
        self.data = {
            "graded_papers": {},
            "exams": {}
        }
        self.load()

    def load(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r') as f:
                    content = f.read()
                    if content:
                        loaded = json.loads(content)
                        # Ensure structure
                        self.data["graded_papers"] = loaded.get("graded_papers", {})
                        self.data["exams"] = loaded.get("exams", {})
            except Exception as e:
                print(f"Error loading local DB: {e}")

    def save(self):
        try:
            # Convert datetime objects to string for JSON serialization
            # This is a simple serialization; for production use proper serializers
            def default_serializer(obj):
                if isinstance(obj, (datetime.date, datetime.datetime)):
                    return obj.isoformat()
                return str(obj)

            with open(self.db_file, 'w') as f:
                json.dump(self.data, f, indent=4, default=default_serializer)
        except Exception as e:
            print(f"Error saving local DB: {e}")

    def add_document(self, collection, data):
        doc_id = str(uuid.uuid4())
        if "timestamp" not in data and "created_at" not in data:
             data["timestamp"] = datetime.datetime.now().isoformat()
        
        self.data[collection][doc_id] = data
        self.save()
        return doc_id

    def get_document(self, collection, doc_id):
        return self.data.get(collection, {}).get(doc_id)

    def query(self, collection, field, value):
        results = []
        for doc_id, data in self.data.get(collection, {}).items():
            if str(data.get(field)) == str(value):
                # Attach ID mostly for compatibility
                res = data.copy()
                # res['id'] = doc_id 
                results.append(res)
        return results
    
    def get_all(self, collection):
         results = []
         for doc_id, data in self.data.get(collection, {}).items():
             res = data.copy()
             res['id'] = doc_id
             results.append(res)
         return results

class FirebaseManager:
    def __init__(self, cred_path="serviceAccountKey.json"):
        self.connection_error = None
        self.mock_mode = False
        self.local_db = None

        # Check for environment variable first (Cloud Deployment)
        firebase_json = os.environ.get("FIREBASE_CREDENTIALS")

        if firebase_json:
            try:
                print("Found FIREBASE_CREDENTIALS env var. Initializing...")
                cred_dict = json.loads(firebase_json)
                cred = credentials.Certificate(cred_dict)
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.enabled = True
                print("Firebase initialized successfully (from Environment).")
            except Exception as e:
                self.connection_error = f"Env Init Error: {e}"
                print(f"Error initializing Firebase from Env: {e}")
                self._enable_mock_mode()
        
        else:
            # Fallback to local file (Local Development)
            # Prioritize standard name, then specific found name
            if os.path.exists(cred_path):
                target_cred = cred_path
            elif os.path.exists("ocrdatabase-9d830-firebase-adminsdk-fbsvc-c5851efa01.json"):
                target_cred = "ocrdatabase-9d830-firebase-adminsdk-fbsvc-c5851efa01.json"
            else:
                target_cred = None

            if target_cred:
                try:
                    cred = credentials.Certificate(target_cred)
                    if not firebase_admin._apps:
                        firebase_admin.initialize_app(cred)
                    self.db = firestore.client()
                    
                    # Verify Connection
                    try:
                        self.db.collection('test_connection').document('ping').get()
                        self.enabled = True
                        print(f"Firebase initialized and connected successfully (from File: {target_cred}).")
                    except Exception as conn_err:
                         self.connection_error = f"Connection Failed: {conn_err}"
                         print(f"CRITICAL ERROR: Firebase credentials valid, but connection failed: {conn_err}")
                         self._enable_mock_mode()
                except Exception as e:
                    self.connection_error = f"File Init Error: {e}"
                    print(f"Error initializing Firebase from File: {e}")
                    self._enable_mock_mode()
            else:
                print(f"Warning: '{cred_path}' or alternative key not found. Firebase features disabled.")
                self._enable_mock_mode()

    def _enable_mock_mode(self):
        print("Initializing Local Mock DB (Fallback Mode)...")
        self.mock_mode = True
        self.enabled = True # Enabled, but using mock
        self.local_db = LocalDB()
        print("Mock DB Ready. Data will be saved to 'local_db.json'.")

    def save_result(self, student_answer, key_answer, score, is_correct, register_number, image_path=None):
        if not self.enabled:
            return None

        # CLEANUP: Ensure register_number is a clean string
        reg_no_clean = str(register_number).strip()

        data = {
            'timestamp': datetime.datetime.now(),
            'register_number': reg_no_clean,
            'student_answer': student_answer,
            'key_answer': key_answer,
            'score': score,
            'is_correct': is_correct,
            'image_path': image_path if image_path else "Not uploaded"
        }

        if self.mock_mode:
            doc_id = self.local_db.add_document('graded_papers', data)
            print(f"DEBUG (MOCK): Saved result for {reg_no_clean} with ID {doc_id}")
            return doc_id

        try:
            doc_ref = self.db.collection('graded_papers').document()
            doc_ref.set(data)
            print(f"DEBUG: Saved result for Reg No: '{reg_no_clean}' with ID: {doc_ref.id}")
            return doc_ref.id
        except Exception as e:
            print(f"Error saving to Firestore: {e}")
            return None

    def get_result(self, doc_id):
        if not self.enabled: return None
        
        if self.mock_mode:
            return self.local_db.get_document('graded_papers', doc_id)

        try:
            doc = self.db.collection('graded_papers').document(doc_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"Error reading from Firestore: {e}")
            return None

    def get_result_by_reg_no(self, register_number):
        if not self.enabled: return None

        reg_no_clean = str(register_number).strip()
        print(f"DEBUG: Searching for Reg No: '{reg_no_clean}'")

        if self.mock_mode:
            results = self.local_db.query('graded_papers', 'register_number', reg_no_clean)
            if results:
                # Sort by timestamp decending (simple string compare for ISO format works well enough)
                results.sort(key=lambda x: str(x.get('timestamp', '')), reverse=True)
                return results[0]
            print("DEBUG (MOCK): No results found.")
            return None

        try:
            # Query the collection
            docs = self.db.collection('graded_papers')\
                .where('register_number', '==', reg_no_clean)\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(1)\
                .stream()
            
            for doc in docs:
                return doc.to_dict()
            
            return None
        except Exception as e:
            print(f"Error searching Firestore: {e}")
            # Fallback
            try:
                 docs = self.db.collection('graded_papers').where('register_number', '==', reg_no_clean).limit(1).stream()
                 for doc in docs: return doc.to_dict()
            except: pass
            return None

    # --- EXAM MANAGEMENT ---
    def save_exam(self, course_name, key_text):
        if not self.enabled: return None
        
        if self.mock_mode:
            data = {
                'course_name': course_name.strip(),
                'answer_key': key_text.strip(),
                'created_at': datetime.datetime.now()
            }
            return self.local_db.add_document('exams', data)

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

        if self.mock_mode:
            exams = self.local_db.get_all('exams')
            # Sort by created_at descending
            exams.sort(key=lambda x: str(x.get('created_at', '')), reverse=True)
            return exams

        try:
            exams = self.db.collection('exams').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in exams]
        except Exception as e:
            print(f"Error fetching exams: {e}")
            return []
    
    def get_exam_key(self, exam_id):
        if not self.enabled: return None

        if self.mock_mode:
            exam = self.local_db.get_document('exams', exam_id)
            return exam.get('answer_key') if exam else None

        try:
            doc = self.db.collection('exams').document(exam_id).get()
            if doc.exists:
                return doc.to_dict().get('answer_key')
            return None
        except Exception as e:
            print(f"Error fetching exam key: {e}")
            return None

