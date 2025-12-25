import firebase_admin
from firebase_admin import credentials, firestore
import os
import datetime

class FirebaseManager:
    def __init__(self, cred_path="serviceAccountKey.json"):
        self.db = None
        self.enabled = False
        
        if os.path.exists(cred_path):
            try:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.enabled = True
                print("Firebase initialized successfully.")
            except Exception as e:
                print(f"Error initializing Firebase: {e}")
        else:
            print(f"Warning: {cred_path} not found. Firebase features disabled.")

    def save_result(self, student_answer, key_answer, score, is_correct, image_path=None):
        """
        Saves the grading result to Firestore.
        Returns the document ID.
        """
        if not self.enabled:
            return None

        try:
            doc_ref = self.db.collection('graded_papers').document()
            data = {
                'timestamp': datetime.datetime.now(),
                'student_answer': student_answer,
                'key_answer': key_answer,
                'score': score,
                'is_correct': is_correct,
                'image_path': image_path if image_path else "Not uploaded"
            }
            doc_ref.set(data)
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
