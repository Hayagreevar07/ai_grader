import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import os

class OCREngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processors = {}
        self.models = {}
        
        # Define model names
        self.model_names = {
            "handwritten": "microsoft/trocr-base-handwritten",
            "printed": "microsoft/trocr-base-printed"
        }
        
    def _load_model(self, model_type):
        if model_type not in self.processors:
            print(f"Loading {model_type} model: {self.model_names[model_type]}...")
            self.processors[model_type] = TrOCRProcessor.from_pretrained(self.model_names[model_type])
            self.models[model_type] = VisionEncoderDecoderModel.from_pretrained(self.model_names[model_type]).to(self.device)
            print(f"{model_type} model loaded.")

    def process_image(self, image_path, model_type="handwritten"):
        """
        Performs OCR on an image.
        Args:
            image_path (str): Path to the image file.
            model_type (str): 'handwritten' or 'printed'.
        Returns:
            str: The recognized text.
        """
        if model_type not in self.model_names:
            raise ValueError(f"Invalid model_type. Choose from {list(self.model_names.keys())}")
            
        self._load_model(model_type)
        
        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as e:
            return f"Error opening image: {e}"

        processor = self.processors[model_type]
        model = self.models[model_type]

        # Preprocess the image
        pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(self.device)

        # Generate text
        generated_ids = model.generate(pixel_values)
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

        return generated_text

if __name__ == "__main__":
    # Test block
    ocr = OCREngine()
    # print(ocr.process_image("test_image.jpg", "printed"))
