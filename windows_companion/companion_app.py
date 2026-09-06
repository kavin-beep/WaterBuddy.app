"""PySide6 UI for the native Water Buddy companion."""

from __future__ import annotations

import argparse
import math
import socket
import sys
import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMenu, QPushButton, QSystemTrayIcon, QVBoxLayout, QWidget

from water_buddy.domain import WaterLogCooldownError
from water_buddy.mascot_design import MASCOT_ACCESSORIES, MASCOT_PALETTE
from windows_companion.ipc import COMMANDS, HOST, PORT, send_command
from windows_companion.launcher import open_app
from windows_companion.models import DesktopPetSettings, MascotState, next_state
from windows_companion.positioning import bottom_right, clamp_position
from windows_companion.profile_bridge import LocalJsonProfileBridge
from windows_companion.reminder_service import should_notify
from windows_companion.single_instance import SingleInstance


class MascotWindow(QWidget):
    command = Signal(str)

    def __init__(self, bridge: LocalJsonProfileBridge) -> None:
        super().__init__()
        self.bridge = bridge
        self.snapshot = bridge.snapshot()
        self.settings = self._settings()
        self.state = MascotState.ENTRANCE
        self.phase = 0.0
        self.drag_origin: tuple[QPoint, QPoint] | None = None
        self.dragged = False
        self.panel: QWidget | None = None
        self.last_reminder_key: str | None = None
        self.setWindowTitle("WaterBuddy mascot")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | self._top_flag())
        self.resize(round(180 * self.settings.scale), round(210 * self.settings.scale))
        self._restore_position()
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._animate)
        self.animation_timer.start(40)
        self.profile_timer = QTimer(self)
        self.profile_timer.timeout.connect(self.reload_profile)
        self.profile_timer.start(3000)
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_reminder)
        self.reminder_timer.start(30000)

    def _settings(self) -> DesktopPetSettings:
        return DesktopPetSettings.from_mapping(self.snapshot["data"]["preferences"].get("desktop_pet"))

    def _top_flag(self):
        return Qt.WindowType.WindowStaysOnTopHint if self.settings.always_on_top else Qt.WindowType.Widget

    def _work_area(self) -> tuple[int, int, int, int]:
        screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        geometry = screen.availableGeometry()
        return geometry.left(), geometry.top(), geometry.right() + 1, geometry.bottom() + 1

    def _restore_position(self) -> None:
        work = self._work_area()
        target = self.settings.position or bottom_right(self.width(), self.height(), work)
        self.move(*clamp_position(*target, self.width(), self.height(), work))

    def _animate(self) -> None:
        if self.settings.motion_enabled:
            self.phase += 0.13
            self.update()

    def reload_profile(self) -> None:
        try:
            self.snapshot = self.bridge.snapshot()
            updated = self._settings()
        except Exception:
            return
        if not updated.enabled:
            QApplication.quit()
            return
        if updated.scale != self.settings.scale:
            self.resize(round(180 * updated.scale), round(210 * updated.scale))
        if updated.always_on_top != self.settings.always_on_top:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, updated.always_on_top)
            self.show()
        self.settings = updated
        self.update()

    def check_reminder(self) -> None:
        reminder_key = str(self.snapshot["data"].get("preferences", {}).get("next_reminder_at"))
        if reminder_key != self.last_reminder_key and should_notify(self.snapshot["data"], datetime.now()):
            self.last_reminder_key = reminder_key
            self.state = next_state(self.state, "reminder_due")
            if self.settings.sound_enabled:
                QApplication.beep()
            self.show_panel("Time for a sip 💧")

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(0, math.sin(self.phase) * 4 if self.settings.motion_enabled else 0)
        painter.scale(self.width() / 180.0, self.width() / 180.0)
        gradient = QLinearGradient(35, 30, 145, 175)
        for point, color in ((0, MASCOT_PALETTE["body_highlight"]), (.35, MASCOT_PALETTE["body_mid"]), (.68, MASCOT_PALETTE["body_deep"]), (1, MASCOT_PALETTE["body_shadow"])):
            gradient.setColorAt(point, QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(45, 212, 191, 95))
        painter.drawEllipse(QRectF(50, 35, 80, 28))
        tip_gradient = QLinearGradient(58, 16, 120, 69); tip_gradient.setColorAt(0, QColor(MASCOT_PALETTE["tip_highlight"])); tip_gradient.setColorAt(.46, QColor(MASCOT_PALETTE["tip_mid"])); tip_gradient.setColorAt(1, QColor(MASCOT_PALETTE["tip_deep"]))
        painter.save(); painter.translate(90, 44); painter.rotate(45); painter.setBrush(tip_gradient); painter.drawRoundedRect(QRectF(-31, -31, 62, 62), 15, 7); painter.restore()
        painter.setPen(QPen(QColor("#8CF5FF"), 3))
        painter.setBrush(gradient)
        body = QPainterPath(); body.moveTo(90, 38); body.cubicTo(130, 38, 154, 63, 152, 108); body.cubicTo(150, 154, 130, 176, 90, 176); body.cubicTo(49, 176, 28, 154, 28, 108); body.cubicTo(28, 65, 50, 38, 90, 38); body.closeSubpath(); painter.drawPath(body)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(MASCOT_PALETTE["body_deep"]))
        left_fin = QPainterPath(); left_fin.moveTo(35, 105); left_fin.cubicTo(6, 87, 2, 119, 34, 134); left_fin.closeSubpath(); painter.drawPath(left_fin)
        right_fin = QPainterPath(); right_fin.moveTo(145, 105); right_fin.cubicTo(174, 87, 178, 119, 146, 134); right_fin.closeSubpath(); painter.drawPath(right_fin)
        painter.setBrush(QColor(159, 242, 255, 62)); painter.drawEllipse(QRectF(56, 123, 68, 43))
        mood = str(self.snapshot["pet"].get("mood", "happy")).casefold()
        painter.setPen(QPen(QColor(MASCOT_PALETTE["face"]), 3))
        painter.setBrush(QColor(MASCOT_PALETTE["face"]))
        if "sleep" in mood:
            painter.drawLine(54, 89, 74, 89); painter.drawLine(106, 89, 126, 89)
        else:
            painter.drawEllipse(QRectF(54, 76, 20, 25)); painter.drawEllipse(QRectF(106, 76, 20, 25))
            painter.setBrush(Qt.GlobalColor.white); painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(59, 80, 7, 8)); painter.drawEllipse(QRectF(111, 80, 7, 8))
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(MASCOT_PALETTE["cheek"])); painter.setOpacity(.42)
        painter.drawEllipse(QRectF(38, 105, 22, 10)); painter.drawEllipse(QRectF(120, 105, 22, 10))
        painter.setOpacity(1); painter.setPen(QPen(QColor(MASCOT_PALETTE["face"]), 3)); painter.setBrush(Qt.BrushStyle.NoBrush)
        if "thirst" in mood or "curious" in mood:
            painter.drawEllipse(QRectF(82, 107, 16, 16))
        else:
            painter.drawArc(QRectF(72, 99, 36, 30), 200 * 16, 140 * 16)
        self._draw_accessory(painter, str(self.snapshot["pet"].get("equipped_accessory", "none")))
        painter.setPen(QColor("#EFFFFF"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(QRectF(10, 181, 160, 24), Qt.AlignmentFlag.AlignCenter, str(self.snapshot["pet"].get("name", "Ripple")))

    def _draw_accessory(self, painter: QPainter, accessory: str) -> None:
        if accessory not in MASCOT_ACCESSORIES or accessory == "none":
            return
        colors = {"seafoam_bow": "#F472B6", "sunny_visor": "#092454", "coral_crown": "#FBBF24", "star_shell": "#F59E0B", "samurai_fit": "#13233F", "cyborg_fit": "#A8DFFF", "cool_guy_fit": "#121A36"}
        painter.setPen(QPen(QColor("#061E52"), 2)); painter.setBrush(QColor(colors.get(accessory, "#8FF7DB")))
        if accessory == "seafoam_bow":
            painter.drawEllipse(QRectF(92, 48, 25, 25)); painter.drawEllipse(QRectF(113, 48, 25, 25))
        elif accessory in {"sunny_visor", "cool_guy_fit"}:
            painter.drawRoundedRect(QRectF(43, 73, 94, 26), 8, 8)
        elif accessory == "coral_crown":
            crown = QPainterPath(); crown.moveTo(54, 51); crown.lineTo(64, 25); crown.lineTo(88, 47); crown.lineTo(108, 22); crown.lineTo(126, 53); crown.closeSubpath(); painter.drawPath(crown)
        elif accessory == "star_shell":
            painter.drawEllipse(QRectF(72, 32, 38, 30))
        else:
            painter.drawRoundedRect(QRectF(45, 130, 90, 36), 12, 12)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_origin = event.globalPosition().toPoint(), self.pos(); self.dragged = False
        elif event.button() == Qt.MouseButton.RightButton:
            self.context_menu().exec(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event) -> None:
        if self.drag_origin and event.buttons() & Qt.MouseButton.LeftButton:
            cursor, origin = self.drag_origin
            delta = event.globalPosition().toPoint() - cursor
            self.dragged = self.dragged or delta.manhattanLength() > 4
            self.move(origin + delta)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.dragged:
            x, y = clamp_position(self.x(), self.y(), self.width(), self.height(), self._work_area())
            self.move(x, y)
            screen = QApplication.screenAt(self.frameGeometry().center())
            self.bridge.update_desktop_settings(
                position={"x": x, "y": y},
                monitor=screen.name() if screen else None,
            )
        else:
            self.state = next_state(self.state, "clicked")
            self.show_panel()
        self.drag_origin = None

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.state = next_state(self.state, "double_clicked")
            open_app("home")

    def show_panel(self, message: str = "What would you like to do?") -> None:
        if self.panel and self.panel.isVisible():
            self.panel.close(); return
        self.panel = QWidget(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.panel.setStyleSheet("QWidget{background:#10233e;color:#f5fbff;border-radius:14px} QPushButton{background:#173354;padding:9px;border:0;border-radius:8px;text-align:left} QPushButton:hover{background:#21466f}")
        layout = QVBoxLayout(self.panel)
        title = QLabel(f"{self.snapshot['pet'].get('name','Ripple')} · Level {self.snapshot['pet'].get('level',1)}")
        title.setStyleSheet("font-size:16px;font-weight:700"); layout.addWidget(title); layout.addWidget(QLabel(message))
        amounts = self.snapshot["data"].get("preferences", {}).get("quick_log_amounts_ml", [250, 500, 750, 1000])
        row = QHBoxLayout()
        for amount in amounts:
            button = QPushButton(f"+{amount} ml"); button.clicked.connect(lambda _=False, value=amount: self.log_water(value)); row.addWidget(button)
        layout.addLayout(row)
        for label, callback in (("Open WaterBuddy", lambda: open_app("home")), ("Snooze reminder 10 min", lambda: self.bridge.snooze(10)), ("Skip reminder", self.bridge.skip)):
            button = QPushButton(label); button.clicked.connect(callback); layout.addWidget(button)
        self.panel.adjustSize()
        work = self._work_area(); right = self.x() + self.width() + self.panel.width()
        panel_x = self.x() - self.panel.width() - 12 if right > work[2] else self.x() + self.width() + 12
        self.panel.move(*clamp_position(panel_x, self.y(), self.panel.width(), self.panel.height(), work)); self.panel.show()

    def log_water(self, amount: int) -> None:
        try:
            result = self.bridge.log_water(amount)
            self.snapshot = self.bridge.snapshot()
            self.state = next_state(self.state, "goal_reached" if result.get("goal_met") else "water_logged")
            if self.settings.sound_enabled:
                QApplication.beep()
        except WaterLogCooldownError as error:
            if self.panel:
                self.panel.setToolTip(error.user_message)
        self.update()

    def context_menu(self) -> QMenu:
        menu = QMenu()
        menu.addAction("Log 250 ml", lambda: self.log_water(250))
        menu.addAction("Open WaterBuddy", lambda: open_app("home"))
        menu.addSeparator(); menu.addAction("Hide for now", self.hide)
        menu.addAction("Remove mascot from Windows", self.remove_mascot)
        return menu

    def remove_mascot(self) -> None:
        self.bridge.update_desktop_settings(enabled=False)
        QApplication.quit()


def create_tray(window: MascotWindow) -> QSystemTrayIcon:
    pixmap = QPixmap(32, 32); pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap); painter.setRenderHint(QPainter.RenderHint.Antialiasing); painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor("#20B6EB")); painter.drawEllipse(3, 3, 26, 26); painter.end()
    tray = QSystemTrayIcon(QIcon(pixmap), window)
    menu = window.context_menu(); menu.addAction("Quit", QApplication.quit); tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: window.show() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
    tray.show(); return tray


def serve_ipc(window: MascotWindow) -> None:
    def worker() -> None:
        try:
            server = socket.socket(); server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); server.bind((HOST, PORT)); server.listen()
            while True:
                connection, _ = server.accept()
                with connection:
                    command = connection.recv(64).decode("ascii", "ignore").strip()
                if command in COMMANDS:
                    window.command.emit(command)
        except OSError:
            pass
    threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--profile", type=Path, required=True); args = parser.parse_args()
    instance = SingleInstance()
    if instance.already_running:
        send_command("SHOW_MASCOT"); return
    app = QApplication(sys.argv); app.setQuitOnLastWindowClosed(False)
    bridge = LocalJsonProfileBridge(args.profile)
    if not DesktopPetSettings.from_mapping(bridge.snapshot()["data"]["preferences"].get("desktop_pet")).enabled:
        return
    window = MascotWindow(bridge)
    actions = {"SHOW_MASCOT": window.show, "HIDE_MASCOT": window.hide, "RELOAD_PROFILE": window.reload_profile, "OPEN_HOME": lambda: open_app("home"), "FOCUS_HOME": lambda: open_app("home"), "SHUTDOWN": app.quit}
    window.command.connect(lambda command: actions[command]())
    serve_ipc(window); tray = create_tray(window); window.show(); app.exec(); tray.hide(); instance.close()
