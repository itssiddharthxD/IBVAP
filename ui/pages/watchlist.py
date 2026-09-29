"""Watchlist page — add people with face photos for local recognition."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QInputDialog, QMessageBox,
    QFileDialog, QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
)
from PySide6.QtCore import Qt

from watchlist.watchlist_service import WatchlistService


class AddPersonDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add person to watchlist")
        self.setMinimumWidth(420)
        layout = QFormLayout(self)

        self.name = QLineEdit()
        self.notes = QLineEdit()
        self.image_path = QLineEdit()
        self.image_path.setReadOnly(True)
        browse = QPushButton("Browse photo…")
        browse.setObjectName("toolBtn")
        browse.clicked.connect(self._browse)
        img_row = QHBoxLayout()
        img_row.addWidget(self.image_path, 1)
        img_row.addWidget(browse)

        layout.addRow("Name *", self.name)
        layout.addRow("Photo *", img_row)
        layout.addRow("Notes", self.notes)
        hint = QLabel("Clear frontal face photo works best. Embedding stays local.")
        hint.setObjectName("pageHint")
        layout.addRow(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select face photo", "",
            "Images (*.jpg *.jpeg *.png *.bmp *.webp)",
        )
        if path:
            self.image_path.setText(path)

    def get_data(self) -> dict:
        return {
            "name": self.name.text().strip(),
            "image": self.image_path.text().strip(),
            "notes": self.notes.text().strip() or None,
        }


class WatchlistPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = WatchlistService()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Watchlist")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        self.btn_add = QPushButton("Add person")
        self.btn_add.setObjectName("toolBtnPrimary")
        self.btn_add.clicked.connect(self._add)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("toolBtn")
        self.btn_delete.clicked.connect(self._delete)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setObjectName("toolBtn")
        self.btn_refresh.clicked.connect(self.refresh)
        for b in (self.btn_add, self.btn_delete, self.btn_refresh):
            b.setCursor(Qt.PointingHandCursor)
            header.addWidget(b)
        root.addLayout(header)

        note = QLabel(
            "Local only — face photos & embeddings never leave this machine.\n"
            "Camera profile: Person Monitoring (Face Detection + Face Recognition)."
        )
        note.setObjectName("pageHint")
        root.addWidget(note)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Person ID", "Name", "Status", "Has face", "Notes"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        root.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        persons = self.service.list_persons()
        self.table.setRowCount(0)
        for p in persons:
            row = self.table.rowCount()
            self.table.insertRow(row)
            has_face = "Yes" if p.embedding else "No photo / no face"
            vals = [p.person_id, p.name, p.status, has_face, p.notes or "—"]
            for col, v in enumerate(vals):
                self.table.setItem(row, col, QTableWidgetItem(str(v)))
            self.table.setRowHeight(row, 30)

    def _add(self) -> None:
        dlg = AddPersonDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.get_data()
        if not data["name"]:
            QMessageBox.warning(self, "Validation", "Name is required.")
            return
        if not data["image"]:
            QMessageBox.warning(self, "Validation", "Please select a face photo.")
            return
        try:
            person = self.service.add_person_from_image(
                name=data["name"], image_path=data["image"], notes=data["notes"]
            )
            if not person.embedding:
                QMessageBox.warning(
                    self,
                    "No face embedding",
                    "Person saved, but no face was detected in the photo "
                    "(or insightface is not installed).\n\n"
                    "Install: pip install insightface onnxruntime\n"
                    "Then delete and re-add with a clear frontal photo.",
                )
            else:
                QMessageBox.information(
                    self, "Added",
                    f"{person.name} added.\nRestart camera streams so the gallery reloads.",
                )
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _delete(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        pid = self.table.item(rows[0].row(), 0).text()
        if QMessageBox.question(self, "Confirm", f"Delete {pid}?") == QMessageBox.Yes:
            self.service.delete_person(pid)
            self.refresh()
