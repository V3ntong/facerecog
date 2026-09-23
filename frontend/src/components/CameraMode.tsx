import { useState, useRef, useCallback, useEffect } from "react";

interface Props {
  onCapture: (blob: Blob) => void;
  onVideoRecorded: (blob: Blob) => void;
  loading: boolean;
}

const REC_DURATION_MS = 60_000;
const COUNTDOWN_FROM_MS = 10_000;

const recorderSupported =
  typeof window !== "undefined" &&
  typeof MediaRecorder !== "undefined" &&
  MediaRecorder.isTypeSupported("video/webm");

export default function CameraMode({ onCapture, onVideoRecorded, loading }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [streaming, setStreaming] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [recTime, setRecTime] = useState(0);
  const streamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);

  const startCamera = useCallback(async () => {
    setCameraError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      setStreaming(true);
    } catch (e: any) {
      const name = e?.name || "";
      if (name === "NotAllowedError" || name === "SecurityError") {
        setCameraError("Camera access denied. Allow camera permission in the browser and try again.");
      } else if (name === "NotFoundError" || name === "OverconstrainedError") {
        setCameraError("No camera found on this device.");
      } else if (name === "NotReadableError") {
        setCameraError("Camera is in use by another app. Close it and try again.");
      } else {
        setCameraError(e?.message || "Could not access camera");
      }
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        // ignore
      }
    }
    mediaRecorderRef.current = null;
    setRecording(false);
  }, []);

  const stopCamera = useCallback(() => {
    stopRecording();
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setStreaming(false);
  }, [stopRecording]);

  const startRecording = useCallback(() => {
    if (!recorderSupported) {
      setCameraError("Video recording is not supported in this browser.");
      return;
    }
    if (!streaming || !streamRef.current) return;

    chunksRef.current = [];
    let mr: MediaRecorder;
    try {
      mr = new MediaRecorder(streamRef.current, { mimeType: "video/webm" });
    } catch {
      setCameraError("Could not start video recording. Try a still capture instead.");
      return;
    }

    mr.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
    };
    mr.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "video/webm" });
      chunksRef.current = [];
      if (blob.size > 0) onVideoRecorded(blob);
    };

    mediaRecorderRef.current = mr;
    mr.start(1000);
    const started = Date.now();
    setRecTime(0);
    setRecording(true);
    timerRef.current = window.setInterval(() => {
      const elapsed = Date.now() - started;
      setRecTime(elapsed);
      if (elapsed >= REC_DURATION_MS) stopRecording();
    }, 200);
  }, [streaming, onVideoRecorded, stopRecording]);

  // Attach the stream once the <video> element is actually mounted
  // (it is conditionally rendered only when `streaming` is true).
  useEffect(() => {
    if (!streaming || !videoRef.current) return;
    const video = videoRef.current;
    video.srcObject = streamRef.current;
    const onLoaded = () => {
      video.play().catch((err) =>
        setCameraError("Could not start video playback: " + (err?.message || err))
      );
    };
    video.addEventListener("loadedmetadata", onLoaded);
    return () => video.removeEventListener("loadedmetadata", onLoaded);
  }, [streaming]);

  const capture = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (blob) onCapture(blob);
    }, "image/jpeg", 0.9);
  }, [onCapture]);

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  const remaining = Math.max(0, REC_DURATION_MS - recTime);
  const inCountdown = recording && remaining <= COUNTDOWN_FROM_MS;

  return (
    <div className="space-y-4">
      {cameraError && (
        <div
          className="px-4 py-3 rounded-xl text-sm"
          style={{
            background: "color-mix(in srgb, var(--error) 10%, var(--bg-card))",
            color: "var(--error)",
          }}
        >
          {cameraError}
        </div>
      )}

      {!recorderSupported && (
        <div
          className="px-4 py-3 rounded-xl text-sm"
          style={{
            background: "color-mix(in srgb, var(--warning, #f59e0b) 10%, var(--bg-card))",
            color: "var(--warning, #f59e0b)",
            border: "1px solid color-mix(in srgb, var(--warning, #f59e0b) 25%, transparent)",
          }}
        >
          Video recording is not supported in this browser. Still capture is still available.
        </div>
      )}

      <div
        className="relative rounded-2xl overflow-hidden"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        {streaming ? (
          <>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full rounded-2xl"
              style={{ transform: "scaleX(-1)" }}
            />
            {/* Recording indicator + timer */}
            {recording && (
              <div className="absolute top-3 right-3 flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium"
                style={{
                  background: "rgba(0,0,0,0.6)",
                  color: inCountdown ? "#f87171" : "#ffffff",
                }}
              >
                <span
                  className="w-2.5 h-2.5 rounded-full animate-pulse"
                  style={{
                    background: inCountdown ? "#f87171" : "#f87171",
                    boxShadow: "0 0 0 0 rgba(248,113,113,0.6)",
                  }}
                />
                {inCountdown
                  ? `Stopping in ${Math.ceil(remaining / 1000)}s`
                  : `REC ${formatTime(recTime / 1000)}`}
              </div>
            )}
            <div className="absolute bottom-4 left-0 right-0 flex justify-center gap-3">
              {recording ? (
                <button
                  onClick={stopRecording}
                  className="px-6 py-2.5 rounded-xl text-sm font-medium text-white transition-all cursor-pointer"
                  style={{ background: "#dc2626" }}
                >
                  Stop Recording
                </button>
              ) : (
                <>
                  <button
                    onClick={capture}
                    disabled={loading}
                    className="px-6 py-2.5 rounded-xl text-sm font-medium text-white transition-all cursor-pointer disabled:opacity-50"
                    style={{ background: "var(--accent)" }}
                  >
                    {loading ? "Processing..." : "Capture"}
                  </button>
                  <button
                    onClick={startRecording}
                    disabled={!recorderSupported}
                    className="px-6 py-2.5 rounded-xl text-sm font-medium text-white transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ background: "#dc2626" }}
                    title="Record up to 60 seconds of video to recognize"
                  >
                    Record video
                  </button>
                  <button
                    onClick={stopCamera}
                    className="px-6 py-2.5 rounded-xl text-sm font-medium transition-all cursor-pointer"
                    style={{ background: "var(--bg-secondary)", color: "var(--text-secondary)" }}
                  >
                    Stop
                  </button>
                </>
              )}
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center gap-4 p-12">
            <div
              className="w-20 h-20 rounded-2xl flex items-center justify-center text-3xl"
              style={{ background: "var(--bg-secondary)", color: "var(--text-muted)" }}
            >
              📸
            </div>
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              Start your camera to recognize people in real time
            </p>
            <button
              onClick={startCamera}
              className="px-8 py-3 rounded-xl text-sm font-medium text-white transition-all cursor-pointer"
              style={{ background: "var(--accent)" }}
            >
              Start Camera
            </button>
          </div>
        )}
      </div>

      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}