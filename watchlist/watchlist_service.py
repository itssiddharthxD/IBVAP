"""Local watchlist — store faces + embeddings offline."""
from __future__ import annotations

from typing import List, Optional
from pathlib import Path
import logging
import pickle
import shutil

import cv2
import numpy as np

from database.database import get_session
from database.repositories.watchlist_repository import WatchlistRepository
from database.models import WatchlistPerson
from core.config import PROJECT_ROOT

logger = logging.getLogger(__name__)


def _detach(session, obj: WatchlistPerson) -> WatchlistPerson:
    if obj is None:
        return obj
    _ = (
        obj.id, obj.person_id, obj.name, obj.reference_image,
        obj.embedding, obj.status, obj.notes, obj.created_at, obj.updated_at,
    )
    session.expunge(obj)
    return obj


class WatchlistService:
    def __init__(self):
        self._img_dir = PROJECT_ROOT / "data" / "watchlist"
        self._img_dir.mkdir(parents=True, exist_ok=True)

    def list_persons(self, active_only: bool = False) -> List[WatchlistPerson]:
        with get_session() as session:
            repo = WatchlistRepository(session)
            persons = repo.list_all(active_only=active_only)
            return [_detach(session, p) for p in persons]

    def add_person(
        self,
        name: str,
        reference_image: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> WatchlistPerson:
        embedding = None
        stored_path = None
        if reference_image:
            stored_path, embedding = self._ingest_image(name, reference_image)

        with get_session() as session:
            repo = WatchlistRepository(session)
            person = repo.create(
                name=name,
                reference_image=stored_path,
                embedding=embedding,
                notes=notes,
            )
            session.flush()
            return _detach(session, person)

    def add_person_from_image(
        self, name: str, image_path: str, notes: Optional[str] = None
    ) -> WatchlistPerson:
        return self.add_person(name=name, reference_image=image_path, notes=notes)

    def update_person(self, person_id: str, **kwargs) -> Optional[WatchlistPerson]:
        # If new image provided, rebuild embedding
        image_path = kwargs.pop("reference_image", None)
        if image_path:
            stored, emb = self._ingest_image(person_id, image_path)
            kwargs["reference_image"] = stored
            kwargs["embedding"] = emb

        with get_session() as session:
            repo = WatchlistRepository(session)
            person = repo.get(person_id)
            if not person:
                return None
            repo.update(person, **kwargs)
            session.flush()
            return _detach(session, person)

    def delete_person(self, person_id: str) -> bool:
        with get_session() as session:
            repo = WatchlistRepository(session)
            return repo.delete(person_id)

    def set_status(self, person_id: str, status: str) -> Optional[WatchlistPerson]:
        return self.update_person(person_id, status=status)

    def _ingest_image(self, key: str, image_path: str) -> tuple:
        """Copy image locally and compute embedding if face engine available."""
        src = Path(image_path)
        if not src.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        dest = self._img_dir / f"{key}_{src.name}"
        shutil.copy2(src, dest)

        embedding_bytes = None
        try:
            from ai_engine.face.face_engine import get_face_engine
            engine = get_face_engine()
            img = cv2.imread(str(dest))
            if img is None:
                raise ValueError("Could not read image")
            emb = engine.embed_image(img)
            if emb is not None:
                embedding_bytes = pickle.dumps(emb.astype(np.float32))
                logger.info("Embedding generated for %s", key)
            else:
                logger.warning("No face found in reference image: %s", dest)
        except Exception as e:
            logger.warning("Embedding failed for %s: %s", key, e)

        return str(dest), embedding_bytes
