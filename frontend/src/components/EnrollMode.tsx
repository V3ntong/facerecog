import { useState, useRef, useCallback, useEffect } from "react";
import type { EnrollValidation } from "../types";
import { validateEnroll, enrollPhoto } from "../api";

interface Photo {
  blob: Blob;
  url: string;
}

export default function EnrollMode() {
  const [name, setName] = useState("");
  const [photo, setPhoto] = useState<Photo | null>(null);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<EnrollValidation | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "error"; text: string } | null>(null);

  const [useCamera, setUseCamera] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [camError, setCamError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const cleanCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  }, []);

  useEffect(() => {
    return () => {
      if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
    };
  }, []);

  useEffect(() => {
    if (useCamera && videoRef.current && cameraActive && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(() => {
        /* ignore */
      });
    }
  }, [useCamera, cameraActive]);

  const startCamera = useCallback(async () => {
    setCamError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      setCameraActive(true);
    } catch (e: any) {
      setCamError(e?.message || "Could not access camera");
      setUseCamera(false);
    }
  }, []);

  const capturePhoto = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    if (video.videoWidth) {
      ctx.drawImage(video, 0, 0);
    }
    canvas.toBlob((blob) => {
      if (blob) {
        setPhoto((prev) => {
          if (prev) URL.revokeObjectURL(prev.url);
          return { blob, url: URL.createObjectURL(blob) };
        });
      }
    }, "image/jpeg", 0.9);
  }, []);

  // Auto-validate the selected photo before the user can enroll.
  useEffect(() => {
    if (!photo) return;
    let cancelled = false;
    setValidating(true);
    setValidation(null);
    setMessage(null);
    validateEnroll(photo.blob)
      .then((v) => {
        if (!cancelled) setValidation(v);
      })
      .catch((e: any) => {
        if (!cancelled) {
          setValidation(null);
          setMessage({ type: "error", text: e.message || "Could not check photo" });
        }
      })
      .finally(() => {
        if (!cancelled) setValidating(false);
      });
    return () => {
      cancelled = true;
    };
  }, [photo]);

  const onFilePicked = useCallback((file: File | null) => {
    if (!file) return;
    setPhoto((prev) => {
      if (prev) URL.revokeObjectURL(prev.url);
      return { blob: file, url: URL.createObjectURL(file) };
    });
  }, []);

  const submit = useCallback(async () => {
    if (!photo) return;
    const trimmed = name.trim();
    if (!trimmed) {
      setMessage({ type: "error", text: "Please enter the person's full name." });
      return;
    }
    if (!validation || !validation.ok) {
      setMessage({ type: "error", text: "The photo needs exactly one face before you can enroll." });
      return;
    }
    setSubmitting(true);
    setMessage(null);
    try {
      const res = await enrollPhoto(photo.blob, trimmed);
      setMessage({ type: "ok", text: res.message });
      setValidation(null);
    } catch (e: any) {
      setMessage({ type: "error", text: e.message || "Enrollment failed" });
    } finally {
      setSubmitting(false);
    }
  }, [photo, name, validation]);

  const nameValid = name.trim().length > 0;

  return (
    <div className="space-y-4">
      <div
        className="rounded-2xl p-5"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <h3 className="text-sm font-medium mb-3" style={{ color: "var(--text-secondary)" }}>
          Enroll a new face
        </h3>

        {/* Name */}
        <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>
          Full name
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            setMessage(null);
          }}
          placeholder="e.g. Maria Santos"
          maxLength={100}
          className="w-full px-3 py-2.5 rounded-xl text-sm outline-none transition-colors"
          style={{
            background: "var(--bg-secondary)",
            color: "var(--text-primary)",
            border: "1px solid var(--border)",
          }}
        />
        <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
          Letters, digits, spaces, dots, apostrophes and hyphens only.
        </p>

        {/* Photo */}
        <div className="mt-4">
          <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>
            Photo (exactly one face, clear and well-lit)
          </label>

          {useCamera ? (
            <div
              className="relative rounded-2xl overflow-hidden"
              style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}
            >
              {cameraActive ? (
                <>
                  <video ref={videoRef} autoPlay playsInline muted className="w-full" style={{ transform: "scaleX(-1)" }} />
                  <div className="absolute bottom-3 left-0 right-0 flex justify-center gap-2">
                    <button
                      onClick={capturePhoto}
                      className="px-5 py-2 rounded-xl text-sm font-medium text-white cursor-pointer"
                      style={{ background: "var(--accent)" }}
                    >
                      Use this photo
                    </button>
                    <button
                      onClick={() => {
                        cleanCamera();
                        setUseCamera(false);
                      }}
                      className="px-5 py-2 rounded-xl text-sm font-medium cursor-pointer"
                      style={{ background: "var(--bg-secondary)", color: "var(--text-secondary)" }}
                    >
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center gap-4 p-8">
                  {camError && (
                    <p className="text-sm" style={{ color: "var(--error)" }}>
                      {camError}
                    </p>
                  )}
                  <button
                    onClick={cleanCamera}
                    className="px-5 py-2 rounded-xl text-sm font-medium cursor-pointer"
                    style={{ background: "var(--bg-secondary)", color: "var(--text-secondary)" }}
                  >
                    Use a file instead
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full px-4 py-6 rounded-xl text-sm cursor-pointer transition-colors"
                style={{
                  background: "var(--bg-secondary)",
                  color: "var(--text-secondary)",
                  border: "1px dashed var(--border)",
                }}
              >
                {photo ? "Choose a different photo" : "Click to pick a photo"}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => onFilePicked(e.target.files?.[0] ?? null)}
              />
              {!photo && (
                <button
                  onClick={() => {
                    setUseCamera(true);
                    startCamera();
                  }}
                  className="mt-2 px-4 py-2 rounded-xl text-sm font-medium cursor-pointer"
                  style={{ background: "var(--bg-secondary)", color: "var(--text-secondary)" }}
                >
                  Or use the camera
                </button>
              )}
            </>
          )}

          {photo && (
            <div className="mt-3 flex items-start gap-3">
              <img
                src={photo.url}
                alt="Preview"
                className="w-24 h-24 object-cover rounded-xl"
                style={{ border: "1px solid var(--border)" }}
              />
              <div className="flex-1">
                {validating ? (
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    Checking photo...
                  </p>
                ) : validation ? (
                  <p
                    className="text-xs font-medium"
                    style={{
                      color: validation.ok ? "var(--accent)" : "var(--error)",
                    }}
                  >
                    {validation.message}
                  </p>
                ) : null}
                <button
                  onClick={() => {
                    setPhoto((prev) => {
                      if (prev) URL.revokeObjectURL(prev.url);
                      return null;
                    });
                    setValidation(null);
                  }}
                  className="mt-2 text-xs underline cursor-pointer"
                  style={{ color: "var(--text-muted)" }}
                >
                  Remove photo
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Submit */}
        <button
          onClick={submit}
          disabled={submitting || !photo || !nameValid || !validation?.ok}
          className="mt-4 w-full px-6 py-3 rounded-xl text-sm font-medium text-white transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ background: "var(--accent)" }}
        >
          {submitting ? "Enrolling..." : "Enroll"}
        </button>
      </div>

      {message && (
        <div
          className="px-4 py-3 rounded-xl text-sm"
          style={{
            background: `color-mix(in srgb, ${message.type === "ok" ? "var(--accent)" : "var(--error)"} 10%, var(--bg-card))`,
            color: message.type === "ok" ? "var(--accent)" : "var(--error)",
            border: `1px solid color-mix(in srgb, ${message.type === "ok" ? "var(--accent)" : "var(--error)"} 25%, transparent)`,
          }}
        >
          {message.text}
        </div>
      )}

      {photo && !validating && (!validation || !validation.ok) && nameValid && (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          Enrollment is blocked until the photo contains exactly one face.
        </p>
      )}

      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}