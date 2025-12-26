"""OCR agent - handles text extraction from images with hybrid local/Gemini approach."""

import io
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from PIL import Image
import numpy as np

from .base_agent import BaseAgent, DocumentData


class OCRAgent(BaseAgent):
    """Agent for OCR processing with local engines and Gemini fallback."""

    def __init__(self, config: Dict[str, Any], logger=None):
        """Initialize OCR agent.

        Args:
            config: Configuration dictionary
            logger: Optional logger instance
        """
        super().__init__(config, logger)
        self.ocr_config = config.get('ocr', {})

        # Initialize local OCR engines
        self._init_tesseract()
        self._init_easyocr()

        # Gemini fallback configuration
        self.use_gemini_fallback = self.ocr_config.get('gemini_fallback', {}).get('enabled', True)
        self.gemini_threshold = self.ocr_config.get('gemini_fallback', {}).get('use_when_confidence_below', 70)
        self.gemini_prompt = self.ocr_config.get('gemini_fallback', {}).get(
            'prompt',
            'Extract all text from this image, including handwritten text.'
        )

        # Initialize Gemini if enabled
        if self.use_gemini_fallback:
            self._init_gemini()

    def _init_tesseract(self):
        """Initialize Tesseract OCR."""
        tesseract_config = self.ocr_config.get('tesseract', {})
        if not tesseract_config.get('enabled', True):
            self.tesseract = None
            return

        try:
            import pytesseract
            self.tesseract = pytesseract
            self.tesseract_lang = tesseract_config.get('language', 'nld+eng')
            self.tesseract_threshold = tesseract_config.get('confidence_threshold', 70)
            self.logger.info("Tesseract OCR initialized")
        except ImportError:
            self.logger.warning("pytesseract not available. Install with: pip install pytesseract")
            self.tesseract = None

    def _init_easyocr(self):
        """Initialize EasyOCR."""
        easyocr_config = self.ocr_config.get('easyocr', {})
        if not easyocr_config.get('enabled', True):
            self.easyocr = None
            return

        try:
            import easyocr
            languages = easyocr_config.get('languages', ['nl', 'en'])
            gpu = easyocr_config.get('gpu', False)
            self.easyocr = easyocr.Reader(languages, gpu=gpu)
            self.easyocr_threshold = easyocr_config.get('confidence_threshold', 70)
            self.logger.info(f"EasyOCR initialized with languages: {languages}")
        except ImportError:
            self.logger.warning("easyocr not available. Install with: pip install easyocr")
            self.easyocr = None
        except Exception as e:
            self.logger.error(f"Failed to initialize EasyOCR: {e}")
            self.easyocr = None

    def _init_gemini(self):
        """Initialize Google Gemini API."""
        try:
            import google.generativeai as genai

            gemini_config = self.config.get('gemini', {})
            api_key = gemini_config.get('api_key')

            if not api_key or api_key.startswith('${'):
                self.logger.warning("Gemini API key not configured. Gemini fallback disabled.")
                self.gemini = None
                return

            genai.configure(api_key=api_key)
            model_name = gemini_config.get('model_name', 'gemini-2.0-flash-exp')
            self.gemini = genai.GenerativeModel(model_name)
            self.logger.info(f"Gemini initialized with model: {model_name}")

        except ImportError:
            self.logger.warning("google-generativeai not available. Install with: pip install google-generativeai")
            self.gemini = None
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini: {e}")
            self.gemini = None

    def process(self, doc: DocumentData) -> DocumentData:
        """Extract text from image using OCR.

        Args:
            doc: DocumentData with image in raw_data

        Returns:
            DocumentData with extracted text in content field
        """
        if doc.file_type not in {'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'image'}:
            self.log_skip(f"{doc.file_path.name}: Not an image file")
            return doc

        if doc.raw_data is None:
            self.log_error(f"{doc.file_path.name}: No image data available")
            doc.processing_status = 'failed'
            doc.errors.append("No image data")
            return doc

        try:
            # Load image
            image = Image.open(io.BytesIO(doc.raw_data))

            # Preprocess image
            image = self._preprocess_image(image)

            # Try local OCR first
            text, confidence = self._local_ocr(image)

            # Fallback to Gemini if confidence is low
            if confidence < self.gemini_threshold and self.gemini:
                self.logger.info(
                    f"{doc.file_path.name}: Local OCR confidence {confidence:.1f}% < {self.gemini_threshold}%, "
                    "using Gemini fallback"
                )
                text = self._gemini_ocr(image)
                confidence = 100.0  # Gemini doesn't provide confidence scores

            doc.content = text
            doc.ocr_confidence = confidence
            doc.processing_status = 'completed'

            self.log_success(
                f"OCR: {doc.file_path.name} - {len(text)} chars, "
                f"confidence: {confidence:.1f}%"
            )

        except Exception as e:
            self.log_error(f"OCR failed for {doc.file_path.name}", e)
            doc.processing_status = 'failed'
            doc.errors.append(f"OCR error: {str(e)}")

        return doc

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results.

        Args:
            image: PIL Image

        Returns:
            Preprocessed image
        """
        try:
            import cv2

            # Convert to numpy array
            img_array = np.array(image)

            # Convert to grayscale if color
            if len(img_array.shape) == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

            # Apply adaptive thresholding for better text contrast
            img_array = cv2.adaptiveThreshold(
                img_array, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )

            # Denoise
            img_array = cv2.fastNlMeansDenoising(img_array)

            # Convert back to PIL Image
            return Image.fromarray(img_array)

        except ImportError:
            # OpenCV not available, return original
            self.logger.debug("OpenCV not available for image preprocessing")
            return image
        except Exception as e:
            self.logger.warning(f"Image preprocessing failed: {e}, using original")
            return image

    def _local_ocr(self, image: Image.Image) -> Tuple[str, float]:
        """Perform OCR using local engines.

        Args:
            image: PIL Image

        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        results = []

        # Try Tesseract
        if self.tesseract:
            try:
                text = self.tesseract.image_to_string(
                    image,
                    lang=self.tesseract_lang
                )
                # Get confidence
                data = self.tesseract.image_to_data(
                    image,
                    lang=self.tesseract_lang,
                    output_type=self.tesseract.Output.DICT
                )
                confidences = [c for c in data['conf'] if c != -1]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                results.append(('tesseract', text, avg_confidence))
                self.logger.debug(f"Tesseract: {len(text)} chars, confidence: {avg_confidence:.1f}%")

            except Exception as e:
                self.logger.warning(f"Tesseract OCR failed: {e}")

        # Try EasyOCR
        if self.easyocr:
            try:
                # Convert PIL to numpy for EasyOCR
                img_array = np.array(image)
                result = self.easyocr.readtext(img_array)

                # Combine text and calculate average confidence
                text_parts = []
                confidences = []
                for (bbox, text, conf) in result:
                    text_parts.append(text)
                    confidences.append(conf * 100)  # Convert to percentage

                text = ' '.join(text_parts)
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                results.append(('easyocr', text, avg_confidence))
                self.logger.debug(f"EasyOCR: {len(text)} chars, confidence: {avg_confidence:.1f}%")

            except Exception as e:
                self.logger.warning(f"EasyOCR failed: {e}")

        # Return best result
        if results:
            # Sort by confidence, then by text length
            results.sort(key=lambda x: (x[2], len(x[1])), reverse=True)
            engine, text, confidence = results[0]
            self.logger.debug(f"Selected {engine} result with confidence {confidence:.1f}%")
            return text, confidence
        else:
            self.logger.warning("All local OCR engines failed")
            return "", 0.0

    def _gemini_ocr(self, image: Image.Image) -> str:
        """Perform OCR using Gemini Vision API.

        Args:
            image: PIL Image

        Returns:
            Extracted text
        """
        if not self.gemini:
            raise RuntimeError("Gemini not initialized")

        try:
            # Convert PIL Image to format Gemini accepts
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            # Generate content
            response = self.gemini.generate_content([
                self.gemini_prompt,
                image
            ])

            text = response.text.strip()
            self.logger.debug(f"Gemini OCR: {len(text)} chars extracted")
            return text

        except Exception as e:
            self.logger.error(f"Gemini OCR failed: {e}")
            raise

    def batch_process(self, documents: list[DocumentData]) -> list[DocumentData]:
        """Process multiple documents in batch.

        Args:
            documents: List of DocumentData objects

        Returns:
            List of processed DocumentData objects
        """
        processed = []
        for doc in documents:
            if doc.file_type in {'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'image'}:
                processed.append(self.process(doc))
            else:
                processed.append(doc)

        return processed
