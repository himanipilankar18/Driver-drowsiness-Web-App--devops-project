/**
 * Browser Camera Capture and Streaming Module
 * 
 * Handles:
 * - Camera access via getUserMedia
 * - Frame capture from video element
 * - Frame encoding (Base64 JPEG)
 * - Real-time transmission to backend
 * - WebSocket and HTTP POST support
 * - Performance optimization (FPS limiting)
 */

class BrowserCameraCapture {
    constructor(config = {}) {
        this.config = {
            frameRate: config.frameRate || 12, // Frames per second (10-15 recommended)
            quality: config.quality || 0.85, // JPEG quality (0.7-0.95)
            maxWidth: config.maxWidth || 1280,
            maxHeight: config.maxHeight || 720,
            useWebSocket: config.useWebSocket !== false, // Prefer WebSocket
            serverUrl: config.serverUrl || '',
            autoStart: config.autoStart || false,
            ...config,
        };

        // State
        this.state = {
            isCapturing: false,
            isPaused: false,
            frameCount: 0,
            errorCount: 0,
            startTime: null,
            lastFrameTime: null,
            currentFPS: 0,
            analysisResults: null,
            lastError: null,
        };

        // UI Elements
        this.videoElement = null;
        this.canvasElement = null;
        this.statusElement = null;
        this.statsElement = null;

        // WebSocket connection
        this.websocket = null;
        this.websocketReconnectAttempts = 0;
        this.websocketMaxReconnectAttempts = 5;
        this.websocketReconnectDelay = 1000;

        // Frame capture interval
        this.captureInterval = null;
        this.frameBuffer = null;

        // Event handlers
        this.eventHandlers = {
            onStart: config.onStart || (() => {}),
            onStop: config.onStop || (() => {}),
            onFrame: config.onFrame || (() => {}),
            onAnalysisResult: config.onAnalysisResult || (() => {}),
            onError: config.onError || (() => {}),
        };
    }

