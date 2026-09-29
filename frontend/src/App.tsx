import { useCallback, useEffect, useState } from "react";
import type { RecognitionResult } from "./types";
import { recognizeFile, recognizeFrame } from "./api";
import { PEOPLE, spottedNames } from "./people";
import { providerLabel } from "./format";
import useHealth from "./useHealth";
import ModeTabs from "./components/ModeTabs";
import Rail from "./components/Rail";
import Slip from "./components/Slip";
import UploadMode from "./components/UploadMode";
import CameraMode from "./components/CameraMode";
import EnrollMode from "./components/EnrollMode";
import EvidencePlate from "./components/EvidencePlate";
import type { Evidence } from "./components/EvidencePlate";
import AppearanceBars from "./components/AppearanceBars";
import Sightings from "./components/Sightings";

type Mode = "upload" | "camera" | "enroll";

const TABS: { id: Mode; label: string }[] = [
  { id: "upload", label: "Photo or clip" },
  { id: "camera", label: "Camera" },
  { id: "enroll", label: "Add a face" },
];

const THEME_KEY = "ohahay:theme";

function initialDark(): boolean {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "dark") return true;
  if (saved === "light") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/** A browser network failure says nothing a reader can act on, so say something. */
function readableError(error: unknown, fallback: string): string {
  const message = error instanceof Error ? error.message : "";
  if (!message || /failed to fetch|network|load failed/i.test(message)) {
    return "The server didn't answer. Start the backend, then try again.";
  }
  return message || fallback;
}

export default function App() {
  const [mode, setMode] = useState<Mode>("upload");
  const [result, setResult] = useState<RecognitionResult | null>(null);
  const [resultKey, setResultKey] = useState(0);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dark, setDark] = useState(initialDark);
  const { health, failed: healthFailed, refresh: refreshHealth } = useHealth();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem(THEME_KEY, dark ? "dark" : "light");
  }, [dark]);

  // Reclaim the object URL of whichever print is being replaced.
  useEffect(() => {
    if (!evidence) return;
    return () => URL.revokeObjectURL(evidence.url);
  }, [evidence]);

  const handleFileUpload = useCallback(async (file: File) => {
    setEvidence({
      url: URL.createObjectURL(file),
      kind: file.type.startsWith("video/") ? "video" : "image",
    });
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await recognizeFile(file));
      setResultKey((key) => key + 1);
    } catch (caught) {
      setError(readableError(caught, "That file couldn't be read."));
    } finally {
      setLoading(false);
    }
  }, []);

  const handleFrameCapture = useCallback(async (blob: Blob) => {
    setEvidence({ url: URL.createObjectURL(blob), kind: "image" });
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await recognizeFrame(blob));
      setResultKey((key) => key + 1);
    } catch (caught) {
      setError(readableError(caught, "That frame couldn't be read."));
    } finally {
      setLoading(false);
    }
  }, []);

  const handleVideoRecorded = useCallback(
    async (blob: Blob) => {
      const file = new File([blob], "camera-recording.webm", { type: "video/webm" });
      await handleFileUpload(file);
    },
    [handleFileUpload]
  );

  const spotted = result ? spottedNames(result.people) : [];
  const status = loading
    ? evidence?.kind === "video"
      ? "Looking for anyone it knows in this clip…"
      : "Looking for anyone it knows…"
    : null;

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <Rail
        health={health}
        healthFailed={healthFailed}
        spotted={spotted}
        resultKey={resultKey}
        dark={dark}
        onToggleDark={() => setDark((value) => !value)}
      />

      <main className="min-w-0 flex-1">
        <div className="w-full max-w-[46rem] px-5 py-6 lg:px-10 lg:py-9">
          <ModeTabs
            tabs={TABS}
            active={mode}
            onSelect={(id) => {
              setMode(id as Mode);
              setError(null);
            }}
          />

          <div
            id={`panel-${mode}`}
            role="tabpanel"
            aria-labelledby={`tab-${mode}`}
            className="pt-5"
          >
            {mode === "upload" && (
              <UploadMode onFileSelect={handleFileUpload} loading={loading} />
            )}
            {mode === "camera" && (
              <CameraMode
                onCapture={handleFrameCapture}
                onVideoRecorded={handleVideoRecorded}
                loading={loading}
              />
            )}
            {mode === "enroll" && <EnrollMode onEnrolled={refreshHealth} />}
          </div>

          {error && (
            <Slip kind="failure" onDismiss={() => setError(null)} className="mt-4">
              {error}
            </Slip>
          )}

          {evidence && (
            <div className="mt-5">
              <EvidencePlate
                evidence={evidence}
                people={result && result.type !== "video" ? result.people : []}
              />
            </div>
          )}

          {status && <p className="type-record mt-3 text-slate">{status}</p>}

          {!loading && result && (
            <>
              <Sightings result={result} resultKey={resultKey} />
              {result.timeline && result.timeline.length > 0 && (
                <AppearanceBars timeline={result.timeline} />
              )}
            </>
          )}

          <p className="type-record mt-8 max-w-[64ch] text-slate">
            When it describes what someone is doing, that photo goes to{" "}
            {health ? providerLabel(health.ai_provider) : "a vision model"}. Matching only ever
            happens against the {PEOPLE.length} people this desk keeps prints of.
          </p>
        </div>
      </main>
    </div>
  );
}
