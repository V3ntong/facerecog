import { useState, useCallback, useEffect } from "react";
import type { RecognitionResult } from "./types";
import { recognizeFile, recognizeFrame } from "./api";
import UploadMode from "./components/UploadMode";
import CameraMode from "./components/CameraMode";
import ResultCard from "./components/ResultCard";
import Header from "./components/Header";
import ErrorBanner from "./components/ErrorBanner";

type Mode = "upload" | "camera";

export default function App() {
  const [mode, setMode] = useState<Mode>("upload");
  const [result, setResult] = useState<RecognitionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dark, setDark] = useState(() => {
    if (typeof window !== "undefined") {
      return window.matchMedia("(prefers-color-scheme: dark)").matches;
    }
    return false;
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  const handleFileUpload = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await recognizeFile(file);
      setResult(res);
    } catch (e: any) {
      setError(e.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleFrameCapture = useCallback(async (blob: Blob) => {
    setLoading(true);
    setError(null);
    try {
      const res = await recognizeFrame(blob);
      setResult(res);
    } catch (e: any) {
      setError(e.message || "Frame recognition failed");
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--bg-primary)" }}>
      <Header dark={dark} onToggleDark={() => setDark(!dark)} />

      <main className="flex-1 w-full max-w-3xl mx-auto px-4 pb-12">
        <div className="flex justify-center gap-1 mb-6 mt-2 p-1 rounded-xl" style={{ background: "var(--bg-secondary)" }}>
          {(["upload", "camera"] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); setResult(null); setError(null); }}
              className="px-6 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer"
              style={{
                background: mode === m ? "var(--bg-card)" : "transparent",
                color: mode === m ? "var(--accent)" : "var(--text-secondary)",
                boxShadow: mode === m ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
              }}
            >
              {m === "upload" ? "Upload" : "Camera"}
            </button>
          ))}
        </div>

        {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

        {mode === "upload" ? (
          <UploadMode onFileSelect={handleFileUpload} loading={loading} />
        ) : (
          <CameraMode onCapture={handleFrameCapture} loading={loading} />
        )}

        {loading && (
          <div className="mt-6 space-y-3">
            <div className="skeleton h-12 w-full" />
            <div className="skeleton h-8 w-3/4" />
            <div className="skeleton h-8 w-1/2" />
          </div>
        )}

        {!loading && result && <ResultCard result={result} />}

        <div className="mt-8 text-center text-xs" style={{ color: "var(--text-muted)" }}>
          This app uses face recognition. Only the 6 enrolled people are ever matched.
        </div>
      </main>
    </div>
  );
}
