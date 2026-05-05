let mediaStream = null;
let captureTimer = null;

const preview = document.getElementById("preview");
const canvas = document.getElementById("frameCanvas");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");

const stateEl = document.getElementById("state");
const fatigueEl = document.getElementById("fatigue_score");
const distractionEl = document.getElementById("distraction_score");
const faceEl = document.getElementById("face_detected");
const errorEl = document.getElementById("error");
const httpWarningEl = document.getElementById("httpWarning");

function setError(message) {
    if (!message) {
        errorEl.hidden = true;
        errorEl.textContent = "";
        return;
    }
    errorEl.hidden = false;
    errorEl.textContent = message;
}

function showHttpWarningIfNeeded() {
    const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    const isSecure = window.location.protocol === "https:";
    httpWarningEl.hidden = isSecure || isLocalhost;
}

async function postStart() {
    await fetch("/start", { method: "POST" });
}

async function postStop() {
    await fetch("/stop", { method: "POST" });
}

function stopLocalCamera() {
    if (captureTimer) {
        clearInterval(captureTimer);
        captureTimer = null;
    }

    if (mediaStream) {
        mediaStream.getTracks().forEach((track) => track.stop());
        mediaStream = null;
    }

    preview.srcObject = null;
}

function updateStatus(data) {
    stateEl.textContent = data.state;
    fatigueEl.textContent = Number(data.fatigue_score || 0).toFixed(2);
    distractionEl.textContent = Number(data.distraction_score || 0).toFixed(2);
    faceEl.textContent = String(Boolean(data.face_detected));
}

async function sendFrame() {
    if (!mediaStream || preview.videoWidth === 0 || preview.videoHeight === 0) {
        return;
    }

    canvas.width = preview.videoWidth;
    canvas.height = preview.videoHeight;
    const context = canvas.getContext("2d");
    context.drawImage(preview, 0, 0, canvas.width, canvas.height);

    const blob = await new Promise((resolve) => {
        canvas.toBlob(resolve, "image/jpeg", 0.8);
    });

    if (!blob) {
        return;
    }

    const formData = new FormData();
    formData.append("image", blob, "frame.jpg");

    const response = await fetch("/process-frame", {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        throw new Error("Frame processing failed");
    }

    const result = await response.json();
    updateStatus(result);
}

async function startMonitoring() {
    try {
        setError("");
        await postStart();

        mediaStream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: false,
        });
        preview.srcObject = mediaStream;

        captureTimer = setInterval(async () => {
            try {
                await sendFrame();
            } catch (error) {
                setError(error.message);
            }
        }, 400);

        startBtn.disabled = true;
        stopBtn.disabled = false;
    } catch (error) {
        const blocked = error && (
            error.name === "NotAllowedError" ||
            error.name === "SecurityError" ||
            error.name === "PermissionDeniedError"
        );
        if (blocked) {
            setError("Camera blocked. Enable permission in browser settings.");
        } else {
            setError(error.message || "Unable to start monitoring");
        }
        stopLocalCamera();
        await postStop();
    }
}

async function stopMonitoring() {
    stopLocalCamera();
    await postStop();
    startBtn.disabled = false;
    stopBtn.disabled = true;
}

showHttpWarningIfNeeded();

startBtn.addEventListener("click", startMonitoring);
stopBtn.addEventListener("click", () => {
    stopMonitoring().catch((error) => setError(error.message));
});

window.addEventListener("beforeunload", () => {
    stopLocalCamera();
});
