import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np

from config import CONFIG
from backend.sources import get_video_source, VideoSource
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

        self._video_source: Optional[VideoSource] = None
        self._detector: Optional[FaceLandmarkDetector] = None
        self._eye_analyzer: Optional[EyeAnalyzer] = None
        self._head_pose_estimator: Optional[HeadPoseEstimator] = None
        self._distraction_monitor: Optional[DistractionMonitor] = None
        self._fatigue_monitor: Optional[FatigueMonitor] = None
        self._fusion_engine: Optional[FusionEngine] = None
        self._alert_manager: Optional[AlertManager] = None
        self._hardware: Optional[HardwareInterface] = None
        self._camera_available = False

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

            # Create video source based on camera mode
            video_source = None
            camera_mode = CONFIG.camera_mode.lower()

            if camera_mode == "local":
                video_source = get_video_source(
                    "local",
                    camera_index=CONFIG.camera_index,
                    frame_width=CONFIG.frame_width,
                    frame_height=CONFIG.frame_height,
                )
            elif camera_mode == "file":
                if CONFIG.video_file_path:
                    video_source = get_video_source(
                        "file",
                        file_path=CONFIG.video_file_path,
                        frame_width=CONFIG.frame_width,
                        frame_height=CONFIG.frame_height,
                    )
                else:
                    self._error = "Video file path not configured (VIDEO_FILE_PATH env var)"
                    self._message = "Cannot start in file mode: path not set"
                    self._latest_frame = self._make_placeholder_frame(self._message)
            elif camera_mode == "rtsp":
                if CONFIG.stream_url:
                    video_source = get_video_source(
                        "rtsp",
                        stream_url=CONFIG.stream_url,
                        frame_width=CONFIG.frame_width,
                        frame_height=CONFIG.frame_height,
                    )
                else:
                    self._error = "Stream URL not configured (STREAM_URL env var)"
                    self._message = "Cannot start in RTSP mode: URL not set"
                    self._latest_frame = self._make_placeholder_frame(self._message)
            elif camera_mode == "mock":
                video_source = get_video_source(
                    "mock",
                    frame_width=CONFIG.frame_width,
                    frame_height=CONFIG.frame_height,
                )
            else:
                self._error = f"Unknown camera mode: {camera_mode}"
                self._message = f"Invalid camera mode: {camera_mode}"
                self._latest_frame = self._make_placeholder_frame(self._message)

            # Try to open the video source
            self._video_source = None
            self._detector = None
            self._camera_available = False

            if video_source and video_source.open():
                try:
                    detector = FaceLandmarkDetector(
                        min_detection_confidence=CONFIG.min_detection_confidence,
                        min_tracking_confidence=CONFIG.min_tracking_confidence,
                    )
                    self._video_source = video_source
                    self._detector = detector
                    self._camera_available = True
                except Exception as exc:
                    logger.exception("Face detector init failed")
                    video_source.close()
                    self._error = f"Face detector init failed: {exc}"
                    self._message = "Face detector initialization failed"
                    self._latest_frame = self._make_placeholder_frame(self._message)
            else:
                if video_source:
                    video_source.close()
                self._message = f"Camera not available (using {camera_mode} mode)"
                self._latest_frame = self._make_placeholder_frame(self._message)

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

            if self._camera_available:
                self._message = f"Monitoring started in {camera_mode} mode"
            else:
                self._message = f"Monitoring started in {camera_mode} mode (no camera)"
                self._latest_frame = self._make_placeholder_frame(self._message)

            self._running = True

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
        video_source = self._video_source
        self._video_source = None
        detector = self._detector
        self._detector = None
        hardware = self._hardware
        self._hardware = None
        self._camera_available = False

        if video_source is not None:
            video_source.close()
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
        assert self._eye_analyzer is not None
        assert self._head_pose_estimator is not None
        assert self._distraction_monitor is not None
        assert self._fatigue_monitor is not None
        assert self._fusion_engine is not None
        assert self._alert_manager is not None

        try:
            while not self._stop_event.is_set():
                if self._video_source is None or self._detector is None:
                    self._latest_face_detected = False
                    self._latest_state = "NO_CAMERA"
                    self._latest_risk_score = 0.0
                    self._latest_fatigue_score = 0.0
                    self._latest_distraction_score = 0.0
                    self._latest_timestamp = time.time()
                    self._message = "Camera/source not available"
                    self._latest_frame = self._make_placeholder_frame("Camera/source not available")
                    time.sleep(0.2)
                    continue

                ok, frame = self._video_source.read()
                if not ok or frame is None:
                    self._latest_face_detected = False
                    self._latest_state = "NO_CAMERA"
                    self._latest_risk_score = 0.0
                    self._latest_fatigue_score = 0.0
                    self._latest_distraction_score = 0.0
                    self._latest_timestamp = time.time()
                    self._message = "Failed to read from source"
                    self._latest_frame = self._make_placeholder_frame("Failed to read from source")
                    if self._video_source is not None:
                        self._video_source.close()
                    self._video_source = None
                    if self._detector is not None:
                        self._detector.close()
                    self._detector = None
                    self._camera_available = False
                    time.sleep(0.2)
                    continue

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
