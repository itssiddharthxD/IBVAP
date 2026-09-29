"""
Unified local face engine.

Primary backend: InsightFace (SCRFD detection + ArcFace embeddings) — offline after first model fetch.
Fallback: OpenCV Haar cascade (detection only, no recognition).
"""
from __future__ import annotations

from typing import List, Optional, Any, Tuple
from datetime import datetime
import logging
import pickle

import numpy as np
import cv2

from core.contracts import FaceResult, BoundingBox, MatchStatus

logger = logging.getLogger(__name__)


class FaceEngine:
    """Singleton-style face detect + embed + match against local gallery."""

    _instance: Optional["FaceEngine"] = None

    def __new__(cls) -> "FaceEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._backend: Optional[str] = None
        self._app = None
        self._cascade = None
        self._ready = False
        self._recog_ready = False
        self._error: Optional[str] = None
        self._gallery: List[dict] = []  # {person_id, name, embedding}
        self._match_threshold = 0.40  # cosine similarity (insightface typically 0.3–0.5)
        self._load()

    def _load(self) -> None:
        # 1) InsightFace
        try:
            from insightface.app import FaceAnalysis

            app = FaceAnalysis(
                name="buffalo_sc",  # small/fast pack
                providers=["CPUExecutionProvider"],
            )
            app.prepare(ctx_id=-1, det_size=(320, 320))
            self._app = app
            self._backend = "insightface"
            self._ready = True
            self._recog_ready = True
            self._error = None
            logger.info("Face engine ready (InsightFace buffalo_sc)")
            return
        except ImportError:
            logger.warning("insightface not installed")
        except Exception as e:
            logger.warning("InsightFace init failed: %s", e)

        # 2) OpenCV Haar — detection only
        try:
            path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            cascade = cv2.CascadeClassifier(path)
            if cascade.empty():
                raise RuntimeError("Haar cascade failed to load")
            self._cascade = cascade
            self._backend = "opencv"
            self._ready = True
            self._recog_ready = False
            self._error = (
                "Face detection only (OpenCV). "
                "For recognition install: pip install insightface onnxruntime"
            )
            logger.info("Face engine: OpenCV detection only (no recognition)")
            return
        except Exception as e:
            logger.warning("OpenCV face cascade failed: %s", e)

        self._error = (
            "Face engine unavailable.\n"
            "Install: pip install insightface onnxruntime"
        )
        logger.error(self._error)

    def is_ready(self) -> bool:
        return self._ready

    def can_recognize(self) -> bool:
        return self._recog_ready

    def get_error(self) -> Optional[str]:
        return self._error

    def set_gallery(self, persons: List[dict]) -> None:
        """
        persons: list of {person_id, name, embedding: bytes|np.ndarray|None}
        """
        gallery = []
        for p in persons:
            emb = p.get("embedding")
            if emb is None:
                continue
            if isinstance(emb, (bytes, bytearray)):
                try:
                    emb = pickle.loads(emb)
                except Exception:
                    continue
            emb = np.asarray(emb, dtype=np.float32).flatten()
            n = np.linalg.norm(emb)
            if n < 1e-6:
                continue
            emb = emb / n
            gallery.append(
                {
                    "person_id": p["person_id"],
                    "name": p.get("name") or p["person_id"],
                    "embedding": emb,
                }
            )
        self._gallery = gallery
        logger.info("Face gallery loaded: %d identities", len(gallery))

    def embed_image(self, image_bgr: np.ndarray) -> Optional[np.ndarray]:
        """Extract normalized face embedding from a reference photo."""
        if not self._recog_ready or self._app is None or image_bgr is None:
            return None
        faces = self._app.get(image_bgr)
        if not faces:
            return None
        # largest face
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        emb = np.asarray(face.embedding, dtype=np.float32).flatten()
        n = np.linalg.norm(emb)
        if n < 1e-6:
            return None
        return emb / n

    def detect_and_match(
        self,
        frame: np.ndarray,
        camera_id: str,
        timestamp: datetime,
        conf_threshold: float = 0.5,
        do_recognize: bool = True,
    ) -> List[FaceResult]:
        if not self._ready or frame is None:
            return []

        if self._backend == "insightface" and self._app is not None:
            return self._run_insightface(frame, camera_id, timestamp, do_recognize)
        if self._backend == "opencv" and self._cascade is not None:
            return self._run_opencv(frame, camera_id, timestamp)
        return []

    def _run_insightface(
        self, frame, camera_id, timestamp, do_recognize: bool
    ) -> List[FaceResult]:
        results: List[FaceResult] = []
        try:
            faces = self._app.get(frame)
        except Exception as e:
            logger.exception("InsightFace get failed: %s", e)
            return results

        for face in faces:
            x1, y1, x2, y2 = [float(v) for v in face.bbox]
            det_score = float(getattr(face, "det_score", 0.8))
            person_id = None
            name = None
            similarity = 0.0
            status = MatchStatus.UNKNOWN

            if do_recognize and self._recog_ready and self._gallery:
                emb = np.asarray(face.embedding, dtype=np.float32).flatten()
                n = np.linalg.norm(emb)
                if n > 1e-6:
                    emb = emb / n
                    best_sim = -1.0
                    best = None
                    for g in self._gallery:
                        sim = float(np.dot(emb, g["embedding"]))
                        if sim > best_sim:
                            best_sim = sim
                            best = g
                    similarity = best_sim
                    if best is not None and best_sim >= self._match_threshold:
                        status = MatchStatus.MATCHED
                        person_id = best["person_id"]
                        name = best["name"]
                    elif best_sim >= self._match_threshold * 0.75:
                        status = MatchStatus.LOW_CONFIDENCE
                    else:
                        status = MatchStatus.UNKNOWN

            results.append(
                FaceResult(
                    camera_id=camera_id,
                    timestamp=timestamp,
                    bounding_box=BoundingBox(x1, y1, x2, y2),
                    confidence=det_score,
                    person_id=person_id,
                    match_status=status,
                    similarity=similarity,
                    name=name,
                )
            )
        return results

    def _run_opencv(self, frame, camera_id, timestamp) -> List[FaceResult]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._cascade.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))
        results = []
        for (x, y, w, h) in faces:
            results.append(
                FaceResult(
                    camera_id=camera_id,
                    timestamp=timestamp,
                    bounding_box=BoundingBox(float(x), float(y), float(x + w), float(y + h)),
                    confidence=0.7,
                    match_status=MatchStatus.UNKNOWN,
                )
            )
        return results


def get_face_engine() -> FaceEngine:
    return FaceEngine()
