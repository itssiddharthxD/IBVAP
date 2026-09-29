"""Offline OCR for license plates."""
from __future__ import annotations

from typing import Tuple, Optional, Any, List
import logging
import re

import numpy as np
import cv2

logger = logging.getLogger(__name__)


class OCREngine:
    def __init__(self):
        self._backend: Optional[str] = None
        self._reader = None
        self._error: Optional[str] = None
        self._ready = False
        self._init()

    def _init(self) -> None:
        try:
            import easyocr
            self._reader = easyocr.Reader(["en"], gpu=False, verbose=False)
            self._backend = "easyocr"
            self._ready = True
            self._error = None
            logger.info("OCR engine ready (EasyOCR)")
            return
        except ImportError:
            logger.warning("easyocr not installed")
        except Exception as e:
            logger.warning("EasyOCR init failed: %s", e)

        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self._backend = "tesseract"
            self._ready = True
            self._error = None
            logger.info("OCR engine ready (Tesseract)")
            return
        except Exception as e:
            logger.warning("Tesseract not available: %s", e)

        self._error = "No OCR backend. Install: pip install easyocr"
        logger.error(self._error)

    def is_ready(self) -> bool:
        return self._ready

    def get_error(self) -> Optional[str]:
        return self._error

    def prepare_variants(self, crop: np.ndarray) -> List[np.ndarray]:
        if crop is None or crop.size == 0:
            return []
        h, w = crop.shape[:2]
        if w < 180 or h < 48:
            scale = max(180 / max(w, 1), 48 / max(h, 1), 2.5)
            crop = cv2.resize(
                crop, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC
            )
        h, w = crop.shape[:2]
        if w > 480:
            scale = 480 / w
            crop = cv2.resize(crop, (480, int(h * scale)), interpolation=cv2.INTER_AREA)

        if len(crop.shape) == 2:
            bgr = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
            gray = crop
        else:
            bgr = crop
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        eq = cv2.equalizeHist(gray)
        # mild unsharp
        blur = cv2.GaussianBlur(eq, (0, 0), 1.0)
        sharp = cv2.addWeighted(eq, 1.6, blur, -0.6, 0)
        thr = cv2.adaptiveThreshold(
            sharp, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5
        )
        return [
            bgr,
            cv2.cvtColor(eq, cv2.COLOR_GRAY2BGR),
            cv2.cvtColor(sharp, cv2.COLOR_GRAY2BGR),
            cv2.cvtColor(thr, cv2.COLOR_GRAY2BGR),
        ]

    def read(self, plate_crop: Any) -> Tuple[str, float]:
        if not self._ready or plate_crop is None or getattr(plate_crop, "size", 0) == 0:
            return "", 0.0
        try:
            if self._backend == "easyocr":
                return self._read_easyocr(plate_crop)
            if self._backend == "tesseract":
                return self._read_tesseract(plate_crop)
        except Exception as e:
            logger.exception("OCR read failed: %s", e)
        return "", 0.0

    def _read_easyocr(self, crop: np.ndarray) -> Tuple[str, float]:
        best_text = ""
        best_conf = 0.0

        for img in self.prepare_variants(crop):
            try:
                results = self._reader.readtext(
                    img,
                    detail=1,
                    paragraph=False,
                    batch_size=1,
                    allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                )
            except Exception:
                try:
                    results = self._reader.readtext(img, detail=1, paragraph=False)
                except Exception:
                    continue
            if not results:
                continue

            parts: List[str] = []
            confs: List[float] = []
            for (_bbox, text, conf) in results:
                cleaned = self.clean_text(text)
                if not cleaned or len(cleaned) < 2:
                    continue
                parts.append(cleaned)
                confs.append(float(conf))
                if conf > best_conf:
                    best_conf = float(conf)
                    best_text = cleaned

            combined = self.clean_text("".join(parts))
            if len(combined) >= 5 and self.looks_like_plate(combined):
                avg = sum(confs) / len(confs) if confs else best_conf
                return combined, max(float(avg), best_conf * 0.85)

            if self.looks_like_plate(best_text) and best_conf >= 0.15:
                return best_text, best_conf

        # Accept weaker hits if alphanumeric mix
        if best_text and len(best_text) >= 5 and best_conf >= 0.12:
            if sum(c.isalpha() for c in best_text) >= 1 and sum(c.isdigit() for c in best_text) >= 2:
                return best_text, best_conf
        return best_text, best_conf

    def _read_tesseract(self, crop: np.ndarray) -> Tuple[str, float]:
        import pytesseract

        best = ("", 0.0)
        for img in self.prepare_variants(crop):
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            config = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            text = pytesseract.image_to_string(gray, config=config)
            cleaned = self.clean_text(text)
            if not cleaned:
                continue
            conf = 0.7 if self.looks_like_plate(cleaned) else 0.35
            if conf > best[1] or len(cleaned) > len(best[0]):
                best = (cleaned, conf)
        return best

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        return re.sub(r"[^A-Za-z0-9]", "", text).upper()

    @staticmethod
    def looks_like_plate(text: str) -> bool:
        if not text:
            return False
        n = len(text)
        if n < 4 or n > 14:
            return False
        letters = sum(c.isalpha() for c in text)
        digits = sum(c.isdigit() for c in text)
        if digits < 2:
            return False
        # Indian-style and generic patterns
        patterns = [
            r"^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{3,4}$",
            r"^[A-Z]{2}[0-9]{2}[A-Z]{1,3}[0-9]{3,4}$",
            r"^[A-Z]{3}[0-9]{3,4}$",
            r"^[0-9]{2}[A-Z]{1,3}[0-9]{3,4}$",
            r"^[A-Z]{2}[0-9]{4,7}$",
            r"^[A-Z0-9]{5,12}$",
        ]
        for p in patterns:
            if re.match(p, text):
                return True
        return 5 <= n <= 12 and letters >= 1 and digits >= 2
