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
}

export interface RecognitionResult {
  type: "image" | "video" | "frame";
  people: RecognizedPerson[];
  sentence: string;
  timeline?: TimelineEntry[];
  filename?: string;
}

export interface HealthResponse {
  status: string;
  embeddings_loaded: number;
  threshold: number;
  ai_provider: string;
}
