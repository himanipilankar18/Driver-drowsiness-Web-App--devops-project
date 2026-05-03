import sys
from unittest.mock import MagicMock

# Mock heavy dependencies
class FakeEncoded:
    def tobytes(self):
        return b"fake"

mock_cv2 = MagicMock()
mock_cv2.imencode.return_value = (True, FakeEncoded())

sys.modules["cv2"] = mock_cv2
sys.modules["numpy"] = MagicMock()
sys.modules["mediapipe"] = MagicMock()

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

# ❌ Removed test_home (UI not required)

def test_status():
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "state" in data
