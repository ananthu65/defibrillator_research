import { useState } from "react";

import { NavigationRail, type NavDestination } from "./components/NavigationRail";
import { RubricSection, type RubricItem } from "./components/RubricSection";
import { SegmentedButton } from "./components/SegmentedButton";
import { StarIcon } from "./components/icons";
import { TextField } from "./components/TextField";
import { VideoDropZone } from "./components/VideoDropZone";

const destinations: NavDestination[] = [
  { id: "review", label: "Review" },
  { id: "compare", label: "Compare models" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

const reviewModes = [
  { value: "auto", label: "Auto Review" },
  { value: "manual", label: "Manual Review" },
] as const;

type ReviewMode = (typeof reviewModes)[number]["value"];

const initialAudio: RubricItem[] = [
  { id: "1.1", label: "1.1  Free flow O₂ away", checked: true },
  { id: "1.2", label: "1.2  Continue chest compressions", checked: true },
  { id: "1.3", label: "1.3  All stand clear", checked: true },
  { id: "1.4", label: "1.4  Stop chest compressions", checked: true },
  { id: "1.5", label: "1.5  Apply gel / pads", checked: false },
  { id: "1.6", label: "1.6  DC shock / discharge", checked: true },
  { id: "1.7", label: "1.7  Start chest compressions", checked: false, flagged: true },
];

const initialVideo: RubricItem[] = [
  { id: "2.1", label: "2.1  Takes one paddle at a time", checked: true },
  { id: "2.2", label: "2.2  Places paddles firmly on chest", checked: true },
  { id: "2.3", label: "2.3  Presses both paddles simultaneously", checked: true },
  { id: "2.4", label: "2.4  Removes paddles after shock", checked: true },
  { id: "2.5", label: "2.5  Resumes chest compressions promptly", checked: false, flagged: true },
];

const toggleItem = (items: RubricItem[], id: string) =>
  items.map((item) => (item.id === id ? { ...item, checked: !item.checked } : item));

export default function App() {
  const [activeNav, setActiveNav] = useState("review");
  const [participant, setParticipant] = useState("P01");
  const [videoModel, setVideoModel] = useState("YOLOv8x");
  const [audioModel, setAudioModel] = useState("Whisper Base");
  const [fileName, setFileName] = useState("P01_cam01.mp4");
  const [mode, setMode] = useState<ReviewMode>("auto");
  const [audio, setAudio] = useState(initialAudio);
  const [video, setVideo] = useState(initialVideo);
  const [feedback, setFeedback] = useState("");

  return (
    <div className="app">
      <NavigationRail
        destinations={destinations}
        activeId={activeNav}
        onSelect={setActiveNav}
      />
      <main className="content">
        <div className="selectors">
          <TextField label="Participant" value={participant} onChange={setParticipant} />
          <TextField label="Video model" value={videoModel} onChange={setVideoModel} />
          <TextField label="Audio model" value={audioModel} onChange={setAudioModel} />
        </div>

        <div className="camera-views">
          <VideoDropZone fileName={fileName} onFileChange={setFileName} />
          <SegmentedButton
            label="Review mode"
            options={reviewModes}
            value={mode}
            onChange={setMode}
          />
        </div>

        <div className="rubric-grid">
          <RubricSection
            title="1. Audio Component"
            items={audio}
            onToggle={(id) => setAudio((items) => toggleItem(items, id))}
          />
          <RubricSection
            title="2. Video Component"
            items={video}
            onToggle={(id) => setVideo((items) => toggleItem(items, id))}
          />
        </div>

        <section className="narrative">
          <h2 className="section-title">3. Narrative Feedback (50–75 words)</h2>
          <textarea
            className="narrative__input"
            placeholder="Add constructive, step-specific feedback for the learner…"
            value={feedback}
            onChange={(event) => setFeedback(event.target.value)}
          />
        </section>

        <div className="actions">
          <button type="button" className="filled-button">
            <StarIcon width={18} height={18} />
            Submit &amp; Save Review
          </button>
        </div>
      </main>
    </div>
  );
}
