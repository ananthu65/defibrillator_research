import type { ModelOption } from "../components/ModelSelect";

// Temporary frontend catalog. FastAPI will replace this source with the
// available-model response from PostgreSQL without changing the selectors.
export const videoModels: readonly ModelOption[] = [
  { value: "YOLOv8n", label: "YOLOv8 Nano" },
  { value: "YOLOv8s", label: "YOLOv8 Small" },
  { value: "YOLOv8m", label: "YOLOv8 Medium" },
  { value: "YOLOv8x", label: "YOLOv8 Extra Large" },
  { value: "Faster R-CNN", label: "Faster R-CNN" },
  { value: "RT-DETR", label: "RT-DETR" },
] as const;

export const audioModels: readonly ModelOption[] = [
  { value: "Whisper Small", label: "Whisper Small" },
  { value: "Whisper Base", label: "Whisper Base" },
] as const;
