from pathlib import Path

class YOLODetector:
    def __init__(self, model_path, device="auto", confidence=0.35, iou=0.45):
        self.model_path = Path(model_path)
        self.device = self._device(device)
        self.confidence = confidence
        self.iou = iou
        self.model = None
        self.error = None

    @staticmethod
    def _device(value):
        if value != "auto":
            return value
        try:
            import torch
            return "cuda:0" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    def load(self):
        if not self.model_path.exists():
            self.error = f"Local model not found: {self.model_path}"
            return False
        try:
            from ultralytics import YOLO
            self.model = YOLO(str(self.model_path))
            return True
        except Exception as exc:
            self.error = str(exc)
            return False

    def infer(self, frame, imgsz=640, tracking=True):
        if self.model is None:
            return []
        kwargs = dict(
            source=frame,
            conf=self.confidence,
            iou=self.iou,
            imgsz=imgsz,
            device=self.device,
            verbose=False,
        )
        results = self.model.track(**kwargs, persist=True) if tracking else self.model.predict(**kwargs)
        return self._parse(results)

    def _parse(self, results):
        detections = []
        from core.contracts import Detection
        for result in results:
            names = result.names
            boxes = result.boxes
            if boxes is None:
                continue
            for i in range(len(boxes)):
                xyxy = boxes.xyxy[i].tolist()
                cls = int(boxes.cls[i].item())
                conf = float(boxes.conf[i].item())
                track = None
                if boxes.id is not None:
                    track = int(boxes.id[i].item())
                detections.append(Detection(
                    class_id=cls,
                    label=str(names.get(cls, cls)),
                    confidence=conf,
                    bbox=tuple(map(int, xyxy)),
                    track_id=track,
                ))
        return detections
