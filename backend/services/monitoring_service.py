import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np

from config import CONFIG
from modules.alert import AlertManager
from modules.distraction import DistractionMonitor
from modules.eye_analysis import EyeAnalyzer
from modules.face_detector import FaceLandmarkDetector
from modules.fatigue import FatigueMonitor
from modules.fusion import FusionEngine
from modules.head_pose import HeadPoseEstimator
from modules.hardware_interface import HardwareInterface


logger = logging.getLogger(__name__)


class MonitoringService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self._message = "System not started"
        self._error: Optional[str] = None

        self._capture: Optional[cv2.VideoCapture] = None
        self._detector: Optional[FaceLandmarkDetector] = None
        self._eye_analyzer: Optional[EyeAnalyzer] = None
        self._head_pose_estimator: Optional[HeadPoseEstimator] = None
        self._distraction_monitor: Optional[DistractionMonitor] = None
        self._fatigue_monitor: Optional[FatigueMonitor] = None
        self._fusion_engine: Optional[FusionEngine] = None
        self._alert_manager: Optional[AlertManager] = None
        self._hardware: Optional[HardwareInterface] = None

        self._latest_frame = self._make_placeholder_frame("System idle")
        self._latest_timestamp = 0.0
        self._latest_state = "OFF"
        self._latest_fatigue_score = 0.0
        self._latest_distraction_score = 0.0
        self._latest_face_detected = False
        self._latest_risk_score = 0.0
        self._latest_decision = None
        self._latest_eye_metrics = None
        self._latest_head_pose = None
        self._latest_fatigue = None
        self._latest_distraction = None

        self._previous_state = None
        self._last_hardware_send_ts = 0.0
        self._no_face_since = None
        self._no_face_forced_critical = False
        self._last_logic_update_ts = 0.0

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def start(self) -> bool:
        with self._lock:
            if self._running:
                self._message = "Monitoring already running"
                self._error = None
                return True

            self._error = None
            self._message = "Starting monitoring"
            self._stop_event.clear()

            capture = cv2.VideoCapture(CONFIG.camera_index)
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG.frame_width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG.frame_height)

            if not capture.isOpened():
                self._error = f"Camera {CONFIG.camera_index} is not available"
                self._message = "Failed to start monitoring"
                capture.release()
                self._latest_frame = self._make_placeholder_frame(self._error)
                return False

            try:
                detector = FaceLandmarkDetector(
                    min_detection_confidence=CONFIG.min_detection_confidence,
                    min_tracking_confidence=CONFIG.min_tracking_confidence,
                )
            except Exception as exc:
                self._error = f"Face detector init failed: {exc}"
                self._message = "Failed to start monitoring"
                capture.release()
                self._latest_frame = self._make_placeholder_frame(self._error)
                return False

            self._capture = capture
            self._detector = detector
            self._eye_analyzer = EyeAnalyzer()
            self._head_pose_estimator = HeadPoseEstimator()
            self._distraction_monitor = DistractionMonitor()
            self._fatigue_monitor = FatigueMonitor()
            self._fusion_engine = FusionEngine()
            self._alert_manager = AlertManager()
            self._hardware = None

            self._previous_state = None
            self._last_hardware_send_ts = 0.0
            self._no_face_since = None
            self._no_face_forced_critical = False
            self._last_logic_update_ts = 0.0
            self._latest_state = "NORMAL"
            self._latest_fatigue_score = 0.0
            self._latest_distraction_score = 0.0
            self._latest_face_detected = False
            self._latest_risk_score = 0.0
            self._latest_decision = None
            self._latest_eye_metrics = None
            self._latest_head_pose = None
            self._latest_fatigue = None
            self._latest_distraction = None
            self._message = "Monitoring started"
            self._running = True

            # Hardware initialization disabled - no ESP32 connection
            # if CONFIG.enable_hardware:
            #     hardware = HardwareInterface(
            #         port=CONFIG.serial_port,
            #         baudrate=CONFIG.serial_baudrate,
            #     )
            #     if hardware.connect():
            #         hardware.send_alert(CONFIG.hardware_default_state)
            #         self._previous_state = CONFIG.hardware_default_state
            #         self._last_hardware_send_ts = time.time()
            #         self._hardware = hardware
            #     else:
            #         self._hardware = None
            #         self._message = "Monitoring started without hardware"

            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            return True

    def stop(self) -> bool:
        with self._lock:
            if not self._running and self._thread is None:
                self._message = "Monitoring already stopped"
                return True

            self._stop_event.set()
            thread = self._thread

        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=3.0)

        self._cleanup_resources()
        with self._lock:
            self._running = False
            self._thread = None
            self._message = "Monitoring stopped"
            self._latest_state = "OFF"
            self._latest_face_detected = False
            self._latest_frame = self._make_placeholder_frame("Monitoring stopped")
        return True

    def _cleanup_resources(self) -> None:
        capture = self._capture
        self._capture = None
        detector = self._detector
        self._detector = None
        hardware = self._hardware
        self._hardware = None

        if capture is not None:
            capture.release()
        if detector is not None:
            detector.close()
        if hardware is not None:
            try:
                if hardware.is_connected():
                    hardware.send_alert("NORMAL")
                    time.sleep(0.2)
            finally:
                hardware.disconnect()

    def _make_placeholder_frame(self, message: str) -> bytes:
        frame = np.zeros((CONFIG.frame_height, CONFIG.frame_width, 3), dtype=np.uint8)
        cv2.putText(frame, "Driver Safety Monitoring System", (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, message, (40, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 180, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, "Start monitoring to activate webcam processing", (40, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2, cv2.LINE_AA)
        ok, encoded = cv2.imencode(".jpg", frame)
        return encoded.tobytes() if ok else b""

    def _encode_frame(self, frame) -> bytes:
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            return self._latest_frame
        return encoded.tobytes()

    def _publish_hardware_state(self, state: str, timestamp: float) -> None:
        if not self._hardware:
            return

        if (
            state != self._previous_state
            or (timestamp - self._last_hardware_send_ts) >= CONFIG.hardware_resend_interval_seconds
        ):
            if self._hardware.send_alert(state):
                self._previous_state = state
                self._last_hardware_send_ts = timestamp

    def _run(self) -> None:
        assert self._capture is not None
        assert self._detector is not None
        assert self._eye_analyzer is not None
        assert self._head_pose_estimator is not None
        assert self._distraction_monitor is not None
        assert self._fatigue_monitor is not None
        assert self._fusion_engine is not None
        assert self._alert_manager is not None

        try:
            while not self._stop_event.is_set():
                ok, frame = self._capture.read()
                if not ok:
                    self._error = "Camera frame read failed"
                    self._message = self._error
                    self._latest_frame = self._make_placeholder_frame(self._error)
                    break

                timestamp = time.time()
                detection = self._detector.process(frame)
                self._latest_face_detected = detection.face_detected

                if detection.face_detected and detection.landmarks is not None:
                    self._no_face_since = None
                    self._no_face_forced_critical = False

                    if (timestamp - self._last_logic_update_ts) >= CONFIG.logic_update_interval_seconds:
                        self._latest_eye_metrics = self._eye_analyzer.update(detection.landmarks, timestamp)
                        self._latest_head_pose = self._head_pose_estimator.estimate(detection.landmarks)
                        self._latest_distraction = self._distraction_monitor.update(self._latest_head_pose, timestamp)
                        self._latest_fatigue = self._fatigue_monitor.update(
                            detection.landmarks,
                            self._latest_eye_metrics,
                            self._latest_head_pose,
                            timestamp,
                        )
                        self._latest_decision = self._fusion_engine.combine(
                            self._latest_fatigue,
                            self._latest_distraction,
                            timestamp,
                        )
                        self._last_logic_update_ts = timestamp

                    if all(
                        value is not None
                        for value in (
                            self._latest_decision,
                            self._latest_eye_metrics,
                            self._latest_head_pose,
                            self._latest_fatigue,
                            self._latest_distraction,
                        )
                    ):
                        frame = self._alert_manager.draw_overlay(
                            frame,
                            self._latest_decision,
                            self._latest_eye_metrics,
                            self._latest_head_pose,
                            self._latest_fatigue,
                            self._latest_distraction,
                        )
                        self._latest_state = self._latest_decision.state
                        self._latest_risk_score = self._latest_decision.risk_score
                        self._latest_fatigue_score = self._latest_decision.fatigue_score
                        self._latest_distraction_score = self._latest_decision.distraction_score
                        self._message = f"Monitoring active: {self._latest_state}"
                        self._alert_manager.publish(
                            self._latest_decision,
                            self._latest_eye_metrics,
                            self._latest_head_pose,
                            self._latest_fatigue,
                            self._latest_distraction,
                        )
                        self._publish_hardware_state(self._latest_state, timestamp)
                    else:
                        frame = self._alert_manager.draw_no_face_overlay(frame)
                else:
                    if self._no_face_since is None:
                        self._no_face_since = timestamp

                    no_face_duration = timestamp - self._no_face_since
                    self._latest_face_detected = False
                    self._message = "No face detected"

                    if no_face_duration >= CONFIG.no_face_hardware_timeout_seconds:
                        if not self._no_face_forced_critical:
                            self._latest_decision = self._fusion_engine.force_critical_no_face(timestamp)
                            self._latest_state = self._latest_decision.state
                            self._latest_risk_score = self._latest_decision.risk_score
                            self._latest_fatigue_score = self._latest_decision.fatigue_score
                            self._latest_distraction_score = self._latest_decision.distraction_score
                            self._no_face_forced_critical = True
                        self._publish_hardware_state("CRITICAL", timestamp)

                    frame = self._alert_manager.draw_no_face_overlay(frame)

                self._latest_timestamp = timestamp
                self._latest_frame = self._encode_frame(frame)

        except Exception as exc:
            logger.exception("Monitoring loop stopped due to an error")
            self._error = str(exc)
            self._message = f"Monitoring error: {exc}"
            self._latest_frame = self._make_placeholder_frame(self._message)
        finally:
            self._cleanup_resources()
            with self._lock:
                self._running = False
                self._thread = None
                if not self._error:
                    self._message = "Monitoring stopped"

    def status(self) -> dict:
        with self._lock:
            return {
                "state": self._latest_state,
                "fatigue_score": round(float(self._latest_fatigue_score), 2),
                "distraction_score": round(float(self._latest_distraction_score), 2),
                "face_detected": bool(self._latest_face_detected),
                "monitoring": self._running,
                "message": self._message,
                "error": self._error,
                "risk_score": round(float(self._latest_risk_score), 2),
                "timestamp": self._latest_timestamp,
            }

    def video_stream(self):
        while True:
            frame = self._latest_frame
            if not frame:
                frame = self._make_placeholder_frame(self._message)
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
            time.sleep(0.03)
