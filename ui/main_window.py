import cv2
from datetime import datetime, date

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QDialog,
    QFormLayout,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QHeaderView,
    QFrame,
    QSizePolicy,
)

from ui.theme import STYLE
from video_engine.source import VideoSource
from ai_engine.yolo import YOLODetector
from security_engine.virtual_fence import VirtualFence
from core.contracts import SecurityEvent
from database.repository import CameraRepository


# ============================================================
# VIDEO WORKER
# ============================================================

class Worker(QThread):

    frame_ready = Signal(object)
    event_ready = Signal(object)
    status_changed = Signal(str)

    def __init__(
        self,
        source,
        camera_name,
        model_path,
        confidence,
        iou,
        imgsz,
        fence_enabled=False,
        fence_points=None,
    ):
        super().__init__()

        self.source_value = source
        self.camera_name = camera_name

        self.model_path = model_path
        self.confidence = confidence
        self.iou = iou
        self.imgsz = imgsz

        self.fence_enabled = fence_enabled
        self.fence_points = fence_points or []

        self.running = False
        self.video = None
        self.detector = None
        self.fence = None

    def run(self):

        self.running = True

        # ----------------------------------------------------
        # Video source
        # ----------------------------------------------------

        self.video = VideoSource(
            self.source_value
        )

        if not self.video.open():

            self.status_changed.emit(
                "OFFLINE"
            )

            return

        self.status_changed.emit(
            "ONLINE"
        )

        # ----------------------------------------------------
        # YOLO
        # ----------------------------------------------------

        self.detector = YOLODetector(
            model_path=self.model_path,
            confidence=self.confidence,
            iou=self.iou,
        )

        self.detector.load()

        # ----------------------------------------------------
        # Virtual fence
        # ----------------------------------------------------

        if self.fence_points:

            self.fence = VirtualFence(
                self.fence_points,
                enabled=self.fence_enabled,
            )

        # ----------------------------------------------------
        # Processing loop
        # ----------------------------------------------------

        while self.running:

            ok, frame = self.video.read()

            if not ok:

                self.status_changed.emit(
                    "OFFLINE"
                )

                break

            detections = []

            # ------------------------------------------------
            # AI detection
            # ------------------------------------------------

            try:

                if self.detector:

                    detections = self.detector.infer(
                        frame,
                        imgsz=self.imgsz,
                        tracking=True,
                    )

            except Exception as exc:

                print(
                    "Detection error:",
                    exc
                )

                detections = []

            # ------------------------------------------------
            # Virtual fence
            # ------------------------------------------------

            if self.fence:

                try:

                    intrusions = (
                        self.fence.check(
                            detections
                        )
                    )

                    for detection in intrusions:

                        event = SecurityEvent(
                            event_type="Virtual Fence Intrusion",
                            severity="HIGH",
                            camera=self.camera_name,
                            timestamp=datetime.now(),
                            message=(
                                f"{detection.label} "
                                f"entered restricted zone"
                            ),
                            detection=detection,
                        )

                        self.event_ready.emit(
                            event
                        )

                except Exception as exc:

                    print(
                        "Fence error:",
                        exc
                    )

            # ------------------------------------------------
            # Draw detections
            # ------------------------------------------------

            display = frame.copy()

            for detection in detections:

                x1, y1, x2, y2 = (
                    detection.bbox
                )

                cv2.rectangle(
                    display,
                    (x1, y1),
                    (x2, y2),
                    (0, 220, 180),
                    2,
                )

                label = detection.label

                if detection.track_id is not None:

                    label += (
                        f" #{detection.track_id}"
                    )

                label += (
                    f" {detection.confidence:.0%}"
                )

                cv2.putText(
                    display,
                    label,
                    (
                        x1,
                        max(
                            20,
                            y1 - 8
                        ),
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 220, 180),
                    2,
                    cv2.LINE_AA,
                )

            # ------------------------------------------------
            # Draw virtual fence
            # ------------------------------------------------

            if (
                self.fence_points
                and len(self.fence_points) >= 3
            ):

                points = [
                    (
                        int(x),
                        int(y)
                    )
                    for x, y
                    in self.fence_points
                ]

                for index in range(
                    len(points)
                ):

                    p1 = points[index]

                    p2 = points[
                        (index + 1)
                        % len(points)
                    ]

                    cv2.line(
                        display,
                        p1,
                        p2,
                        (0, 180, 255),
                        2,
                    )

            self.frame_ready.emit(
                display
            )

        # ----------------------------------------------------
        # Cleanup
        # ----------------------------------------------------

        if self.video:

            self.video.release()

        self.status_changed.emit(
            "OFFLINE"
        )

    def stop(self):

        self.running = False

        if self.video:

            self.video.release()


# ============================================================
# SECTION TITLE
# ============================================================

class SectionTitle(QLabel):

    def __init__(self, text):

        super().__init__(
            text
        )

        self.setObjectName(
            "sectionTitle"
        )


# ============================================================
# MAIN WINDOW
# ============================================================

