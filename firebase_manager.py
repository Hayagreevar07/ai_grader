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

    def save_result(self, student_answer, key_answer, score, is_correct, register_number, image_path=None):
        """
        Saves the grading result to Firestore.
        Returns the document ID.
        """
        if not self.enabled:
            print("Firebase disabled, cannot save.")
            return None

        try:
            # Use register_number as ID or part of query? 
            # Better to use auto-ID but index by reg_no for search.
            doc_ref = self.db.collection('graded_papers').document()
            data = {
                'timestamp': datetime.datetime.now(),
                'register_number': register_number,
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

    def get_result_by_reg_no(self, register_number):
        """
        Retrieves the most recent result for a specific register number.
        """
        if not self.enabled:
            return None

        try:
            # Query the collection
            docs = self.db.collection('graded_papers')\
                .where('register_number', '==', register_number)\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(1)\
                .stream()
            
            for doc in docs:
                return doc.to_dict() # Return the first (most recent) match
            
            return None
        except Exception as e:
            print(f"Error searching Firestore: {e}")
            return None
