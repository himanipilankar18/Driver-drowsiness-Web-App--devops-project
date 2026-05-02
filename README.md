# Driver Safety System (Real-Time Monitoring)

A real-time driver safety monitoring system using OpenCV and MediaPipe to detect fatigue and distraction.
Includes a lightweight FastAPI web interface and optional ESP32 hardware alerts.

---

## 🚀 Features

### 🎯 Core Detection

* Eye closure detection (EAR)
* Blink rate & microsleep detection
* Yawn detection (mouth ratio)
* Head pose estimation (yaw, pitch, roll)
* Distraction detection

### 🧠 Intelligent State System

* **NORMAL** – Safe driving
* **WARNING** – Moderate risk
* **CRITICAL** – High risk
* Smooth transitions (no flickering)

### 🌐 Web Interface

* Start/Stop monitoring
* Live video stream
* Real-time status API
* Lightweight FastAPI + HTML (no React)

### ⚙️ Hardware (Optional)

* ESP32 buzzer + LED alerts
* Serial communication
* Fully optional (can run without hardware)

---

## 🛠️ Tech Stack

* Python 3.10
* FastAPI
* OpenCV
* MediaPipe
* NumPy
* PySerial (optional)

---

## ⚙️ Setup Instructions

### 1. Install Python (3.10 recommended)

```bash
winget install Python.Python.3.10
```

---

### 2. Clone Repository

```bash
git clone <your-repo-url>
cd driver_safety_system
```

---

### 3. Create Virtual Environment

```bash
py -3.10 -m venv venv
venv\Scripts\activate
```

---

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 5. Run Application

```bash
uvicorn backend.main:app --reload
```

---

## 🌐 Access Application

| Feature    | URL                          |
| ---------- | ---------------------------- |
| Home       | http://127.0.0.1:8000/       |
| Video Feed | http://127.0.0.1:8000/video  |
| API Status | http://127.0.0.1:8000/status |
| API Docs   | http://127.0.0.1:8000/docs   |

---

## 🧪 How to Test

1. Click **Start Monitoring**
2. Check webcam feed
3. Try:

   * Close eyes → fatigue increases
   * Turn head → distraction increases
4. Observe state changes:

   * NORMAL → WARNING → CRITICAL

---

## ⚙️ Configuration

Edit:

```bash
configs/config.py
```

### Important

```python
ENABLE_HARDWARE = False
```

Set to `True` only if ESP32 is connected.

---

## 📁 Project Structure

```
driver_safety_system/
│
├── backend/              # FastAPI web app
├── modules/              # Core AI logic
├── configs/              # Configuration
├── requirements.txt
├── README.md
```

---

## 🧠 System Architecture

```
Camera → Face Detection → Feature Extraction
        ↓
   Eye + Head + Fatigue Analysis
        ↓
     Risk Fusion Engine
        ↓
   State (NORMAL/WARNING/CRITICAL)
        ↓
   Web UI + (Optional Hardware)
```

---

## 📌 Status

✔ Core system working
✔ Web interface working


---

