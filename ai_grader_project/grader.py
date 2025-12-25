from sentence_transformers import SentenceTransformer, util
import sys

class Grader:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        print(f"Loading semantic model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print("Semantic model loaded.")

    def grade_answer(self, student_answer, key_answer, threshold=0.5):
        """
        Compares the student's answer with the key answer using semantic similarity.
        Args:
            student_answer (str): The text from the student's answer sheet.
            key_answer (str): The correct answer/keywords from the marking scheme.
            threshold (float): Similarity score threshold to consider it correct.
        Returns:
            dict: Contains 'score', 'is_correct', and 'similarity'.
        """
        # Compute embeddings
        embeddings1 = self.model.encode(student_answer, convert_to_tensor=True)
        embeddings2 = self.model.encode(key_answer, convert_to_tensor=True)

        # Compute cosine similarity
        cosine_scores = util.cos_sim(embeddings1, embeddings2)
        similarity = cosine_scores.item()

        # Simple logic: scale similarity to a score out of 100 or check threshold
        is_correct = similarity >= threshold
        
        return {
            "student_answer": student_answer,
            "key_answer": key_answer,
            "similarity_score": round(similarity, 4),
            "is_correct": is_correct
        }

if __name__ == "__main__":
    grader = Grader()
    res = grader.grade_answer("The capital of France is Paris", "Paris is the capital of France")
    print(res)
