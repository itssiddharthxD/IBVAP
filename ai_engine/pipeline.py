"""AI Pipeline – detection, face, ANPR tasks."""
from __future__ import annotations

from typing import List, Any, Dict
from datetime import datetime
import logging

from core.contracts import DetectionResult
from .task_manager import TaskManager
from .detection.yolo_detector import YOLODetector
from .tracking.bytetrack import ByteTrackTracker
from .face.face_detector import FaceDetector
from .face.face_recognizer import FaceRecognizer
from .vehicle.vehicle_classifier import VehicleClassifier
from .anpr.anpr_pipeline import ANPRPipeline

logger = logging.getLogger(__name__)


class AIPipeline:
    def __init__(self, device: str = "AUTO"):
        self.device = device
        self.yolo = YOLODetector(device=device)
        self.tracker = ByteTrackTracker()
        self.face_detector = FaceDetector()
        self.face_recognizer = FaceRecognizer()
        self.vehicle_clf = VehicleClassifier()
        self.anpr = ANPRPipeline()
        self._frame_counter = 0
        self._gallery_loaded = False

        if self.face_detector.is_ready():
            logger.info("Face detection ready")
        else:
            logger.warning("Face detection: %s", self.face_detector.get_error())
        if self.anpr.is_ready():
            logger.info("ANPR ready")
        else:
            logger.warning("ANPR: %s", "; ".join(self.anpr.get_errors()))

    def _ensure_gallery(self) -> None:
        if self._gallery_loaded or not self.face_recognizer.is_ready():
            return
        try:
            from watchlist.watchlist_service import WatchlistService
            svc = WatchlistService()
            persons = svc.list_persons(active_only=True)
            gallery = []
            for p in persons:
                gallery.append(
                    {
                        "person_id": p.person_id,
                        "name": p.name,
                        "embedding": p.embedding,
                    }
                )
            self.face_recognizer.load_gallery(gallery)
            self._gallery_loaded = True
        except Exception as e:
            logger.warning("Could not load face gallery: %s", e)

    def reload_gallery(self) -> None:
        self._gallery_loaded = False
        self._ensure_gallery()

    def status_report(self) -> Dict[str, str]:
        return {
            "YOLO": "ready" if self.yolo.is_ready() else (self.yolo.get_error() or "not ready"),
            "Face": "ready" if self.face_detector.is_ready() else (self.face_detector.get_error() or "not ready"),
            "Face Recognition": (
                "ready" if self.face_recognizer.is_ready() else (self.face_recognizer.get_error() or "not ready")
            ),
            "ANPR": "ready" if self.anpr.is_ready() else "; ".join(self.anpr.get_errors()) or "not ready",
        }

    def process(
        self,
        frame: Any,
        camera_id: str,
        timestamp: datetime,
        task_manager: TaskManager,
        conf_threshold: float = 0.5,
        frame_interval: int = 2,
    ) -> Dict[str, List]:
        self._frame_counter += 1
        result: Dict[str, List] = {"detections": [], "faces": [], "anpr": []}

        if frame_interval > 1 and (self._frame_counter % frame_interval) != 0:
            return result

        anpr_enabled = (
            task_manager.has_anpr()
            if hasattr(task_manager, "has_anpr")
            else (
                task_manager.is_enabled("ANPR / OCR")
                or task_manager.is_enabled("License Plate Detection")
            )
        )
        face_det = task_manager.is_enabled("Face Detection")
        face_rec = task_manager.is_enabled("Face Recognition")

        need_yolo = (
            task_manager.is_enabled("Person Detection")
            or task_manager.is_enabled("Vehicle Detection")
            or task_manager.is_enabled("Vehicle Classification")
            or task_manager.is_enabled("Tracking")
            or anpr_enabled
        )

        detections: List[DetectionResult] = []
        all_vehicles: List[DetectionResult] = []

        if need_yolo and self.yolo.is_ready():
            yolo_conf = min(conf_threshold, 0.35) if anpr_enabled else conf_threshold
            raw = self.yolo.detect(frame, camera_id, timestamp, conf_threshold=yolo_conf)
            # Always assign track IDs when we have detections (needed for line/loiter rules)
            if raw:
                raw = self.tracker.update(raw, frame)
            filtered = []
            for d in raw:
                if d.class_name == "person" and task_manager.is_enabled("Person Detection"):
                    filtered.append(d)
                elif d.class_name in ("car", "motorcycle", "bus", "truck", "bicycle"):
                    if task_manager.is_enabled("Vehicle Classification"):
                        vt = self.vehicle_clf.classify(d.class_name)
                        if vt:
                            d.extra["vehicle_type"] = vt
                    all_vehicles.append(d)
                    if (
                        task_manager.is_enabled("Vehicle Detection")
                        or task_manager.is_enabled("Vehicle Classification")
                        or anpr_enabled
                    ):
                        filtered.append(d)
            detections = filtered
        result["detections"] = detections

        # Face detect / recognize
        if (face_det or face_rec) and self.face_detector.is_ready():
            if face_rec and self.face_recognizer.is_ready():
                self._ensure_gallery()
                result["faces"] = self.face_recognizer.recognize_frame(
                    frame, camera_id, timestamp
                )
            else:
                result["faces"] = self.face_detector.detect(
                    frame, camera_id, timestamp, conf_threshold
                )

        if anpr_enabled:
            if self.anpr.is_ready():
                result["anpr"] = self.anpr.process(
                    frame, camera_id, timestamp, vehicle_detections=all_vehicles
                )
            elif self._frame_counter % 90 == 1:
                logger.warning("ANPR not ready: %s", "; ".join(self.anpr.get_errors()))

        return result