class MainWindow(QMainWindow):

    def __init__(self, config, repo):

        super().__init__()

        # IMPORTANT:
        # bootstrap.py calls:
        #
        # MainWindow(cfg, repo)
        #
        # Therefore config comes first.

        self.config = config
        self.repo = repo

        self.worker = None
        self.current_camera_id = None

        # ----------------------------------------------------
        # Camera repository
        # ----------------------------------------------------

        self.camera_repo = CameraRepository(
            self.repo.session
        )

        self.setWindowTitle(
            "IBVAP Command Center"
        )

        self.resize(
            1366,
            768
        )

        self.setMinimumSize(
            1100,
            650
        )

        self.setStyleSheet(
            STYLE + self._local_style()
        )

        self._build()

        self.refresh_cameras()
        self.refresh_events()
        self.refresh_dashboard()

    # ========================================================
    # LOCAL STYLE
    # ========================================================

    def _local_style(self):

        return """

        QMainWindow {
            background: #07111d;
        }

        QWidget {
            color: #e6edf5;
            font-family: "Segoe UI";
        }

        QLabel#pageTitle {
            font-size: 24px;
            font-weight: 600;
            color: #f3f7fb;
        }

        QLabel#pageSubtitle {
            font-size: 12px;
            color: #7f9ab5;
        }

        QLabel#sectionTitle {
            font-size: 13px;
            font-weight: 600;
            color: #dce8f3;
        }

        QFrame#panel {
            background: #0b1927;
            border: 1px solid #19364c;
            border-radius: 7px;
        }

        QFrame#metric {
            background: #0b1927;
            border: 1px solid #19364c;
            border-radius: 7px;
        }

        QLabel#metricTitle {
            font-size: 11px;
            color: #8ba4bb;
        }

        QLabel#metricValue {
            font-size: 25px;
            font-weight: 600;
            color: #f2f6fa;
        }

        QPushButton#navButton {
            text-align: left;
            padding: 10px 14px;
            border-radius: 5px;
            border: 1px solid transparent;
            background: transparent;
            color: #aebfd0;
        }

        QPushButton#navButton:hover {
            background: #0e2234;
            color: #ffffff;
        }

        QPushButton#navButton:checked {
            background: #102a40;
            border: 1px solid #1b4865;
            color: #ffffff;
        }

        QPushButton#primaryButton {
            background: #0d7f76;
            border: 1px solid #159b90;
            border-radius: 5px;
            padding: 8px 15px;
            color: white;
        }

        QPushButton#primaryButton:hover {
            background: #119287;
        }

        QPushButton#secondaryButton {
            background: #102233;
            border: 1px solid #23445c;
            border-radius: 5px;
            padding: 8px 15px;
            color: #d8e5ef;
        }

        QPushButton#secondaryButton:hover {
            background: #142d43;
        }

        QPushButton#dangerButton {
            background: #331b20;
            border: 1px solid #6a303a;
            border-radius: 5px;
            padding: 8px 15px;
            color: #ffb7c0;
        }

        QLineEdit,
        QComboBox {

            background: #091724;
            border: 1px solid #24445c;
            border-radius: 5px;
            padding: 7px 9px;
            color: #e7eef5;
        }

        QLineEdit:focus,
        QComboBox:focus {
            border: 1px solid #258d9c;
        }

        QTableWidget {

            background: #091724;
            border: 1px solid #19364c;
            gridline-color: #132b3c;
            selection-background-color: #12384d;
            selection-color: white;
            alternate-background-color: #0b1b2a;
        }

        QHeaderView::section {

            background: #102438;
            color: #9fb5c8;
            border: none;
            border-right: 1px solid #1b3448;
            border-bottom: 1px solid #19364c;
            padding: 8px;
            font-size: 11px;
            font-weight: 500;
        }

        QListWidget {

            background: #091724;
            border: 1px solid #19364c;
            border-radius: 6px;
        }

        QListWidget::item {

            padding: 9px;
            border-bottom: 1px solid #142c3e;
        }

        QListWidget::item:selected {
            background: #12384d;
        }

        QLabel#videoScreen {

            background: #02070c;
            border: 1px solid #19364c;
            border-radius: 6px;
        }

        """

    # ========================================================
    # BUILD
    # ========================================================

    def _build(self):

        root = QWidget()

        self.setCentralWidget(
            root
        )

        main_layout = QHBoxLayout(
            root
        )

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        main_layout.setSpacing(
            0
        )

        # ----------------------------------------------------
        # SIDEBAR
        # ----------------------------------------------------

        sidebar = QFrame()

        sidebar.setFixedWidth(
            150
        )

        sidebar.setStyleSheet(
            """
            QFrame {
                background: #07111d;
                border-right: 1px solid #172d3e;
            }
            """
        )

        side_layout = QVBoxLayout(
            sidebar
        )

        side_layout.setContentsMargins(
            16,
            22,
            16,
            16
        )

        side_layout.setSpacing(
            6
        )

        logo = QLabel(
            "IBVAP"
        )

        logo.setStyleSheet(
            """
            font-size: 24px;
            font-weight: 700;
            color: white;
            """
        )

        subtitle = QLabel(
            "COMMAND CENTER"
        )

        subtitle.setStyleSheet(
            """
            font-size: 10px;
            color: #7692aa;
            letter-spacing: 1px;
            """
        )

        side_layout.addWidget(
            logo
        )

        side_layout.addWidget(
            subtitle
        )

        side_layout.addSpacing(
            28
        )

        self.nav_buttons = []

        pages = [
            (
                "Dashboard",
                self._dashboard_page()
            ),
            (
                "Live Feed",
                self._live_page()
            ),
            (
                "Cameras",
                self._camera_page()
            ),
            (
                "Events",
                self._events_page()
            ),
        ]

        self.stack = QStackedWidget()

        for index, (
            name,
            page
        ) in enumerate(pages):

            button = QPushButton(
                name
            )

            button.setObjectName(
                "navButton"
            )

            button.setCheckable(
                True
            )

            if index == 0:
                button.setChecked(
                    True
                )

            button.clicked.connect(
                lambda checked=False,
                i=index:
                self._navigate(i)
            )

            self.nav_buttons.append(
                button
            )

            side_layout.addWidget(
                button
            )

            self.stack.addWidget(
                page
            )

        side_layout.addStretch()

        edge_label = QLabel(
            "● OFFLINE / EDGE"
        )

        edge_label.setStyleSheet(
            """
            color: #6f899e;
            font-size: 10px;
            """
        )

        side_layout.addWidget(
            edge_label
        )

        main_layout.addWidget(
            sidebar
        )

        main_layout.addWidget(
            self.stack,
            1
        )

    # ========================================================
    # NAVIGATION
    # ========================================================

    def _navigate(
        self,
        index
    ):

        self.stack.setCurrentIndex(
            index
        )

        for i, button in enumerate(
            self.nav_buttons
        ):

            button.setChecked(
                i == index
            )

        if index == 0:

            self.refresh_dashboard()

        elif index == 2:

            self.refresh_cameras()

        elif index == 3:

            self.refresh_events()

    # ========================================================
    # PAGE HEADER
    # ========================================================

    def _page_header(
        self,
        title,
        subtitle
    ):

        widget = QWidget()

        layout = QVBoxLayout(
            widget
        )

        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        layout.setSpacing(
            3
        )

        title_label = QLabel(
            title
        )

        title_label.setObjectName(
            "pageTitle"
        )

        subtitle_label = QLabel(
            subtitle
        )

        subtitle_label.setObjectName(
            "pageSubtitle"
        )

        layout.addWidget(
            title_label
        )

        layout.addWidget(
            subtitle_label
        )

        return widget

    # ========================================================
    # DASHBOARD
    # ========================================================

    def _dashboard_page(self):

        page = QWidget()

        layout = QVBoxLayout(
            page
        )

        layout.setContentsMargins(
            28,
            22,
            8,
            20
        )

        layout.setSpacing(
            18
        )

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        header = QHBoxLayout()

        header.addWidget(
            self._page_header(
                "Dashboard",
                "IBVAP • Intelligent Border Video Analytics Platform"
            )
        )

        header.addStretch()

        self.system_status = QLabel(
            "● SYSTEM ONLINE"
        )

        self.system_status.setStyleSheet(
            """
            color: #22d3a7;
            border: 1px solid #185e5a;
            border-radius: 5px;
            padding: 9px 14px;
            font-size: 11px;
            """
        )

        header.addWidget(
            self.system_status
        )

        layout.addLayout(
            header
        )

        # ----------------------------------------------------
        # METRICS
        # ----------------------------------------------------

        metrics = QHBoxLayout()

        metrics.setSpacing(
            8
        )

        self.total_camera_value = (
            self._metric(
                metrics,
                "CAMERAS"
            )
        )

        self.online_camera_value = (
            self._metric(
                metrics,
                "ONLINE"
            )
        )

        self.alert_value = (
            self._metric(
                metrics,
                "ACTIVE ALERTS"
            )
        )

        self.events_today_value = (
            self._metric(
                metrics,
                "EVENTS TODAY"
            )
        )

        layout.addLayout(
            metrics
        )

        # ----------------------------------------------------
        # CAMERA STATUS + ALERTS
        # ----------------------------------------------------

        upper = QHBoxLayout()

        upper.setSpacing(
            12
        )

        # Camera panel

        camera_panel = QFrame()

        camera_panel.setObjectName(
            "panel"
        )

        camera_layout = QVBoxLayout(
            camera_panel
        )

        camera_layout.setContentsMargins(
            14,
            12,
            14,
            12
        )

        camera_layout.addWidget(
            SectionTitle(
                "Camera Status"
            )
        )

        self.dashboard_camera_table = (
            QTableWidget()
        )

        self.dashboard_camera_table.setColumnCount(
            4
        )

        self.dashboard_camera_table.setHorizontalHeaderLabels(
            [
                "Camera",
                "Location",
                "Status",
                "Source"
            ]
        )

        self._prepare_table(
            self.dashboard_camera_table
        )

        camera_layout.addWidget(
            self.dashboard_camera_table
        )

        upper.addWidget(
            camera_panel,
            3
        )

        # Alert panel

        alert_panel = QFrame()

        alert_panel.setObjectName(
            "panel"
        )

        alert_layout = QVBoxLayout(
            alert_panel
        )

        alert_layout.setContentsMargins(
            14,
            12,
            14,
            12
        )

        alert_layout.addWidget(
            SectionTitle(
                "Active Alerts"
            )
        )

        self.dashboard_alert_list = (
            QListWidget()
        )

        alert_layout.addWidget(
            self.dashboard_alert_list
        )

        upper.addWidget(
            alert_panel,
            2
        )

        layout.addLayout(
            upper,
            1
        )

        # ----------------------------------------------------
        # RECENT EVENTS
        # ----------------------------------------------------

        event_panel = QFrame()

        event_panel.setObjectName(
            "panel"
        )

        event_layout = QVBoxLayout(
            event_panel
        )

        event_layout.setContentsMargins(
            14,
            12,
            14,
            12
        )

        event_layout.addWidget(
            SectionTitle(
                "Recent Security Events"
            )
        )

        self.dashboard_event_table = (
            QTableWidget()
        )

        self.dashboard_event_table.setColumnCount(
            5
        )

        self.dashboard_event_table.setHorizontalHeaderLabels(
            [
                "Time",
                "Camera",
                "Event",
                "Confidence",
                "Severity"
            ]
        )

        self._prepare_table(
            self.dashboard_event_table
        )

        event_layout.addWidget(
            self.dashboard_event_table
        )

        layout.addWidget(
            event_panel,
            1
        )

        return page

    # ========================================================
    # METRIC
    # ========================================================

    def _metric(
        self,
        parent_layout,
        title
    ):

        frame = QFrame()

        frame.setObjectName(
            "metric"
        )

        layout = QVBoxLayout(
            frame
        )

        layout.setContentsMargins(
            12,
            10,
            12,
            10
        )

        title_label = QLabel(
            title
        )

        title_label.setObjectName(
            "metricTitle"
        )

        value_label = QLabel(
            "0"
        )

        value_label.setObjectName(
            "metricValue"
        )

        layout.addWidget(
            title_label
        )

        layout.addWidget(
            value_label
        )

        parent_layout.addWidget(
            frame
        )

        return value_label

    # ========================================================
    # LIVE PAGE
    # ========================================================

    def _live_page(self):

        page = QWidget()

        layout = QVBoxLayout(
            page
        )

        layout.setContentsMargins(
            28,
            22,
            8,
            20
        )

        layout.setSpacing(
            14
        )

        header = QHBoxLayout()

        header.addWidget(
            self._page_header(
                "Live Feed",
                "Real-time camera monitoring and AI detection"
            )
        )

        header.addStretch()

        self.live_status = QLabel(
            "● NO CAMERA"
        )

        self.live_status.setStyleSheet(
            """
            color: #8ca2b5;
            border: 1px solid #28465b;
            border-radius: 5px;
            padding: 8px 12px;
            """
        )

        header.addWidget(
            self.live_status
        )

        layout.addLayout(
            header
        )

        # ----------------------------------------------------
        # TOOLBAR
        # ----------------------------------------------------

        toolbar = QHBoxLayout()

        toolbar.addWidget(
            QLabel(
                "Camera:"
            )
        )

        self.live_camera_combo = (
            QComboBox()
        )

        self.live_camera_combo.setMinimumWidth(
            280
        )

        refresh_btn = QPushButton(
            "Refresh"
        )

        refresh_btn.setObjectName(
            "secondaryButton"
        )

        refresh_btn.clicked.connect(
            self.refresh_live_camera_list
        )

        open_btn = QPushButton(
            "Open Feed"
        )

        open_btn.setObjectName(
            "primaryButton"
        )

        open_btn.clicked.connect(
            self.open_live_feed
        )

        stop_btn = QPushButton(
            "Stop"
        )

        stop_btn.setObjectName(
            "dangerButton"
        )

        stop_btn.clicked.connect(
            self.stop_stream
        )

        toolbar.addWidget(
            self.live_camera_combo
        )

        toolbar.addWidget(
            refresh_btn
        )

        toolbar.addWidget(
            open_btn
        )

        toolbar.addWidget(
            stop_btn
        )

        toolbar.addStretch()

        layout.addLayout(
            toolbar
        )

        # ----------------------------------------------------
        # VIDEO
        # ----------------------------------------------------

        video_frame = QFrame()

        video_frame.setObjectName(
            "panel"
        )

        video_layout = QVBoxLayout(
            video_frame
        )

        video_layout.setContentsMargins(
            10,
            10,
            10,
            10
        )

        self.video_label = QLabel(
            "NO LIVE FEED"
        )

        self.video_label.setObjectName(
            "videoScreen"
        )

        self.video_label.setAlignment(
            Qt.AlignCenter
        )

        self.video_label.setMinimumHeight(
            450
        )

        self.video_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        video_layout.addWidget(
            self.video_label
        )

        layout.addWidget(
            video_frame,
            1
        )

        return page

    # ========================================================
    # CAMERA PAGE
    # ========================================================

    def _camera_page(self):

        page = QWidget()

        layout = QVBoxLayout(
            page
        )

        layout.setContentsMargins(
            28,
            22,
            8,
            20
        )

        layout.setSpacing(
            14
        )

        header = QHBoxLayout()

        header.addWidget(
            self._page_header(
                "Camera Management",
                "Configure and monitor registered video sources"
            )
        )

        header.addStretch()

        add_btn = QPushButton(
            "Add Camera"
        )

        add_btn.setObjectName(
            "primaryButton"
        )

        add_btn.clicked.connect(
            self.add_camera_dialog
        )

        refresh_btn = QPushButton(
            "Refresh"
        )

        refresh_btn.setObjectName(
            "secondaryButton"
        )

        refresh_btn.clicked.connect(
            self.refresh_cameras
        )

        open_btn = QPushButton(
            "Open Feed"
        )

        open_btn.setObjectName(
            "secondaryButton"
        )

        open_btn.clicked.connect(
            self.open_selected_camera
        )

        delete_btn = QPushButton(
            "Delete"
        )

        delete_btn.setObjectName(
            "dangerButton"
        )

        delete_btn.clicked.connect(
            self.delete_selected_camera
        )

        header.addWidget(
            add_btn
        )

        header.addWidget(
            refresh_btn
        )

        header.addWidget(
            open_btn
        )

        header.addWidget(
            delete_btn
        )

        layout.addLayout(
            header
        )

        # ----------------------------------------------------
        # TABLE
        # ----------------------------------------------------

        self.camera_table = (
            QTableWidget()
        )

        self.camera_table.setColumnCount(
            6
        )

        self.camera_table.setHorizontalHeaderLabels(
            [
                "ID",
                "Camera",
                "Location",
                "Source Type",
                "Source",
                "Status"
            ]
        )

        self._prepare_table(
            self.camera_table
        )

        self.camera_table.itemDoubleClicked.connect(
            lambda item:
            self.open_selected_camera()
        )

        layout.addWidget(
            self.camera_table,
            1
        )

        return page

    # ========================================================
    # EVENTS PAGE
    # ========================================================

    def _events_page(self):

        page = QWidget()

        layout = QVBoxLayout(
            page
        )

        layout.setContentsMargins(
            28,
            22,
            8,
            20
        )

        layout.setSpacing(
            14
        )

        header = QHBoxLayout()

        header.addWidget(
            self._page_header(
                "Security Events",
                "Recorded events generated by the analytics engine"
            )
        )

        header.addStretch()

        refresh_btn = QPushButton(
            "Refresh"
        )

        refresh_btn.setObjectName(
            "secondaryButton"
        )

        refresh_btn.clicked.connect(
            self.refresh_events
        )

        header.addWidget(
            refresh_btn
        )

        layout.addLayout(
            header
        )

        # ----------------------------------------------------
        # FILTER
        # ----------------------------------------------------

        filter_layout = QHBoxLayout()

        filter_layout.addWidget(
            QLabel(
                "Severity:"
            )
        )

        self.event_filter = (
            QComboBox()
        )

        self.event_filter.addItems(
            [
                "ALL",
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "LOW"
            ]
        )

        self.event_filter.currentTextChanged.connect(
            self.refresh_events
        )

        filter_layout.addWidget(
            self.event_filter
        )

        filter_layout.addStretch()

        layout.addLayout(
            filter_layout
        )

        # ----------------------------------------------------
        # TABLE
        # ----------------------------------------------------

        self.event_table = (
            QTableWidget()
        )

        self.event_table.setColumnCount(
            7
        )

        self.event_table.setHorizontalHeaderLabels(
            [
                "Time",
                "Camera",
                "Event",
                "Message",
                "Confidence",
                "Severity",
                "Snapshot"
            ]
        )

        self._prepare_table(
            self.event_table
        )

        layout.addWidget(
            self.event_table,
            1
        )

        return page

    # ========================================================
    # TABLE CONFIG
    # ========================================================

    def _prepare_table(
        self,
        table
    ):

        table.setAlternatingRowColors(
            True
        )

        table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        table.verticalHeader().setVisible(
            False
        )

        table.horizontalHeader().setStretchLastSection(
            True
        )

        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Interactive
        )

        table.setMinimumHeight(
            180
        )

    # ========================================================
    # DASHBOARD REFRESH
    # ========================================================

    def refresh_dashboard(self):

        try:

            cameras = (
                self.camera_repo.get_all()
            )

        except Exception:

            cameras = []

        # ----------------------------------------------------
        # Camera count
        # ----------------------------------------------------

        total = len(
            cameras
        )

        online = 0

        for camera in cameras:

            status = str(
                getattr(
                    camera,
                    "status",
                    "OFFLINE"
                )
            ).upper()

            if status == "ONLINE":

                online += 1

        self.total_camera_value.setText(
            str(total)
        )

        self.online_camera_value.setText(
            str(online)
        )

        # ----------------------------------------------------
        # Camera table
        # ----------------------------------------------------

        self.dashboard_camera_table.setRowCount(
            len(cameras)
        )

        for row, camera in enumerate(
            cameras
        ):

            values = [
                getattr(
                    camera,
                    "name",
                    "-"
                ),
                getattr(
                    camera,
                    "location",
                    "-"
                ),
                getattr(
                    camera,
                    "status",
                    "OFFLINE"
                ),
                getattr(
                    camera,
                    "source_type",
                    "-"
                ),
            ]

            for column, value in enumerate(
                values
            ):

                self.dashboard_camera_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(
                        str(value)
                    )
                )

        # ----------------------------------------------------
        # Events
        # ----------------------------------------------------

        try:

            events = self.repo.recent(
                200
            )

        except Exception:

            events = []

        # ----------------------------------------------------
        # Today
        # ----------------------------------------------------

        today_events = []

        today = date.today()

        for event in events:

            timestamp = getattr(
                event,
                "timestamp",
                None
            )

            if (
                timestamp
                and timestamp.date() == today
            ):

                today_events.append(
                    event
                )

        self.events_today_value.setText(
            str(
                len(today_events)
            )
        )

        # ----------------------------------------------------
        # Active alerts
        # ----------------------------------------------------

        alerts = []

        for event in events:

            severity = str(
                getattr(
                    event,
                    "severity",
                    ""
                )
            ).upper()

            if severity in {
                "HIGH",
                "CRITICAL"
            }:

                alerts.append(
                    event
                )

        self.alert_value.setText(
            str(
                len(alerts)
            )
        )

        self.dashboard_alert_list.clear()

        for event in alerts[:8]:

            timestamp = getattr(
                event,
                "timestamp",
                None
            )

            time_text = (
                timestamp.strftime(
                    "%H:%M:%S"
                )
                if timestamp
                else "--:--:--"
            )

            camera = getattr(
                event,
                "camera",
                "-"
            )

            event_type = getattr(
                event,
                "event_type",
                "Security Event"
            )

            severity = str(
                getattr(
                    event,
                    "severity",
                    "HIGH"
                )
            ).upper()

            item = QListWidgetItem(
                f"{time_text}   {camera}\n"
                f"{event_type}   [{severity}]"
            )

            self.dashboard_alert_list.addItem(
                item
            )

        if not alerts:

            self.dashboard_alert_list.addItem(
                QListWidgetItem(
                    "No active security alerts"
                )
            )

        # ----------------------------------------------------
        # Recent events
        # ----------------------------------------------------

        recent_events = events[:10]

        self.dashboard_event_table.setRowCount(
            len(recent_events)
        )

        for row, event in enumerate(
            recent_events
        ):

            timestamp = getattr(
                event,
                "timestamp",
                None
            )

            time_text = (
                timestamp.strftime(
                    "%H:%M:%S"
                )
                if timestamp
                else "-"
            )

            confidence = getattr(
                event,
                "confidence",
                None
            )

            confidence_text = (
                f"{confidence:.0%}"
                if confidence is not None
                else "-"
            )

            values = [
                time_text,
                getattr(
                    event,
                    "camera",
                    "-"
                ),
                getattr(
                    event,
                    "event_type",
                    "-"
                ),
                confidence_text,
                getattr(
                    event,
                    "severity",
                    "-"
                ),
            ]

            for column, value in enumerate(
                values
            ):

                self.dashboard_event_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(
                        str(value)
                    )
                )

    # ========================================================
    # CAMERA REFRESH
    # ========================================================

    def refresh_cameras(self):

        try:

            cameras = (
                self.camera_repo.get_all()
            )

        except Exception as exc:

            QMessageBox.critical(
                self,
                "Camera Error",
                str(exc)
            )

            return

        if hasattr(
            self,
            "camera_table"
        ):

            self.camera_table.setRowCount(
                len(cameras)
            )

            for row, camera in enumerate(
                cameras
            ):

                values = [
                    getattr(
                        camera,
                        "id",
                        "-"
                    ),
                    getattr(
                        camera,
                        "name",
                        "-"
                    ),
                    getattr(
                        camera,
                        "location",
                        "-"
                    ),
                    getattr(
                        camera,
                        "source_type",
                        "-"
                    ),
                    getattr(
                        camera,
                        "source",
                        "-"
                    ),
                    getattr(
                        camera,
                        "status",
                        "OFFLINE"
                    ),
                ]

                for column, value in enumerate(
                    values
                ):

                    self.camera_table.setItem(
                        row,
                        column,
                        QTableWidgetItem(
                            str(value)
                        )
                    )

        self.refresh_live_camera_list()

        self.refresh_dashboard()

    # ========================================================
    # LIVE CAMERA LIST
    # ========================================================

    def refresh_live_camera_list(self):

        if not hasattr(
            self,
            "live_camera_combo"
        ):
            return

        current = (
            self.live_camera_combo.currentData()
        )

        self.live_camera_combo.blockSignals(
            True
        )

        self.live_camera_combo.clear()

        try:

            cameras = (
                self.camera_repo.get_all()
            )

        except Exception:

            cameras = []

        for camera in cameras:

            self.live_camera_combo.addItem(
                (
                    f"{camera.name} "
                    f"— {camera.location}"
                ),
                camera.id
            )

        if current is not None:

            index = (
                self.live_camera_combo.findData(
                    current
                )
            )

            if index >= 0:

                self.live_camera_combo.setCurrentIndex(
                    index
                )

        self.live_camera_combo.blockSignals(
            False
        )

    # ========================================================
    # ADD CAMERA
    # ========================================================

    def add_camera_dialog(self):

        dialog = QDialog(
            self
        )

        dialog.setWindowTitle(
            "Add Camera"
        )

        dialog.setMinimumWidth(
            430
        )

        layout = QFormLayout(
            dialog
        )

        name = QLineEdit()

        location = QLineEdit()

        source_type = QComboBox()

        source_type.addItems(
            [
                "RTSP",
                "Webcam",
                "Video File"
            ]
        )

        source = QLineEdit()

        source.setPlaceholderText(
            "rtsp://... / 0 / video.mp4"
        )

        layout.addRow(
            "Camera Name:",
            name
        )

        layout.addRow(
            "Location:",
            location
        )

        layout.addRow(
            "Source Type:",
            source_type
        )

        layout.addRow(
            "Source:",
            source
        )

        buttons = QHBoxLayout()

        cancel = QPushButton(
            "Cancel"
        )

        cancel.setObjectName(
            "secondaryButton"
        )

        save = QPushButton(
            "Add Camera"
        )

        save.setObjectName(
            "primaryButton"
        )

        cancel.clicked.connect(
            dialog.reject
        )

        save.clicked.connect(
            dialog.accept
        )

        buttons.addWidget(
            cancel
        )

        buttons.addWidget(
            save
        )

        layout.addRow(
            "",
            buttons
        )

        if (
            dialog.exec()
            != QDialog.Accepted
        ):

            return

        camera_name = (
            name.text().strip()
        )

        camera_location = (
            location.text().strip()
        )

        camera_source = (
            source.text().strip()
        )

        if not camera_name:

            QMessageBox.warning(
                self,
                "Invalid Camera",
                "Camera name is required."
            )

            return

        if not camera_source:

            QMessageBox.warning(
                self,
                "Invalid Source",
                "Camera source is required."
            )

            return

        try:

            self.camera_repo.add(
                name=camera_name,
                location=camera_location,
                source_type=source_type.currentText(),
                source=camera_source
            )

            self.refresh_cameras()

        except Exception as exc:

            QMessageBox.critical(
                self,
                "Camera Error",
                str(exc)
            )

    # ========================================================
    # SELECTED CAMERA
    # ========================================================

    def _selected_camera_id(self):

        if not hasattr(
            self,
            "camera_table"
        ):

            return None

        row = (
            self.camera_table.currentRow()
        )

        if row < 0:

            return None

        item = (
            self.camera_table.item(
                row,
                0
            )
        )

        if item is None:

            return None

        try:

            return int(
                item.text()
            )

        except ValueError:

            return None

    # ========================================================
    # OPEN SELECTED CAMERA
    # ========================================================

    def open_selected_camera(self):

        camera_id = (
            self._selected_camera_id()
        )

        if camera_id is None:

            QMessageBox.warning(
                self,
                "Camera",
                "Select a camera first."
            )

            return

        try:

            camera = (
                self.camera_repo.get(
                    camera_id
                )
            )

        except Exception as exc:

            QMessageBox.critical(
                self,
                "Camera Error",
                str(exc)
            )

            return

        if camera is None:

            return

        self._navigate(
            1
        )

        index = (
            self.live_camera_combo.findData(
                camera.id
            )
        )

        if index >= 0:

            self.live_camera_combo.setCurrentIndex(
                index
            )

        self.start_stream(
            camera_id=camera.id,
            camera_name=camera.name,
            source=camera.source
        )

    # ========================================================
    # OPEN LIVE FEED
    # ========================================================

    def open_live_feed(self):

        camera_id = (
            self.live_camera_combo.currentData()
        )

        if camera_id is None:

            QMessageBox.warning(
                self,
                "Live Feed",
                "Select a camera first."
            )

            return

        try:

            camera = (
                self.camera_repo.get(
                    camera_id
                )
            )

        except Exception as exc:

            QMessageBox.critical(
                self,
                "Camera Error",
                str(exc)
            )

            return

        if camera is None:

            return

        self.start_stream(
            camera_id=camera.id,
            camera_name=camera.name,
            source=camera.source
        )

    # ========================================================
    # START STREAM
    # ========================================================

    def start_stream(
        self,
        camera_id,
        camera_name,
        source
    ):

        self.stop_stream(
            refresh=False
        )

        self.current_camera_id = (
            camera_id
        )

        model_path = self.config.get(
            "model_path",
            "models/yolo.pt"
        )

        confidence = float(
            self.config.get(
                "confidence",
                0.35
            )
        )

        iou = float(
            self.config.get(
                "iou",
                0.45
            )
        )

        imgsz = int(
            self.config.get(
                "imgsz",
                640
            )
        )

        zone = self.config.get(
            "zone",
            {}
        )

        fence_enabled = bool(
            zone.get(
                "enabled",
                False
            )
        )

        fence_points = zone.get(
            "points",
            []
        )

        self.worker = Worker(
            source=source,
            camera_name=camera_name,
            model_path=model_path,
            confidence=confidence,
            iou=iou,
            imgsz=imgsz,
            fence_enabled=fence_enabled,
            fence_points=fence_points
        )

        self.worker.frame_ready.connect(
            self.update_video_frame
        )

        self.worker.event_ready.connect(
            self.handle_event
        )

        self.worker.status_changed.connect(
            self.update_camera_status
        )

        self.video_label.setText(
            "CONNECTING..."
        )

        self.live_status.setText(
            f"● CONNECTING — {camera_name}"
        )

        self.worker.start()

    # ========================================================
    # STOP STREAM
    # ========================================================

    def stop_stream(
        self,
        refresh=True
    ):

        if self.worker:

            self.worker.stop()

            if self.worker.isRunning():

                self.worker.quit()

                self.worker.wait(
                    1500
                )

            self.worker = None

        self.video_label.setText(
            "NO LIVE FEED"
        )

        self.live_status.setText(
            "● NO CAMERA"
        )

        self.live_status.setStyleSheet(
            """
            color: #8ca2b5;
            border: 1px solid #28465b;
            border-radius: 5px;
            padding: 8px 12px;
            """
        )

        if refresh:

            self.refresh_dashboard()

    # ========================================================
    # CAMERA STATUS
    # ========================================================

    def update_camera_status(
        self,
        status
    ):

        if (
            self.current_camera_id
            is not None
        ):

            try:

                self.camera_repo.update_status(
                    self.current_camera_id,
                    status
                )

            except Exception:

                pass

        if status == "ONLINE":

            self.live_status.setText(
                "● LIVE"
            )

            self.live_status.setStyleSheet(
                """
                color: #22d3a7;
                border: 1px solid #185e5a;
                border-radius: 5px;
                padding: 8px 12px;
                """
            )

        else:

            self.live_status.setText(
                "● OFFLINE"
            )

            self.live_status.setStyleSheet(
                """
                color: #e27777;
                border: 1px solid #63343a;
                border-radius: 5px;
                padding: 8px 12px;
                """
            )

        self.refresh_dashboard()

    # ========================================================
    # UPDATE VIDEO
    # ========================================================

    def update_video_frame(
        self,
        frame
    ):

        if frame is None:

            return

        frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        height, width, channels = (
            frame.shape
        )

        bytes_per_line = (
            channels * width
        )

        image = QImage(
            frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(
            image
        )

        scaled = pixmap.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.video_label.setPixmap(
            scaled
        )

    # ========================================================
    # HANDLE EVENT
    # ========================================================

    def handle_event(
        self,
        event
    ):

        try:

            self.repo.add(
                event
            )

        except Exception as exc:

            print(
                "Event database error:",
                exc
            )

        self.refresh_events()
        self.refresh_dashboard()

    # ========================================================
    # REFRESH EVENTS
    # ========================================================

    def refresh_events(self):

        try:

            events = (
                self.repo.recent(
                    200
                )
            )

        except Exception:

            events = []

        if hasattr(
            self,
            "event_table"
        ):

            selected_filter = (
                self.event_filter.currentText()
                if hasattr(
                    self,
                    "event_filter"
                )
                else "ALL"
            )

            filtered = []

            for event in events:

                severity = str(
                    getattr(
                        event,
                        "severity",
                        ""
                    )
                ).upper()

                if (
                    selected_filter != "ALL"
                    and severity
                    != selected_filter
                ):

                    continue

                filtered.append(
                    event
                )

            self.event_table.setRowCount(
                len(filtered)
            )

            for row, event in enumerate(
                filtered
            ):

                timestamp = getattr(
                    event,
                    "timestamp",
                    None
                )

                time_text = (
                    timestamp.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if timestamp
                    else "-"
                )

                confidence = getattr(
                    event,
                    "confidence",
                    None
                )

                confidence_text = (
                    f"{confidence:.0%}"
                    if confidence is not None
                    else "-"
                )

                values = [
                    time_text,
                    getattr(
                        event,
                        "camera",
                        "-"
                    ),
                    getattr(
                        event,
                        "event_type",
                        "-"
                    ),
                    getattr(
                        event,
                        "message",
                        "-"
                    ),
                    confidence_text,
                    getattr(
                        event,
                        "severity",
                        "-"
                    ),
                    getattr(
                        event,
                        "snapshot_path",
                        "-"
                    )
                ]

                for column, value in enumerate(
                    values
                ):

                    self.event_table.setItem(
                        row,
                        column,
                        QTableWidgetItem(
                            str(value)
                        )
                    )

    # ========================================================
    # DELETE CAMERA
    # ========================================================

    def delete_selected_camera(self):

        camera_id = (
            self._selected_camera_id()
        )

        if camera_id is None:

            QMessageBox.warning(
                self,
                "Camera",
                "Select a camera first."
            )

            return

        reply = QMessageBox.question(
            self,
            "Delete Camera",
            "Delete the selected camera?",
            QMessageBox.Yes
            | QMessageBox.No
        )

        if (
            reply
            != QMessageBox.Yes
        ):

            return

        try:

            self.camera_repo.delete(
                camera_id
            )

            self.refresh_cameras()

        except Exception as exc:

            QMessageBox.critical(
                self,
                "Camera Error",
                str(exc)
            )

    # ========================================================
    # CLOSE
    # ========================================================

    def closeEvent(
        self,
        event
    ):

        self.stop_stream(
            refresh=False
        )

        event.accept()