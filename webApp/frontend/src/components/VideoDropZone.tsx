import { useRef } from "react";

import { AttachFileIcon, StarIcon } from "./icons";

type VideoDropZoneProps = {
  fileName: string;
  onFileChange: (fileName: string) => void;
};

export function VideoDropZone({ fileName, onFileChange }: VideoDropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <div className="drop-zone">
      <AttachFileIcon width={32} height={32} />
      <p className="drop-zone__name">{fileName}</p>
      <p className="drop-zone__hint">Selected automatically from file</p>
      <button
        type="button"
        className="outline-button"
        onClick={() => inputRef.current?.click()}
      >
        <StarIcon width={18} height={18} />
        Choose file
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFileChange(file.name);
        }}
      />
    </div>
  );
}
