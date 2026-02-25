"""
Local DistilBert model provider for prompt injection detection.
Loads a fine-tuned DistilBertForSequenceClassification model and runs inference locally.
"""

import os
import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification

from .types import GuardResponse, TokenUsage

# Default path to the local model directory
DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "prompt_injection_model"
)


class LocalModelProvider:
    """
    Local DistilBert model provider for prompt injection detection.
    Loads the model once and provides a predict method.
    """

    def __init__(self, model_path: str | None = None):
        """
        Initialize the local model provider.

        Args:
            model_path: Path to the directory containing model files
                        (config.json, model.safetensors, tokenizer files).
                        Defaults to the prompt_injection_model directory.
        """
        self.model_path = model_path or os.path.abspath(DEFAULT_MODEL_PATH)

        if not os.path.isdir(self.model_path):
            raise FileNotFoundError(
                f"Model directory not found: {self.model_path}. "
                "Please provide the correct path to your DistilBert model."
            )

        # Load tokenizer and model
        self.tokenizer = DistilBertTokenizer.from_pretrained(self.model_path)
        self.model = DistilBertForSequenceClassification.from_pretrained(self.model_path)
        self.model.eval()  # Set to evaluation mode

    def predict(self, text: str) -> GuardResponse:
        """
        Run inference on the input text.

        Args:
            text: The input text to classify.

        Returns:
            GuardResponse with classification, reasoning, and confidence.
        """
        # Tokenize input
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )

        # Run inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=-1)
            predicted_class = torch.argmax(probabilities, dim=-1).item()
            confidence = probabilities[0][predicted_class].item()

        # Map: label 0 = safe (pass), label 1 = injection (block)
        if predicted_class == 1:
            classification = "block"
            reasoning = (
                f"Local DistilBert model detected prompt injection "
                f"with {confidence:.1%} confidence."
            )
            violation_types = ["prompt_injection"]
            cwe_codes = ["CWE-77"]
        else:
            classification = "pass"
            reasoning = (
                f"Local DistilBert model classified input as safe "
                f"with {confidence:.1%} confidence."
            )
            violation_types = []
            cwe_codes = []

        return GuardResponse(
            classification=classification,
            reasoning=reasoning,
            violation_types=violation_types,
            cwe_codes=cwe_codes,
            usage=TokenUsage(
                prompt_tokens=inputs["input_ids"].shape[-1],
                completion_tokens=0,
                total_tokens=inputs["input_ids"].shape[-1],
            ),
        )
