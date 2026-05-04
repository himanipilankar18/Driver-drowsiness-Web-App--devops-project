# Browser Camera - Quick Reference

## 🚀 Getting Started (5 minutes)

### Step 1: Start Server
```bash
export CAMERA_MODE=browser
python -m uvicorn backend.main:app --reload
```

### Step 2: Open Dashboard
```
http://localhost:8000
```

### Step 3: Click "Browser Camera" → "Start Browser Camera"

✅ Done! Frames are now being captured and processed.

---

## 📱 What Works

| Feature | Status |
|---------|--------|
| Browser camera access | ✅ Works |
| Real-time frame capture | ✅ Works |
| WebSocket streaming | ✅ Works |
| HTTP fallback | ✅ Works |
| Face detection | ✅ Works |
| Fatigue analysis | ✅ Works |
| Distraction analysis | ✅ Works |
| Multi-platform | ✅ Chrome, Firefox, Safari, Edge |

---

## 🔧 Configuration Presets

### Low Latency (Fast Internet)
```javascript
{
    frameRate: 15,
    quality: 0.95,
    maxWidth: 1280,
    maxHeight: 720,
}
```

### Balanced (Recommended)
```javascript
{
    frameRate: 12,      // Default
    quality: 0.85,      // Default
    maxWidth: 1280,
    maxHeight: 720,
}
```

### Low Bandwidth (Slow Internet)
```javascript
{
    frameRate: 8,
    quality: 0.70,
    maxWidth: 640,
    maxHeight: 480,
}
```

---

## 📡 API Quick Reference

### Start Browser Mode
```bash
curl -X POST http://localhost:8000/configure/browser
```

### Send Frame (HTTP)
```bash
curl -X POST http://localhost:8000/frame/base64 \
  -H "Content-Type: application/json" \
  -d '{"frame":"base64_jpeg_data..."}'
```

### Get Statistics
```bash
curl http://localhost:8000/frame/stats
```

### Check Status
```bash
curl http://localhost:8000/status
```

---

## 🎯 Common Tasks

### Enable Browser Camera Automatically
```bash
# Set environment variable
export CAMERA_MODE=browser

# Start application
python -m uvicorn backend.main:app --reload
```

### Test from Command Line
```bash
# Check if server is running
curl http://localhost:8000/status

# Get available modes
curl http://localhost:8000/modes

# Get frame stats
curl http://localhost:8000/frame/stats
```

### Browser Console Debugging
```javascript
// Open DevTools (F12) → Console

// Access camera object
console.log(camera);

// Check current FPS
console.log(camera.getStatus().stats.fps);

// Enable all logs
camera.eventHandlers.onFrame = (info) => {
    console.log('Frame:', info.frameNumber);
};
```

---

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| Camera permission denied | Check browser permissions |
| No frames in stats | Check if monitoring is running (`POST /start`) |
| High latency | Lower frameRate or maxWidth |
| High CPU usage | Reduce quality or frameRate |
| Frames rejected | Check frame size < 10MB |
| WebSocket errors | Try HTTP mode: `useWebSocket: false` |

---

## 📊 Performance Targets

| Metric | Expected |
|--------|----------|
| FPS (12 frameRate) | ~12 fps |
| Latency | 100-200ms |
| CPU usage | 10-20% |
| Memory | < 100MB |
| Bandwidth (quality 0.85) | ~600 kbps |

---

## 💡 Pro Tips

1. **Quality vs Bandwidth**: Lower quality = smaller files
   ```javascript
   quality: 0.70   // ~40KB per frame
   quality: 0.85   // ~60KB per frame
   quality: 0.95   // ~100KB per frame
   ```

2. **Latency vs Quality**: Lower FPS = lower latency
   ```javascript
   frameRate: 10   // Lowest latency
   frameRate: 12   // Balanced
   frameRate: 15   // Best responsiveness
   ```

3. **Check Network Speed**:
   ```javascript
   if (navigator.connection?.downlink < 2) {
       frameRate = 8;  // Slow network
   }
   ```

4. **Monitor Resources**:
   ```javascript
   setInterval(() => {
       const stats = camera.getStatus();
       console.log('FPS:', stats.stats.fps, 'Errors:', stats.stats.errors);
   }, 1000);
   ```

---

## 📋 Deployment Checklist

- [ ] CAMERA_MODE=browser environment variable set
- [ ] WebSocket support enabled
- [ ] CORS configured (if needed)
- [ ] HTTPS/WSS for production
- [ ] Camera permissions handled
- [ ] Error handling in place
- [ ] Statistics monitoring active
- [ ] Performance tested

---

## 🔐 Security Checklist

- [ ] CORS properly configured
- [ ] Frame size limits enforced
- [ ] HTTPS/TLS enabled (production)
- [ ] User permissions respected
- [ ] Rate limiting active
- [ ] Error messages sanitized

---

## 📞 Support

### Check Logs
```bash
# View server logs
python -m uvicorn backend.main:app --reload --log-level debug

# View browser console
# Open DevTools (F12) → Console tab
```

### Enable Debug Mode
```javascript
// In browser console
camera.eventHandlers.onFrame = (info) => {
    console.log(`Frame ${info.frameNumber}`);
};

camera.eventHandlers.onAnalysisResult = (result) => {
    console.log('Analysis:', result);
};

camera.eventHandlers.onError = (error) => {
    console.error('Error:', error);
};
```

---

## 🚀 Next Steps

1. ✅ Basic setup complete
2. → Customize frameRate/quality for your needs
3. → Deploy to production
4. → Monitor performance
5. → Optimize based on real-world usage

---

**Ready to Deploy?** 🚀

Browser camera mode is production-ready!

All documentation: [BROWSER_CAMERA_GUIDE.md](BROWSER_CAMERA_GUIDE.md)
