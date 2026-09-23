import type { RecognitionResult, HealthResponse, EnrollValidation, EnrollResult } from "./types";

const BASE = "";

export async function recognizeFile(file: File): Promise<RecognitionResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/recognize`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Recognition failed");
  }
  return res.json();
}

export async function recognizeFrame(
  blob: Blob,
  describe = false
): Promise<RecognitionResult> {
  const form = new FormData();
  form.append("file", blob, "frame.jpg");
  if (describe) form.append("describe", "true");
  const res = await fetch(`${BASE}/api/recognize/frame`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Frame recognition failed");
  }
  return res.json();
}

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE}/api/health`);
  return res.json();
}

export async function validateEnroll(blob: Blob): Promise<EnrollValidation> {
  const form = new FormData();
  form.append("file", blob, "enroll-photo.jpg");
  const res = await fetch(`${BASE}/api/enroll/validate`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Enrollment check failed");
  }
  return res.json();
}

export async function enrollPhoto(blob: Blob, name: string): Promise<EnrollResult> {
  const form = new FormData();
  form.append("file", blob, "enroll-photo.jpg");
  form.append("name", name);
  const res = await fetch(`${BASE}/api/enroll`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Enrollment failed");
  }
  return res.json();
}
