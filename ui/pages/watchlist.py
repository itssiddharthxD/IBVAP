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
        from services.plate_watchlist_service import PlateWatchlistService
        self.plate_svc = PlateWatchlistService()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        title = QLabel("Watchlist")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        from PySide6.QtWidgets import QTabWidget
        tabs = QTabWidget()
        tabs.addTab(self._build_faces_tab(), "Faces")
        tabs.addTab(self._build_plates_tab(), "Plates")
        root.addWidget(tabs)

    def _build_faces_tab(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)
        header = QHBoxLayout()
        header.addStretch()
        btn_add = QPushButton("Add person")
        btn_add.setObjectName("toolBtnPrimary")
        btn_add.clicked.connect(self._add)
        btn_del = QPushButton("Delete")
        btn_del.setObjectName("toolBtn")
        btn_del.clicked.connect(self._delete)
        btn_ref = QPushButton("Refresh")
        btn_ref.setObjectName("toolBtn")
        btn_ref.clicked.connect(self.refresh)
        header.addWidget(btn_add)
        header.addWidget(btn_del)
        header.addWidget(btn_ref)
        root.addLayout(header)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Status", "Face", "Notes"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        root.addWidget(self.table)
        self.refresh()
        return w

    def _build_plates_tab(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)
        header = QHBoxLayout()
        header.addWidget(QLabel("Blacklist / whitelist plates for ANPR rules"))
        header.addStretch()
        btn_add = QPushButton("Add plate")
        btn_add.setObjectName("toolBtnPrimary")
        btn_add.clicked.connect(self._add_plate)
        btn_del = QPushButton("Delete")
        btn_del.setObjectName("toolBtn")
        btn_del.clicked.connect(self._del_plate)
        btn_ref = QPushButton("Refresh")
        btn_ref.setObjectName("toolBtn")
        btn_ref.clicked.connect(self.refresh_plates)
        header.addWidget(btn_add)
        header.addWidget(btn_del)
        header.addWidget(btn_ref)
        root.addLayout(header)
        self.plate_table = QTableWidget(0, 4)
        self.plate_table.setHorizontalHeaderLabels(["ID", "Plate", "List", "Notes"])
        self.plate_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.plate_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.plate_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        root.addWidget(self.plate_table)
        self.refresh_plates()
        return w

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

    def refresh_plates(self) -> None:
        plates = self.plate_svc.list_plates(active_only=False)
        self.plate_table.setRowCount(0)
        for p in plates:
            row = self.plate_table.rowCount()
            self.plate_table.insertRow(row)
            vals = [p.plate_id, p.plate_text, p.list_type, p.notes or "—"]
            for col, v in enumerate(vals):
                self.plate_table.setItem(row, col, QTableWidgetItem(str(v)))

    def _add(self) -> None:
        dlg = AddPersonDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.get_data()
        if not data["name"] or not data["image"]:
            QMessageBox.warning(self, "Validation", "Name and photo required.")
            return
        try:
            person = self.service.add_person_from_image(
                name=data["name"], image_path=data["image"], notes=data["notes"]
            )
            if not person.embedding:
                QMessageBox.warning(self, "No face", "Saved but no face embedding.")
            else:
                QMessageBox.information(self, "Added", f"{person.name} added.")
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

    def _add_plate(self) -> None:
        plate, ok = QInputDialog.getText(self, "Add plate", "Plate number:")
        if not ok or not plate.strip():
            return
        list_type, ok2 = QInputDialog.getItem(
            self, "List type", "Type:", ["blacklist", "whitelist"], 0, False
        )
        if not ok2:
            return
        try:
            self.plate_svc.add(plate.strip(), list_type=list_type)
            self.refresh_plates()
            QMessageBox.information(
                self, "Added",
                f"{plate.upper()} on {list_type}.\nEnable rule type «Plate Blacklist Match» for alerts."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _del_plate(self) -> None:
        rows = self.plate_table.selectionModel().selectedRows()
        if not rows:
            return
        pid = self.plate_table.item(rows[0].row(), 0).text()
        if QMessageBox.question(self, "Confirm", "Delete plate?") == QMessageBox.Yes:
            self.plate_svc.delete(pid)
            self.refresh_plates()
