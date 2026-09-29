# IBVAP — Intelligent Border Video Analytics Platform

Offline / edge-first intelligent video analytics desktop application for security monitoring using CCTV/IP cameras, webcams, and prerecorded video files.

## Features

- Camera management (RTSP, Webcam, Video files)
- AI Profiles: ANPR, Person Monitoring, Vehicle Monitoring, General Detection, Custom
- Modular AI tasks per camera (Person/Vehicle/Face/ANPR/Tracking)
- Live monitoring grid (1×1 / 2×2 / 3×3)
- Local SQLite database for cameras, events, watchlist, ANPR
- Dashboard with real local metrics
- Dark professional command-center UI
- Fully offline — no cloud dependencies at runtime

## Requirements

- Python 3.12+
- See `requirements.txt`

## Quick Start

```bash
cd IBVAP
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## Models

Place model files under `models/`:

| Model            | Default path                  |
|------------------|-------------------------------|
| YOLO             | models/yolo11n.pt             |
| SCRFD            | models/scrfd_500m.onnx        |
| ArcFace          | models/arcface_r100.onnx      |
| Plate detector   | models/plate_detector.pt      |

The application starts even if models are missing and shows clear error messages instead of crashing.

## Architecture

```
UI (PySide6)
  → Services
    → Video Engine (OpenCV + QThread workers)
    → AI Engine (YOLO / SCRFD / ArcFace / ANPR interfaces)
    → SQLite (SQLAlchemy)
```

AI tasks answer *"What can the camera detect?"*  
Future security rules will answer *"What should happen when something is detected?"* and remain architecturally separate.

## Project Structure

See the repository tree under `IBVAP/`.

## License

Proprietary / Internal use.
