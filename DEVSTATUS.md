# WhoIsThere — Dev Status

**Last updated:** 2026-09-22  
**Phase:** Step 6 of 7 (Frontend built, tests + README remaining)

---

## Completed Steps

### Step 0: Inspect DB + Filesystem
- Connected to SQL Server `localhost\FaceRecognitionDB` via ODBC Driver 18, Windows Auth
- Database exists, zero tables (clean slate)
- `C:\FaceDataset` has 6 empty subfolders: Dajes, Maquilan, Moraleja, Pendang, Pogoy, Urmenita
- **Blocker identified:** No images in the dataset folders yet

### Step 1: Project Scaffolding
- Created full directory structure: `backend/app/`, `backend/tests/`, `frontend/src/`, `scripts/`
- `.env.example` with all config vars (DB, AI, recognition, server)
- `.gitignore` set up
- `backend/requirements.txt` with all Python dependencies
- `backend/app/config.py` — Pydantic settings, connection string builder
- `backend/app/database.py` — SQLAlchemy engine, `init_db()` creates Person + FaceEmbedding tables, `ensure_person()` helper

### Step 2: Enrollment
- `backend/app/services/enrollment.py` — scans `C:\FaceDataset`, reads images, detects faces, stores 512-d embeddings
  - Idempotent (skips already-enrolled persons)
  - Skips: no face, multiple faces, low quality, too small
  - Prints summary table
- `backend/app/enroll.py` — CLI entrypoint: `python -m app.enroll`
- Also supports importing images as VARBINARY into a PersonImage table

### Step 3: Recognition Engine
- `backend/app/services/face_service.py` — InsightFace buffalo_l (SCRFD detector + ArcFace 512-d), with DeepFace fallback
- `backend/app/services/recognition.py` — core logic:
  - `load_embeddings()` — loads all from DB into memory
  - `recognize_faces()` — top-k mean cosine similarity per person
  - `calibrate_threshold()` — leave-one-out test, prints accuracy report
  - `recognize_video_frames()` — simple tracking across frames with majority vote
  - `build_sentence()` — "{Names} spotted {doing}."

### Step 4: Description Module
- `backend/app/services/description.py` — vision LLM adapter
  - Provider adapter: Anthropic Claude + OpenAI GPT-4o via env `AI_PROVIDER`
  - Prompt engineering: returns JSON `{"people":[{"name":"","doing":""}]}`
  - Names come ONLY from local model, LLM only describes actions
  - Graceful fallback: if LLM fails, still returns names without "doing"

### Step 5: FastAPI Backend
- `backend/app/main.py` — FastAPI app with CORS, lifespan (loads embeddings at startup)
- `backend/app/routes/recognize.py` — three endpoints:
  - `GET /api/health` — status, embedding count, threshold
  - `POST /api/recognize` — multipart file upload (image or video)
  - `POST /api/recognize/frame` — live camera frame, optional describe flag
  - Rate limiting, file type/size validation, temp file cleanup for video
- `backend/app/calibrate.py` — CLI: `python -m app.calibrate`

### Step 6: React Frontend (in progress)
- Vite + React 19 + TypeScript 6 + Tailwind CSS v4
- Proxy config: `/api` → `localhost:8000`
- Components built:
  - `Header.tsx` — logo + dark/light toggle
  - `UploadMode.tsx` — drag-and-drop zone, preview, file type hints
  - `CameraMode.tsx` — getUserMedia, start/stop/capture buttons
  - `ResultCard.tsx` — sentence, person chips with colors, timeline, face details
  - `ErrorBanner.tsx` — dismissible error
  - `useHealth.ts` — health check hook
- `src/api.ts` — typed fetch wrappers
- `src/types.ts` — TypeScript interfaces
- **TypeScript compiles cleanly** ✓

---

## Remaining: Step 7 — Tests + README

### Tests needed
| Test | File | What it verifies |
|------|------|------------------|
| Unit: `build_sentence` | `tests/test_recognition.py` | Sentence construction for 0, 1, 2+ names, unknowns |
| Unit: `cosine_similarity` | `tests/test_face_service.py` | Identical vectors → 1.0, orthogonal → 0.0 |
| Unit: threshold logic | `tests/test_recognition.py` | Faces above/below threshold classified correctly |
| API: `/api/health` | `tests/test_api.py` | Returns 200, correct shape |
| API: `/api/recognize` (image) | `tests/test_api.py` | Upload sample image, returns people + sentence |
| API: `/api/recognize/frame` | `tests/test_api.py` | Frame endpoint returns type=frame |

### README needed
Exact Windows setup steps:
1. Prerequisites: Python 3.11+, Node 18+, ODBC Driver 18
2. SQL Server connection string (SQL auth + Windows auth examples)
3. `.env` setup
4. Place images in `C:\FaceDataset\<Name>\`
5. `pip install -r requirements.txt`
6. `python -m app.enroll` (reports per-person counts)
7. `python -m app.calibrate` (prints accuracy, updates threshold)
8. `python -m uvicorn app.main:app --reload` (backend on :8000)
9. `cd frontend && npm install && npm run dev` (frontend on :5173)
10. Open http://localhost:5173

---

## Known Issues / Notes

| Issue | Status | Fix |
|-------|--------|-----|
| InsightFace model download corrupted on first try | Fixed | Re-downloaded via Python script, organized into `buffalo_l/` folder |
| DeepFace not installable on Python 3.14 | Known | TensorFlow has no 3.14 wheel; InsightFace works fine |
| `C:\FaceDataset` folders are empty | **BLOCKER** | You must add images before enrollment + calibration work |
| LLM description requires API key | Not set | Add `AI_API_KEY` to `.env` for descriptions; works without it (names only) |
| Path with `&` causes npm/npx issues | Workaround | Use `node node_modules/...` instead of `npx` |

---

## Tomorrow's Plan

### Morning priorities (start here)

1. **Add test images** to `C:\FaceDataset\<Name>\` (at least 3-5 per person for calibration to work)
2. **Run enrollment:** `cd backend && python -m app.enroll`
3. **Run calibration:** `cd backend && python -m app.calibrate` — update `RECOGNITION_THRESHOLD` in `.env`
4. **Set AI_API_KEY** in `.env` if you want descriptions

### After enrollment works

5. **Write unit tests** — `build_sentence`, `cosine_similarity`, threshold logic
6. **Write API tests** — health, recognize (image), recognize (frame) using a sample image
7. **Run all tests:** `cd backend && python -m pytest tests/ -v`
8. **Write README.md** with exact setup steps
9. **End-to-end test** — upload photo of enrolled person, verify `<Name> spotted <doing>.` appears

### Nice-to-have / polish
- Video timeline in frontend (backend supports it, UI renders it)
- Live camera recognition loop (send frame every ~1s, draw overlay boxes)
- Frontend: show face bounding boxes on the preview image
- Dark mode persistence in localStorage



sdfahsdjkashjhdsjkhfkljasddhf
fasdjhkffgasdhjfgasdhjf
asdfjhgasdlkjfhasdhjff
asdfhjgasdhjfgasdjkhfg