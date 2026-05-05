import time

from config import CONFIG
from modules.distraction import DistractionMonitor
from modules.eye_analysis import EyeAnalyzer
from modules.face_detector import FaceLandmarkDetector
from modules.fatigue import FatigueMonitor
from modules.fusion import FusionEngine
from modules.head_pose import HeadPoseEstimator


class MonitoringService:
    def __init__(self) -> None:
        self._running = False

        self._detector = FaceLandmarkDetector(
            min_detection_confidence=CONFIG.min_detection_confidence,
            min_tracking_confidence=CONFIG.min_tracking_confidence,
        )
        self._eye_analyzer = EyeAnalyzer()
        self._head_pose_estimator = HeadPoseEstimator()
        self._distraction_monitor = DistractionMonitor()
        self._fatigue_monitor = FatigueMonitor()
        self._fusion_engine = FusionEngine()

        self._latest_timestamp = 0.0
        self._latest_state = "NORMAL"
        self._latest_fatigue_score = 0.0
        self._latest_distraction_score = 0.0
        self._latest_face_detected = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def process_frame(self, frame) -> dict:
        if not self._running:
            return {
                "state": "NORMAL",
                "fatigue_score": 0.0,
                "distraction_score": 0.0,
                "face_detected": False,
            }

        timestamp = time.time()
        detection = self._detector.process(frame)
        self._latest_face_detected = detection.face_detected

        if not detection.face_detected or detection.landmarks is None:
            self._latest_state = "WARNING"
            self._latest_fatigue_score = 0.0
            self._latest_distraction_score = 0.0
            self._latest_timestamp = timestamp
            return {
                "state": self._latest_state,
                "fatigue_score": 0.0,
                "distraction_score": 0.0,
                "face_detected": False,
            }

        eye_metrics = self._eye_analyzer.update(detection.landmarks, timestamp)
        head_pose = self._head_pose_estimator.estimate(detection.landmarks)
        distraction = self._distraction_monitor.update(head_pose, timestamp)
        fatigue = self._fatigue_monitor.update(
            detection.landmarks,
            eye_metrics,
            head_pose,
            timestamp,
        )
        decision = self._fusion_engine.combine(fatigue, distraction, timestamp)

        self._latest_state = decision.state
        self._latest_fatigue_score = float(decision.fatigue_score)
        self._latest_distraction_score = float(decision.distraction_score)
        self._latest_timestamp = timestamp

        return {
            "state": self._latest_state,
            "fatigue_score": round(self._latest_fatigue_score, 2),
            "distraction_score": round(self._latest_distraction_score, 2),
            "face_detected": True,
        }
