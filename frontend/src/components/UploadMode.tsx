import { useCallback, useRef, useState } from "react";

interface Props {
  onFileSelect: (file: File) => void;
  loading: boolean;
}

/**
 * The drop target is the input and nothing else: the chosen photo appears once,
 * on the evidence plate below, instead of being previewed twice.
 */
export default function UploadMode({ onFileSelect, loading }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      setDragOver(false);
      const file = event.dataTransfer.files[0];
      if (file) onFileSelect(file);
    },
    [onFileSelect]
  );

  const onChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (file) onFileSelect(file);
      // So the same file can be picked again after a failed read.
      event.target.value = "";
    },
    [onFileSelect]
  );

  return (
    <div
      role="button"
      tabIndex={0}
      aria-disabled={loading}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          inputRef.current?.click();
        }
      }}
      onDragOver={(event) => {
        event.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      className={`border border-dashed px-4 py-7 transition-colors ${
        loading ? "pointer-events-none opacity-50" : "cursor-pointer"
      } ${dragOver ? "border-ink bg-flash" : "border-dim hover:border-ink"}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*,video/*"
        onChange={onChange}
        className="hidden"
      />
      <p className="type-ui text-ink">Drop a photo or a clip here, or click to choose one.</p>
      <p className="type-ui mt-1 max-w-[62ch] text-slate">
        Ohahay names anyone it knows and tells you what they're up to.
      </p>
      <p className="type-record mt-3 text-slate">
        JPG, PNG, BMP, WebP, GIF, MP4, MOV, AVI or WebM — up to 100 MB.
      </p>
    </div>
  );
}
