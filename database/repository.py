from database.models import Event, Camera


class EventRepository:

    def __init__(self, session):
        self.session = session

    def add(self, event):
        row = Event(
            timestamp=event.timestamp,
            camera=event.camera,
            event_type=event.event_type,
            severity=event.severity,
            message=event.message,
            confidence=(
                event.detection.confidence
                if event.detection
                else None
            ),
            snapshot_path=event.snapshot_path,
        )

        self.session.add(row)
        self.session.commit()

        return row

    def recent(self, limit=100):
        return (
            self.session.query(Event)
            .order_by(Event.timestamp.desc())
            .limit(limit)
            .all()
        )


class CameraRepository:

    def __init__(self, session):
        self.session = session

    def add(
        self,
        name,
        location,
        source_type,
        source,
    ):
        camera = Camera(
            name=name,
            location=location,
            source_type=source_type,
            source=source,
            enabled=True,
            status="OFFLINE",
        )

        self.session.add(camera)
        self.session.commit()
        self.session.refresh(camera)

        return camera

    def get_all(self):
        return (
            self.session.query(Camera)
            .order_by(Camera.id.asc())
            .all()
        )

    def get(self, camera_id):
        return (
            self.session.query(Camera)
            .filter(Camera.id == camera_id)
            .first()
        )

    def update(
        self,
        camera_id,
        name=None,
        location=None,
        source_type=None,
        source=None,
        enabled=None,
    ):
        camera = self.get(camera_id)

        if not camera:
            return None

        if name is not None:
            camera.name = name

        if location is not None:
            camera.location = location

        if source_type is not None:
            camera.source_type = source_type

        if source is not None:
            camera.source = source

        if enabled is not None:
            camera.enabled = enabled

        self.session.commit()
        self.session.refresh(camera)

        return camera

    def delete(self, camera_id):
        camera = self.get(camera_id)

        if not camera:
            return None

        self.session.delete(camera)
        self.session.commit()

        return camera

    def update_status(self, camera_id, status):
        camera = self.get(camera_id)

        if not camera:
            return None

        camera.status = status

        self.session.commit()
        self.session.refresh(camera)

        return camera