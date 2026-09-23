export interface RecognizedPerson {
  name: string;
  score: number;
  box: [number, number, number, number];
  doing?: string;
}

export interface TimelineEntry {
  person: string;
  first_seen: number;
  last_seen: number;
  confidence: number;
  doing?: string;
}

export interface RecognitionResult {
  type: "image" | "video" | "frame";
  people: RecognizedPerson[];
  sentence: string;
  summary?: string | null;
  timeline?: TimelineEntry[];
  filename?: string;
  notice?: string | null;
}

export interface EnrollValidation {
  ok: boolean;
  face_count: number;
  message: string;
}

export interface EnrollResult {
  ok: boolean;
  person: string;
  person_id: number;
  is_new: boolean;
  embeddings_total: number;
  message: string;
}

export interface HealthResponse {
  status: string;
  embeddings_loaded: number;
  threshold: number;
  ai_provider: string;
}