    /**
     * Initialize camera capture
     */
    async initialize() {
        try {
            // Request camera access
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: this.config.maxWidth },
                    height: { ideal: this.config.maxHeight },
                    facingMode: 'user',
                },
                audio: false,
            });

            // Create video element
            this.videoElement = document.createElement('video');
            this.videoElement.srcObject = stream;
            this.videoElement.autoplay = true;
            this.videoElement.playsinline = true;
            this.videoElement.style.display = 'none'; // Hidden from UI

            // Wait for video to load
            await new Promise((resolve) => {
                this.videoElement.onloadedmetadata = () => {
                    this.videoElement.play();
                    resolve();
                };
            });

            // Create canvas for frame capture
            this.canvasElement = document.createElement('canvas');
            this.canvasElement.width = this.videoElement.videoWidth;
            this.canvasElement.height = this.videoElement.videoHeight;

            console.log(
                `[BrowserCamera] Initialized: ${this.canvasElement.width}x${this.canvasElement.height}`
            );

            // Connect WebSocket if enabled
            if (this.config.useWebSocket) {
                this.connectWebSocket();
            }

            return true;
        } catch (error) {
            this.handleError(`Initialization failed: ${error.message}`);
            throw error;
        }
    }

    /**
     * Connect to WebSocket server
     */
    connectWebSocket() {
        try {
            // Construct WebSocket URL
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            const wsUrl = `${protocol}//${host}/ws/camera`;

            console.log(`[BrowserCamera] Connecting to WebSocket: ${wsUrl}`);

            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                console.log('[BrowserCamera] WebSocket connected');
                this.websocketReconnectAttempts = 0;
            };

            this.websocket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                if (message.type === 'status') {
                    this.state.analysisResults = message;
                    this.eventHandlers.onAnalysisResult(message);
                }
            };

            this.websocket.onerror = (error) => {
                console.error('[BrowserCamera] WebSocket error:', error);
                this.handleError(`WebSocket error: ${error.message || 'Unknown'}`);
            };

            this.websocket.onclose = () => {
                console.log('[BrowserCamera] WebSocket disconnected');
                this.attemptWebSocketReconnect();
            };
        } catch (error) {
            this.handleError(`WebSocket connection failed: ${error.message}`);
        }
    }

    /**
     * Attempt to reconnect WebSocket
     */
    attemptWebSocketReconnect() {
        if (
            this.websocketReconnectAttempts < this.websocketMaxReconnectAttempts &&
            this.state.isCapturing
        ) {
            this.websocketReconnectAttempts++;
            const delay = this.websocketReconnectDelay * this.websocketReconnectAttempts;

            console.log(
                `[BrowserCamera] Reconnecting WebSocket in ${delay}ms (attempt ${this.websocketReconnectAttempts})`
            );

            setTimeout(() => {
                if (this.state.isCapturing) {
                    this.connectWebSocket();
                }
            }, delay);
        }
    }

    /**
     * Start frame capture and transmission
     */
    async start() {
        if (this.state.isCapturing) {
            console.warn('[BrowserCamera] Already capturing');
            return false;
        }

        try {
            // Initialize if not already done
            if (!this.videoElement) {
                await this.initialize();
            }

            this.state.isCapturing = true;
            this.state.frameCount = 0;
            this.state.errorCount = 0;
            this.state.startTime = Date.now();
            this.state.lastFrameTime = null;
            this.state.lastError = null;

            // Start frame capture loop
            const frameInterval = 1000 / this.config.frameRate;
            this.captureInterval = setInterval(() => {
                if (!this.state.isPaused) {
                    this.captureAndSendFrame();
                }
            }, frameInterval);

            console.log('[BrowserCamera] Capture started');
            this.eventHandlers.onStart();

            return true;
        } catch (error) {
            this.state.isCapturing = false;
            this.handleError(`Start failed: ${error.message}`);
            return false;
        }
    }

    /**
     * Stop frame capture and transmission
     */
    stop() {
        if (!this.state.isCapturing) {
            console.warn('[BrowserCamera] Not currently capturing');
            return false;
        }

        this.state.isCapturing = false;

        if (this.captureInterval) {
            clearInterval(this.captureInterval);
            this.captureInterval = null;
        }

        // Close WebSocket
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }

        // Clean up video element
        if (this.videoElement && this.videoElement.srcObject) {
            this.videoElement.srcObject.getTracks().forEach((track) => {
                track.stop();
            });
        }

        console.log('[BrowserCamera] Capture stopped');
        this.eventHandlers.onStop();

        return true;
    }

    /**
     * Pause frame capture without stopping
     */
    pause() {
        if (!this.state.isCapturing) {
            return false;
        }
        this.state.isPaused = true;
        console.log('[BrowserCamera] Capture paused');
        return true;
    }

    /**
     * Resume frame capture
     */
    resume() {
        if (!this.state.isCapturing) {
            return false;
        }
        this.state.isPaused = false;
        console.log('[BrowserCamera] Capture resumed');
        return true;
    }

    /**
     * Capture frame from video and send to server
     */
    async captureAndSendFrame() {
        try {
            if (!this.videoElement || !this.canvasElement) {
                return;
            }

            // Draw video frame to canvas
            const context = this.canvasElement.getContext('2d');
            if (!context) {
                throw new Error('Failed to get canvas context');
            }

            context.drawImage(
                this.videoElement,
                0,
                0,
                this.canvasElement.width,
                this.canvasElement.height
            );

            // Convert canvas to JPEG Base64
            const imageData = this.canvasElement.toDataURL(
                'image/jpeg',
                this.config.quality
            );

            // Extract Base64 data
            const base64Data = imageData.split(',')[1];

            // Send frame
            if (this.config.useWebSocket && this.websocket?.readyState === WebSocket.OPEN) {
                this.sendFrameWebSocket(base64Data);
            } else {
                await this.sendFrameHTTP(base64Data);
            }

            // Update stats
            this.state.frameCount++;
            this.state.lastFrameTime = Date.now();
            this.updateStats();
            this.eventHandlers.onFrame({
                frameNumber: this.state.frameCount,
                timestamp: this.state.lastFrameTime,
            });
        } catch (error) {
            this.state.errorCount++;
            console.error('[BrowserCamera] Frame capture error:', error);
            this.handleError(`Frame capture error: ${error.message}`);
        }
    }

    /**
     * Send frame via WebSocket
     */
    sendFrameWebSocket(base64Data) {
        try {
            const message = {
                type: 'frame',
                data: base64Data,
            };
            this.websocket.send(JSON.stringify(message));
        } catch (error) {
            console.error('[BrowserCamera] WebSocket send error:', error);
            this.state.errorCount++;
        }
    }

    /**
     * Send frame via HTTP POST
     */
    async sendFrameHTTP(base64Data) {
        try {
            const response = await fetch('/frame/base64', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    frame: base64Data,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            if (result.status === 'success') {
                this.state.analysisResults = result.analysis;
                this.eventHandlers.onAnalysisResult(result.analysis);
            } else {
                throw new Error(result.message || 'Unknown error');
            }
        } catch (error) {
            console.error('[BrowserCamera] HTTP send error:', error);
            this.state.errorCount++;
            this.handleError(`HTTP send error: ${error.message}`);
        }
    }

    /**
     * Update and display statistics
     */
    updateStats() {
        const now = Date.now();
        const elapsed = (now - this.state.startTime) / 1000;

        if (elapsed > 0) {
            this.state.currentFPS = this.state.frameCount / elapsed;
        }

        const stats = {
            frameCount: this.state.frameCount,
            fps: this.state.currentFPS.toFixed(1),
            errors: this.state.errorCount,
            elapsedSeconds: Math.floor(elapsed),
            isCapturing: this.state.isCapturing,
            isPaused: this.state.isPaused,
            analysisResults: this.state.analysisResults,
        };

        if (this.statsElement) {
            this.statsElement.textContent = `Frames: ${stats.frameCount} | FPS: ${stats.fps} | Errors: ${stats.errors}`;
        }

        return stats;
    }

    /**
     * Handle error
     */
    handleError(message) {
        this.state.lastError = message;
        console.error('[BrowserCamera] Error:', message);

        if (this.statusElement) {
            this.statusElement.textContent = `Error: ${message}`;
            this.statusElement.style.color = 'red';
        }

        this.eventHandlers.onError(message);
    }

    /**
     * Get current status
     */
    getStatus() {
        return {
            ...this.state,
            stats: this.updateStats(),
            webSocketConnected: this.websocket?.readyState === WebSocket.OPEN,
        };
    }

    /**
     * Attach status element for display
     */
    attachStatusElement(element) {
        this.statusElement = element;
    }

    /**
     * Attach stats element for display
     */
    attachStatsElement(element) {
        this.statsElement = element;
    }
}

// Export for use in HTML
if (typeof window !== 'undefined') {
    window.BrowserCameraCapture = BrowserCameraCapture;
}
