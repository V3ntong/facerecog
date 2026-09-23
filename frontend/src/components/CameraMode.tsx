import { useState, useRef, useCallback, useEffect } from "react";

interface Props {
  onCapture: (blob: Blob) => void;
  loading: boolean;
}

export default function CameraMode({ onCapture, loading }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [streaming, setStreaming] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

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

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setStreaming(false);
  }, []);

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
    return () => stopCamera();
  }, [stopCamera]);

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
            <div className="absolute bottom-4 left-0 right-0 flex justify-center gap-3">
              <button
                onClick={capture}
                disabled={loading}
                className="px-6 py-2.5 rounded-xl text-sm font-medium text-white transition-all cursor-pointer disabled:opacity-50"
                style={{ background: "var(--accent)" }}
              >
                {loading ? "Processing..." : "Capture"}
              </button>
              <button
                onClick={stopCamera}
                className="px-6 py-2.5 rounded-xl text-sm font-medium transition-all cursor-pointer"
                style={{ background: "var(--bg-secondary)", color: "var(--text-secondary)" }}
              >
                Stop
              </button>
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
