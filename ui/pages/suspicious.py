"""Suspicious Activity — Rules / History / Test (tabbed)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QComboBox, QLineEdit,
    QSpinBox, QDoubleSpinBox, QCheckBox, QFormLayout, QGroupBox, QTabWidget,
    QMessageBox, QSplitter, QFrame, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from security.rule_manager import RuleManager
from security.alert_manager import AlertManager
from security.analytics_engine import AnalyticsEngine
from security.rule_types import (
    RULE_TYPES, list_rule_types, rule_type_label, fields_for, OBJECT_TYPES, defaults_for, RULE_TEMPLATES,
)
from security.state_store import StateStore
from services.camera_service import CameraService
from ui.widgets.zone_drawer import ZoneDrawer


SEVERITY_COLORS = {
    "critical": "#E05555",
    "high": "#E07A3D",
    "medium": "#D4A017",
    "low": "#3D9B8F",
}


class SuspiciousPage(QWidget):
    def __init__(self, video_service=None, parent=None):
        super().__init__(parent)
        self.video_service = video_service
        self.rule_mgr = RuleManager.instance()
        self.alert_mgr = AlertManager()
        self.camera_svc = CameraService()
        self._editing_id: Optional[str] = None
        self._analytics = AnalyticsEngine(
            rule_manager=self.rule_mgr,
            alert_manager=self.alert_mgr,
            state=StateStore(),
        )
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        title = QLabel("Suspicious Activity")
        title.setObjectName("pageTitle")
        title.setStyleSheet(
            "background:transparent; border:none; color:#EAEAEA; font-size:18px; font-weight:700;"
        )
        root.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_rules_tab(), "Rules")
        self.tabs.addTab(self._build_history_tab(), "Activity History")
        self.tabs.addTab(self._build_test_tab(), "Test")
        root.addWidget(self.tabs)

    # ══════════════════════════════════════════════════════════════
    # RULES TAB
    # ══════════════════════════════════════════════════════════════

    def _build_rules_tab(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        # Left: rules list
        left = QVBoxLayout()
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("Saved Rules"))
        hdr.addStretch()
        btn_new = QPushButton("New Rule")
        btn_new.setObjectName("toolBtnPrimary")
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.clicked.connect(self._new_rule)
        hdr.addWidget(btn_new)
        btn_tpl = QPushButton("Apply template")
        btn_tpl.setObjectName("toolBtn")
        btn_tpl.setCursor(Qt.PointingHandCursor)
        btn_tpl.clicked.connect(self._apply_template)
        hdr.addWidget(btn_tpl)
        left.addLayout(hdr)

        self.rules_table = QTableWidget(0, 5)
        self.rules_table.setHorizontalHeaderLabels(
            ["Name", "Type", "Camera", "Enabled", "Severity"]
        )
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rules_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rules_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.rules_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.rules_table.setMaximumWidth(480)
        self.rules_table.itemSelectionChanged.connect(self._on_rule_selected)
        self._style_table(self.rules_table)
        left.addWidget(self.rules_table)

        btns = QHBoxLayout()
        self.btn_toggle = QPushButton("Enable / Disable")
        self.btn_toggle.setObjectName("toolBtn")
        self.btn_toggle.clicked.connect(self._toggle_rule)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("toolBtn")
        self.btn_delete.clicked.connect(self._delete_rule)
        btns.addWidget(self.btn_toggle)
        btns.addWidget(self.btn_delete)
        btns.addStretch()
        left.addLayout(btns)
        layout.addLayout(left, 2)

        # Right: editor form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        form_host = QWidget()
        form_layout = QVBoxLayout(form_host)
        form_layout.setContentsMargins(4, 0, 4, 0)

        box = QGroupBox("Create / Edit Rule")
        box.setStyleSheet("QGroupBox { font-weight:600; }")
        fl = QFormLayout(box)
        fl.setSpacing(8)
        fl.setContentsMargins(12, 16, 12, 12)

        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("e.g. Border Loitering")
        fl.addRow("Rule Name", self.ed_name)

        self.ed_type = QComboBox()
        for k in list_rule_types():
            self.ed_type.addItem(rule_type_label(k), k)
        self.ed_type.currentIndexChanged.connect(self._on_type_changed)
        fl.addRow("Type", self.ed_type)

        self.ed_camera = QComboBox()
        self._reload_cameras()
        fl.addRow("Camera", self.ed_camera)

        self.ed_object = QComboBox()
        self.ed_object.addItems(OBJECT_TYPES)
        fl.addRow("Object", self.ed_object)

        self.ed_severity = QComboBox()
        self.ed_severity.addItems(["low", "medium", "high", "critical"])
        self.ed_severity.setCurrentText("medium")
        fl.addRow("Severity", self.ed_severity)

        # Dynamic fields container
        self.dyn_widget = QWidget()
        self.dyn_form = QFormLayout(self.dyn_widget)
        self.dyn_form.setContentsMargins(0, 0, 0, 0)
        self.dyn_form.setSpacing(8)
        fl.addRow(self.dyn_widget)

        # Dynamic field widgets are recreated in _on_type_changed
        # (QFormLayout.removeRow deletes C++ objects — never reuse them)
        self.ed_duration = None
        self.ed_min_count = None
        self.ed_window = None
        self.ed_direction = None
        self.ed_dir_tol = None
        self.ed_speed = None
        self.ed_cooldown = None

        self.ed_enabled = QCheckBox("Enabled")
        self.ed_enabled.setChecked(True)
        fl.addRow("Status", self.ed_enabled)

        # Zone drawer
        zone_box = QGroupBox("Zone / ROI  (click to add points, right-click undo)")
        zv = QVBoxLayout(zone_box)
        zbtns = QHBoxLayout()
        btn_load = QPushButton("Load Frame from Camera")
        btn_load.setObjectName("toolBtn")
        btn_load.clicked.connect(self._load_zone_frame)
        btn_clear = QPushButton("Clear Zone")
        btn_clear.setObjectName("toolBtn")
        btn_clear.clicked.connect(lambda: self.zone_drawer.clear_zone())
        zbtns.addWidget(btn_load)
        zbtns.addWidget(btn_clear)
        zbtns.addStretch()
        zv.addLayout(zbtns)
        self.zone_drawer = ZoneDrawer()
        self.zone_drawer.setMinimumHeight(220)
        zv.addWidget(self.zone_drawer)
        fl.addRow(zone_box)

        save_row = QHBoxLayout()
        save_row.addStretch()
        self.btn_save = QPushButton("Save Rule")
        self.btn_save.setObjectName("toolBtnPrimary")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setFixedHeight(34)
        self.btn_save.setMinimumWidth(140)
        self.btn_save.clicked.connect(self._save_rule)
        save_row.addWidget(self.btn_save)
        fl.addRow(save_row)

        form_layout.addWidget(box)
        form_layout.addStretch()
        scroll.setWidget(form_host)
        layout.addWidget(scroll, 3)

        self._on_type_changed()
        self._refresh_rules_table()
        return w

    def _style_table(self, table: QTableWidget) -> None:
        table.setStyleSheet(
            """
            QTableWidget { background:#0D1A2A; color:#F2F7FB; border:1px solid #1C2B3C; gridline-color:#1C2B3C; }
            QHeaderView::section { background:#0B1726; color:#71859B; border:1px solid #1C2B3C; padding:6px; }
            """
        )

    def _clear_dyn(self) -> None:
        """Remove dynamic rows. Widgets are owned by the form and deleted by Qt."""
        while self.dyn_form.rowCount():
            self.dyn_form.removeRow(0)
        # Drop Python refs so we never touch deleted C++ objects
        self.ed_duration = None
        self.ed_min_count = None
        self.ed_window = None
        self.ed_direction = None
        self.ed_dir_tol = None
        self.ed_speed = None
        self.ed_cooldown = None

    def _on_type_changed(self) -> None:
        self._clear_dyn()
        key = self.ed_type.currentData()
        fields = fields_for(key or "loitering")
        defs = defaults_for(key or "loitering")

        if "duration" in fields:
            self.ed_duration = QSpinBox()
            self.ed_duration.setRange(1, 3600)
            self.ed_duration.setValue(int(defs.get("duration_sec", 30)))
            self.ed_duration.setSuffix(" sec")
            self.dyn_form.addRow("Duration", self.ed_duration)
        if "min_count" in fields:
            self.ed_min_count = QSpinBox()
            self.ed_min_count.setRange(1, 100)
            self.ed_min_count.setValue(int(defs.get("min_count", 5)))
            self.dyn_form.addRow("Min people / count", self.ed_min_count)
        if "window" in fields:
            self.ed_window = QSpinBox()
            self.ed_window.setRange(10, 7200)
            self.ed_window.setValue(int(defs.get("window_sec", 120)))
            self.ed_window.setSuffix(" sec")
            self.dyn_form.addRow("Time window", self.ed_window)
        if "direction" in fields:
            self.ed_direction = QDoubleSpinBox()
            self.ed_direction.setRange(0, 359)
            self.ed_direction.setValue(float(defs.get("direction_deg", 0)))
            self.ed_direction.setSuffix(" °")
            self.ed_dir_tol = QDoubleSpinBox()
            self.ed_dir_tol.setRange(5, 180)
            self.ed_dir_tol.setValue(float(defs.get("direction_tolerance_deg", 45)))
            self.ed_dir_tol.setSuffix(" °")
            self.dyn_form.addRow("Allowed direction", self.ed_direction)
            self.dyn_form.addRow("Direction tolerance", self.ed_dir_tol)
        if "speed_threshold" in fields:
            self.ed_speed = QDoubleSpinBox()
            self.ed_speed.setRange(0.01, 5.0)
            self.ed_speed.setSingleStep(0.01)
            self.ed_speed.setValue(float(defs.get("speed_threshold", 0.15)))
            self.dyn_form.addRow("Speed threshold", self.ed_speed)
        if "cooldown" in fields:
            self.ed_cooldown = QSpinBox()
            self.ed_cooldown.setRange(0, 600)
            self.ed_cooldown.setValue(30)
            self.ed_cooldown.setSuffix(" sec")
            self.dyn_form.addRow("Alert cooldown", self.ed_cooldown)

        ot = defs.get("object_type")
        if ot and ot in OBJECT_TYPES:
            self.ed_object.setCurrentText(ot)

        if "schedule" in fields:
            self.ed_sched_start = QSpinBox()
            self.ed_sched_start.setRange(-1, 23)
            self.ed_sched_start.setSpecialValueText("Any")
            self.ed_sched_start.setValue(-1)
            self.ed_sched_end = QSpinBox()
            self.ed_sched_end.setRange(-1, 23)
            self.ed_sched_end.setSpecialValueText("Any")
            self.ed_sched_end.setValue(-1)
            self.dyn_form.addRow("Schedule start hour", self.ed_sched_start)
            self.dyn_form.addRow("Schedule end hour", self.ed_sched_end)
        else:
            self.ed_sched_start = None
            self.ed_sched_end = None

        if "record" in fields:
            self.ed_record = QCheckBox("Save snapshot/clip on alert")
            self.dyn_form.addRow(self.ed_record)
        else:
            self.ed_record = None

        if "line" in fields:
            self.ed_line_hint = QLabel("Line: use first 2 zone points as crossing line (draw 2+ points)")
            self.ed_line_hint.setObjectName("pageHint")
            self.dyn_form.addRow(self.ed_line_hint)

        self.zone_drawer.setEnabled(True)

    def _reload_cameras(self) -> None:
        self.ed_camera.clear()
        self.ed_camera.addItem("All cameras", "*")
        try:
            for c in self.camera_svc.list_cameras():
                self.ed_camera.addItem(f"{c.name} ({c.camera_id})", c.camera_id)
        except Exception:
            pass

    def _refresh_rules_table(self) -> None:
        self.rule_mgr.reload()
        rules = self.rule_mgr.list_rules()
        self.rules_table.setRowCount(0)
        self._rule_rows = rules
        for r in rules:
            row = self.rules_table.rowCount()
            self.rules_table.insertRow(row)
            vals = [
                r.name,
                rule_type_label(r.rule_type),
                r.camera_id or "*",
                "Yes" if r.enabled else "No",
                r.severity or "medium",
            ]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                if col == 4:
                    item.setForeground(QColor(SEVERITY_COLORS.get(str(v), "#EAEAEA")))
                self.rules_table.setItem(row, col, item)

    def _selected_rule(self):
        rows = self.rules_table.selectionModel().selectedRows()
        if not rows:
            return None
        idx = rows[0].row()
        if idx < 0 or idx >= len(self._rule_rows):
            return None
        return self._rule_rows[idx]

    def _new_rule(self) -> None:
        self._editing_id = None
        self.ed_name.clear()
        self.ed_type.setCurrentIndex(0)
        self.ed_enabled.setChecked(True)
        self.zone_drawer.clear_zone()
        self._on_type_changed()
        self.btn_save.setText("Save Rule")

    def _on_rule_selected(self) -> None:
        r = self._selected_rule()
        if not r:
            return
        self._editing_id = r.rule_id
        self.ed_name.setText(r.name)
        # type
        for i in range(self.ed_type.count()):
            if self.ed_type.itemData(i) == r.rule_type:
                self.ed_type.setCurrentIndex(i)
                break
        self._on_type_changed()
        # camera
        for i in range(self.ed_camera.count()):
            if self.ed_camera.itemData(i) == r.camera_id:
                self.ed_camera.setCurrentIndex(i)
                break
        if r.object_type:
            self.ed_object.setCurrentText(r.object_type)
        if r.severity:
            self.ed_severity.setCurrentText(r.severity)
        if r.duration_sec is not None and self.ed_duration is not None:
            self.ed_duration.setValue(int(r.duration_sec))
        if r.min_count is not None and self.ed_min_count is not None:
            self.ed_min_count.setValue(int(r.min_count))
        if r.window_sec is not None and self.ed_window is not None:
            self.ed_window.setValue(int(r.window_sec))
        if r.direction_deg is not None and self.ed_direction is not None:
            self.ed_direction.setValue(float(r.direction_deg))
        if r.direction_tolerance_deg is not None and self.ed_dir_tol is not None:
            self.ed_dir_tol.setValue(float(r.direction_tolerance_deg))
        if r.speed_threshold is not None and self.ed_speed is not None:
            self.ed_speed.setValue(float(r.speed_threshold))
        if self.ed_cooldown is not None:
            self.ed_cooldown.setValue(int(r.cooldown_sec or 30))
        self.ed_enabled.setChecked(bool(r.enabled))
        if r.zone:
            self.zone_drawer.set_zone(r.zone)
        else:
            self.zone_drawer.clear_zone()
        self.btn_save.setText("Update Rule")

    def _collect_form(self) -> Dict[str, Any]:
        rtype = self.ed_type.currentData()
        fields = fields_for(rtype)
        cooldown = 30.0
        if self.ed_cooldown is not None:
            cooldown = float(self.ed_cooldown.value())
        data: Dict[str, Any] = {
            "name": self.ed_name.text().strip() or "Unnamed Rule",
            "rule_type": rtype,
            "camera_id": self.ed_camera.currentData() or "*",
            "object_type": self.ed_object.currentText(),
            "severity": self.ed_severity.currentText(),
            "enabled": self.ed_enabled.isChecked(),
            "cooldown_sec": cooldown,
            "zone": self.zone_drawer.get_zone() or None,
        }
        if "duration" in fields and self.ed_duration is not None:
            data["duration_sec"] = float(self.ed_duration.value())
        if "min_count" in fields and self.ed_min_count is not None:
            data["min_count"] = int(self.ed_min_count.value())
        if "window" in fields and self.ed_window is not None:
            data["window_sec"] = float(self.ed_window.value())
        if "direction" in fields and self.ed_direction is not None:
            data["direction_deg"] = float(self.ed_direction.value())
            data["direction_tolerance_deg"] = float(self.ed_dir_tol.value()) if self.ed_dir_tol else 45.0
        if "speed_threshold" in fields and self.ed_speed is not None:
            data["speed_threshold"] = float(self.ed_speed.value())
        if getattr(self, "ed_sched_start", None) is not None:
            s = self.ed_sched_start.value()
            e = self.ed_sched_end.value()
            data["schedule_start_hour"] = None if s < 0 else s
            data["schedule_end_hour"] = None if e < 0 else e
        if getattr(self, "ed_record", None) is not None:
            data["record_on_alert"] = self.ed_record.isChecked()
        zone = data.get("zone")
        if "line" in fields and zone and len(zone) >= 2:
            # longest edge of drawn points = virtual line
            best = zone[:2]
            best_d = -1.0
            n = len(zone)
            for i in range(n if n > 2 else 1):
                a = zone[i]
                b = zone[(i + 1) % n] if n > 2 else zone[min(i + 1, n - 1)]
                d = (float(a[0]) - float(b[0])) ** 2 + (float(a[1]) - float(b[1])) ** 2
                if d > best_d:
                    best_d = d
                    best = [a, b]
            data["line"] = best
            if not data.get("zone") or len(zone) < 3:
                data["zone"] = zone  # keep for display
        return data

    def _save_rule(self) -> None:
        data = self._collect_form()
        if not data["name"]:
            QMessageBox.warning(self, "Validation", "Rule name is required.")
            return
        try:
            if self._editing_id:
                self.rule_mgr.update_rule(self._editing_id, data)
                QMessageBox.information(self, "Saved", f"Rule updated: {data['name']}")
            else:
                self.rule_mgr.create_rule(data)
                QMessageBox.information(self, "Saved", f"Rule created: {data['name']}")
            self._refresh_rules_table()
            self._new_rule()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _toggle_rule(self) -> None:
        r = self._selected_rule()
        if not r:
            return
        self.rule_mgr.set_enabled(r.rule_id, not r.enabled)
        self._refresh_rules_table()

    def _delete_rule(self) -> None:
        r = self._selected_rule()
        if not r:
            return
        if QMessageBox.question(
            self, "Delete", f"Delete rule «{r.name}»?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        self.rule_mgr.delete_rule(r.rule_id)
        self._refresh_rules_table()
        self._new_rule()

    def _load_zone_frame(self) -> None:
        """Grab last frame from running stream for selected camera, or placeholder."""
        cam_id = self.ed_camera.currentData()
        frame = None
        if self.video_service and cam_id and cam_id not in ("*", ""):
            try:
                # StreamManager may expose last frames via workers
                sm = getattr(self.video_service, "stream_manager", None) or getattr(
                    self.video_service, "_manager", None
                )
                if sm is None and hasattr(self.video_service, "stream_manager"):
                    sm = self.video_service.stream_manager
            except Exception:
                sm = None
        # Fallback: solid dark placeholder so user can still draw relative coords
        import numpy as np
        frame = np.zeros((480, 854, 3), dtype=np.uint8)
        frame[:] = (30, 40, 50)
        # draw grid
        import cv2
        for x in range(0, 854, 50):
            cv2.line(frame, (x, 0), (x, 480), (45, 55, 65), 1)
        for y in range(0, 480, 50):
            cv2.line(frame, (0, y), (854, y), (45, 55, 65), 1)
        cv2.putText(
            frame, "Zone canvas — click to draw polygon",
            (40, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 1, cv2.LINE_AA,
        )
        self.zone_drawer.set_frame(frame)
        # restore zone if editing
        r = self._selected_rule()
        if r and r.zone:
            self.zone_drawer.set_zone(r.zone)

    # ══════════════════════════════════════════════════════════════
    # HISTORY TAB
    # ══════════════════════════════════════════════════════════════

    def _build_history_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 8, 0, 0)

        filters = QHBoxLayout()
        self.f_rule = QComboBox()
        self.f_rule.addItem("All rules", "")
        self.f_cam = QComboBox()
        self.f_cam.addItem("All cameras", "")
        self.f_type = QComboBox()
        self.f_type.addItem("All types", "")
        for k in list_rule_types():
            self.f_type.addItem(rule_type_label(k), k)
        self.f_status = QComboBox()
        self.f_status.addItems(["All status", "new", "acknowledged", "resolved"])
        for cb in (self.f_rule, self.f_cam, self.f_type, self.f_status):
            cb.setMinimumWidth(120)
            filters.addWidget(cb)

        btn_ref = QPushButton("Refresh")
        btn_ref.setObjectName("toolBtn")
        btn_ref.clicked.connect(self._refresh_history)
        filters.addWidget(btn_ref)
        btn_ack = QPushButton("Acknowledge")
        btn_ack.setObjectName("toolBtn")
        btn_ack.clicked.connect(self._hist_ack)
        filters.addWidget(btn_ack)
        btn_res = QPushButton("Resolve")
        btn_res.setObjectName("toolBtn")
        btn_res.clicked.connect(self._hist_resolve)
        filters.addWidget(btn_res)
        filters.addStretch()
        layout.addLayout(filters)

        self.hist_table = QTableWidget(0, 9)
        self.hist_table.setHorizontalHeaderLabels([
            "Time", "Rule", "Type", "Camera", "Object/Track",
            "Duration/Count", "Severity", "Status", "Description",
        ])
        self.hist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.hist_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.hist_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._style_table(self.hist_table)
        layout.addWidget(self.hist_table)

        self._hist_rows = []
        self._refresh_filter_combos()
        self._refresh_history()
        return w

    def _refresh_filter_combos(self) -> None:
        self.f_rule.blockSignals(True)
        cur = self.f_rule.currentData()
        self.f_rule.clear()
        self.f_rule.addItem("All rules", "")
        for r in self.rule_mgr.list_rules():
            self.f_rule.addItem(r.name, r.name)
        self.f_rule.blockSignals(False)

        self.f_cam.blockSignals(True)
        self.f_cam.clear()
        self.f_cam.addItem("All cameras", "")
        try:
            for c in self.camera_svc.list_cameras():
                self.f_cam.addItem(c.name, c.camera_id)
        except Exception:
            pass
        self.f_cam.blockSignals(False)

    def _refresh_history(self) -> None:
        rule = self.f_rule.currentData() or None
        cam = self.f_cam.currentData() or None
        atype = self.f_type.currentData() or None
        st = self.f_status.currentText()
        status = None if st == "All status" else st
        try:
            rows = self.alert_mgr.recent(
                limit=300,
                rule_name=rule,
                camera_id=cam,
                activity_type=atype,
                status=status,
            )
        except Exception:
            rows = []
        self._hist_rows = rows
        self.hist_table.setRowCount(0)
        for e in rows:
            row = self.hist_table.rowCount()
            self.hist_table.insertRow(row)
            track = str(e.track_id) if e.track_id is not None else (e.object_type or "—")
            metric = "—"
            if e.duration_sec is not None:
                metric = f"{int(e.duration_sec)}s"
            elif e.count_value is not None:
                metric = str(e.count_value)
            vals = [
                e.timestamp.strftime("%Y-%m-%d %H:%M:%S") if e.timestamp else "—",
                e.rule_name,
                rule_type_label(e.activity_type) if e.activity_type else e.activity_type,
                e.camera_id,
                track,
                metric,
                e.severity,
                e.status,
                (e.description or "—")[:80],
            ]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                if col == 6:
                    item.setForeground(QColor(SEVERITY_COLORS.get(str(v), "#EAEAEA")))
                self.hist_table.setItem(row, col, item)

    def _hist_selected_id(self) -> Optional[str]:
        rows = self.hist_table.selectionModel().selectedRows()
        if not rows:
            return None
        idx = rows[0].row()
        if 0 <= idx < len(self._hist_rows):
            return self._hist_rows[idx].activity_id
        return None

    def _hist_ack(self) -> None:
        aid = self._hist_selected_id()
        if not aid:
            QMessageBox.information(self, "Select", "Select a row first.")
            return
        self.alert_mgr.acknowledge(aid)
        self._refresh_history()

    def _hist_resolve(self) -> None:
        aid = self._hist_selected_id()
        if not aid:
            QMessageBox.information(self, "Select", "Select a row first.")
            return
        self.alert_mgr.resolve(aid)
        self._refresh_history()

    # ══════════════════════════════════════════════════════════════
    # TEST TAB
    # ══════════════════════════════════════════════════════════════

    def _build_test_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        hint = QLabel(
            "Inject synthetic detections into the Analytics Engine using the existing pipeline path.\n"
            "Requires at least one saved & enabled rule of the matching type. Results appear in Activity History."
        )
        hint.setObjectName("pageHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.test_camera = QComboBox()
        self._reload_test_cameras()
        row = QHBoxLayout()
        row.addWidget(QLabel("Camera for test:"))
        row.addWidget(self.test_camera)
        row.addStretch()
        layout.addLayout(row)

        grid = QHBoxLayout()
        tests = [
            ("Test Restricted Zone", "restricted_zone"),
            ("Test Loitering", "loitering"),
            ("Test Crowd", "crowd"),
            ("Test Wrong Direction", "wrong_direction"),
            ("Test Stopped Vehicle", "stopped_vehicle"),
            ("Test Abnormal Movement", "abnormal_movement"),
            ("Test Unknown Face", "unknown_face"),
            ("Test Line Crossing", "line_crossing"),
        ]
        for label, key in tests:
            btn = QPushButton(label)
            btn.setObjectName("toolBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(36)
            btn.clicked.connect(lambda checked=False, k=key: self._run_test(k))
            grid.addWidget(btn)
        layout.addLayout(grid)

        self.test_log = QLabel("Ready.")
        self.test_log.setWordWrap(True)
        self.test_log.setStyleSheet(
            "background:#0D1A2A; border:1px solid #1C2B3C; padding:10px; color:#9A9A9A;"
        )
        self.test_log.setMinimumHeight(120)
        layout.addWidget(self.test_log)
        layout.addStretch()
        return w

    def _reload_test_cameras(self) -> None:
        self.test_camera.clear()
        try:
            cams = self.camera_svc.list_cameras()
            for c in cams:
                self.test_camera.addItem(f"{c.name} ({c.camera_id})", c.camera_id)
            if not cams:
                self.test_camera.addItem("demo_cam", "demo_cam")
        except Exception:
            self.test_camera.addItem("demo_cam", "demo_cam")

    def _run_test(self, rule_type: str) -> None:
        from core.contracts import DetectionResult, BoundingBox
        from datetime import datetime

        cam_id = self.test_camera.currentData() or "demo_cam"
        # Ensure a matching enabled rule exists (create temp if needed)
        matching = [
            r for r in self.rule_mgr.list_rules(enabled_only=True)
            if r.rule_type == rule_type and r.camera_id in ("*", "", cam_id)
        ]
        if not matching:
            # auto-create a test rule
            defs = defaults_for(rule_type)
            data = {
                "name": f"[TEST] {rule_type_label(rule_type)}",
                "rule_type": rule_type,
                "camera_id": cam_id,
                "object_type": defs.get("object_type", "person"),
                "severity": defs.get("severity", "medium"),
                "enabled": True,
                "cooldown_sec": 5,
                "zone": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]],
                "duration_sec": defs.get("duration_sec", 1),
                "min_count": defs.get("min_count", 2),
                "window_sec": defs.get("window_sec", 60),
                "direction_deg": defs.get("direction_deg", 0),
                "direction_tolerance_deg": defs.get("direction_tolerance_deg", 30),
                "speed_threshold": defs.get("speed_threshold", 0.05),
            }
            # force short thresholds for test
            if rule_type in ("loitering", "stopped_vehicle", "unattended_object"):
                data["duration_sec"] = 1
            if rule_type == "crowd":
                data["min_count"] = 2
            self.rule_mgr.create_rule(data)
            self._refresh_rules_table()

        now = datetime.utcnow()
        dets = []

        def make_det(cls, tid, x1, y1, x2, y2, conf=0.9):
            return DetectionResult(
                camera_id=cam_id,
                timestamp=now,
                class_name=cls,
                confidence=conf,
                bounding_box=BoundingBox(x1, y1, x2, y2),
                track_id=tid,
            )

        # Synthetic sequences
        if rule_type == "crowd":
            dets = [
                make_det("person", i, 100 + i * 40, 100, 140 + i * 40, 200)
                for i in range(5)
            ]
            created = self._analytics.process(cam_id, now, dets, frame_size=(640, 480))
        elif rule_type == "restricted_zone":
            dets = [make_det("person", 1, 300, 300, 360, 400)]  # center of zone
            created = self._analytics.process(cam_id, now, dets, frame_size=(640, 480))
        elif rule_type == "loitering":
            # simulate same track over time via state
            dets = [make_det("person", 42, 300, 300, 360, 400)]
            t0 = now - timedelta(seconds=5)
            self._analytics.process(cam_id, t0, dets, frame_size=(640, 480))
            created = self._analytics.process(cam_id, now, dets, frame_size=(640, 480))
        elif rule_type == "wrong_direction":
            # move left while allowed is 0° (right)
            d1 = make_det("person", 7, 400, 200, 460, 300)
            d2 = make_det("person", 7, 300, 200, 360, 300)
            d3 = make_det("person", 7, 200, 200, 260, 300)
            self._analytics.process(cam_id, now - timedelta(seconds=2), [d1], frame_size=(640, 480))
            self._analytics.process(cam_id, now - timedelta(seconds=1), [d2], frame_size=(640, 480))
            created = self._analytics.process(cam_id, now, [d3], frame_size=(640, 480))
        elif rule_type == "stopped_vehicle":
            d = make_det("car", 9, 300, 300, 400, 380)
            t0 = now - timedelta(seconds=5)
            self._analytics.process(cam_id, t0, [d], frame_size=(640, 480))
            self._analytics.process(cam_id, t0 + timedelta(seconds=2), [d], frame_size=(640, 480))
            created = self._analytics.process(cam_id, now, [d], frame_size=(640, 480))
        elif rule_type == "abnormal_movement":
            d1 = make_det("person", 3, 100, 200, 160, 300)
            d2 = make_det("person", 3, 400, 200, 460, 300)  # large jump
            self._analytics.process(cam_id, now - timedelta(seconds=1), [d1], frame_size=(640, 480))
            created = self._analytics.process(cam_id, now, [d2], frame_size=(640, 480))
        elif rule_type == "unknown_face":
            from core.contracts import FaceResult, BoundingBox, MatchStatus
            face = FaceResult(
                camera_id=cam_id,
                timestamp=now,
                bounding_box=BoundingBox(200, 150, 280, 250),
                confidence=0.92,
                match_status=MatchStatus.UNKNOWN,
                similarity=0.1,
                name=None,
            )
            created = self._analytics.process(
                cam_id, now, detections=[], faces=[face], frame_size=(640, 480)
            )
        elif rule_type == "line_crossing":
            # horizontal line mid-frame; car moves top→bottom across it
            # ensure a line_crossing rule exists with line [[0,0.5],[1,0.5]]
            rules = [r for r in self.rule_mgr.list_rules(enabled_only=True)
                     if r.rule_type == "line_crossing"]
            if not rules:
                self.rule_mgr.create_rule({
                    "name": "Test Line",
                    "rule_type": "line_crossing",
                    "camera_id": cam_id,
                    "object_type": "vehicle",
                    "line": [[0.0, 0.5], [1.0, 0.5]],
                    "cooldown_sec": 1,
                    "enabled": True,
                    "severity": "medium",
                })
            else:
                # patch first rule line for test reliability
                self.rule_mgr.update_rule(rules[0].rule_id, {
                    "line": [[0.0, 0.5], [1.0, 0.5]],
                    "object_type": "vehicle",
                    "cooldown_sec": 1,
                    "enabled": True,
                })
            d1 = make_det("car", 7, 300, 100, 380, 160)
            d2 = make_det("car", 7, 300, 300, 380, 360)
            self._analytics.process(cam_id, now - timedelta(seconds=0.5), [d1], frame_size=(640, 480))
            created = self._analytics.process(cam_id, now, [d2], frame_size=(640, 480))
        else:
            created = []

        msg = (
            f"Test «{rule_type_label(rule_type)}» on camera {cam_id}: "
            f"{len(created)} alert(s) created."
        )
        if created:
            msg += "\n" + "\n".join(f"  • {c.rule_name}: {c.description}" for c in created)
        else:
            msg += "\n(No alert — check rule thresholds / cooldown, or run again.)"
        self.test_log.setText(msg)
        self._refresh_history()
        self.tabs.setCurrentIndex(1)  # jump to history


    def _apply_template(self) -> None:
        """Create a pack of pre-defined rules for the selected camera."""
        from PySide6.QtWidgets import QInputDialog
        names = [t["name"] for t in RULE_TEMPLATES]
        if not names:
            QMessageBox.information(self, "Templates", "No templates available.")
            return
        name, ok = QInputDialog.getItem(self, "Template", "Choose pack:", names, 0, False)
        if not ok:
            return
        tpl = next(x for x in RULE_TEMPLATES if x["name"] == name)
        cam = self.ed_camera.currentData() or "*"
        n = 0
        errors = []
        for r in tpl["rules"]:
            data = {
                "name": r["name"],
                "rule_type": r["rule_type"],
                "camera_id": cam,
                "enabled": True,
                "severity": r.get("severity", "medium"),
                "cooldown_sec": float(r.get("cooldown_sec", 30)),
                "object_type": r.get("object_type", "person"),
            }
            if r.get("duration_sec") is not None:
                data["duration_sec"] = float(r["duration_sec"])
            if r.get("min_count") is not None:
                data["min_count"] = int(r["min_count"])
            if r.get("schedule_start_hour") is not None:
                data["schedule_start_hour"] = int(r["schedule_start_hour"])
            if r.get("schedule_end_hour") is not None:
                data["schedule_end_hour"] = int(r["schedule_end_hour"])
            try:
                self.rule_mgr.create_rule(data)
                n += 1
            except Exception as e:
                errors.append(f"{r.get('name')}: {e}")
        self._refresh_rules_table()
        msg = f"Created {n} rules from «{name}»."
        if errors:
            msg += "\n\nSome failed:\n" + "\n".join(errors[:5])
        QMessageBox.information(self, "Template", msg)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._reload_cameras()
        self._reload_test_cameras()
        self._refresh_rules_table()
        self._refresh_filter_combos()
