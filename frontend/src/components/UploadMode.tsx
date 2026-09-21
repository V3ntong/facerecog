import { useState, useRef, useCallback } from "react";

interface Props {
  onFileSelect: (file: File) => void;
  loading: boolean;
}

export default function UploadMode({ onFileSelect, loading }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((file: File) => {
    setFileName(file.name);
    if (file.type.startsWith("image/")) {
      const url = URL.createObjectURL(file);
      setPreview(url);
    } else {
      setPreview(null);
    }
    onFileSelect(file);
  }, [onFileSelect]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const onChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }, [handleFile]);

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className="relative rounded-2xl border-2 border-dashed p-10 text-center cursor-pointer transition-all duration-200"
        style={{
          borderColor: dragOver ? "var(--accent)" : "var(--border)",
          background: dragOver
            ? "color-mix(in srgb, var(--accent) 5%, var(--bg-card))"
            : "var(--bg-card)",
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*,video/*"
          onChange={onChange}
          className="hidden"
        />

        {preview ? (
          <div className="flex flex-col items-center gap-3">
            <img
              src={preview}
              alt="Preview"
              className="max-h-64 rounded-xl object-contain"
            />
            <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
              {fileName}
            </span>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              Click or drop to replace
            </span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center text-2xl"
              style={{ background: "var(--bg-secondary)", color: "var(--text-muted)" }}
            >
              {loading ? "⏳" : "📷"}
            </div>
            <div>
              <p className="font-medium" style={{ color: "var(--text-primary)" }}>
                Drop an image or video here
              </p>
              <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
                or click to browse
              </p>
            </div>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              JPG, PNG, BMP, WebP, GIF, MP4, MOV, AVI, WebM — max 100 MB
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
