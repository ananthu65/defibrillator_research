import { useState } from "react";

import { ModelSelect } from "./components/ModelSelect";
import { NavigationRail, type NavDestination } from "./components/NavigationRail";
import { RubricSection, type RubricItem } from "./components/RubricSection";
import { SegmentedButton } from "./components/SegmentedButton";
import { StarIcon } from "./components/icons";
import { VideoDropZone } from "./components/VideoDropZone";
import { audioModels, videoModels } from "./data/availableModels";

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
  const [videoModel, setVideoModel] = useState("YOLOv8x");
  const [audioModel, setAudioModel] = useState("Whisper Base");
  const [fileName, setFileName] = useState("P01_cam01.mp4");
  const [mode, setMode] = useState<ReviewMode>("auto");
  const [reviewStarted, setReviewStarted] = useState(false);
  const [audio, setAudio] = useState(initialAudio);
  const [video, setVideo] = useState(initialVideo);
  const [feedback, setFeedback] = useState("");

  const needsModels = mode === "auto";
  const canStart = Boolean(
    fileName && (!needsModels || (videoModel && audioModel)),
  );

  const changeMode = (nextMode: ReviewMode) => {
    setMode(nextMode);
    setReviewStarted(false);
  };

  const changeFile = (nextFileName: string) => {
    setFileName(nextFileName);
    setReviewStarted(false);
  };

  return (
    <div className="app">
      <NavigationRail
        destinations={destinations}
        activeId={activeNav}
        onSelect={setActiveNav}
      />
      <main className="content">
        <div className="camera-views">
          <VideoDropZone fileName={fileName} onFileChange={changeFile} />

          <section className="review-setup" aria-labelledby="review-setup-title">
            <div className="review-setup__heading">
              <div>
                <h2 id="review-setup-title" className="section-title">
                  Review setup
                </h2>
                <p className="review-setup__description">
                  Choose a review method, then start the recording analysis.
                </p>
              </div>
              <SegmentedButton
                label="Review mode"
                options={reviewModes}
                value={mode}
                onChange={changeMode}
              />
            </div>

            <div className="model-selectors" aria-disabled={!needsModels}>
              <ModelSelect
                label="Video model"
                value={videoModel}
                options={videoModels}
                disabled={!needsModels}
                onChange={(value) => {
                  setVideoModel(value);
                  setReviewStarted(false);
                }}
              />
              <ModelSelect
                label="Audio model"
                value={audioModel}
                options={audioModels}
                disabled={!needsModels}
                onChange={(value) => {
                  setAudioModel(value);
                  setReviewStarted(false);
                }}
              />
            </div>

            <div className="review-setup__footer">
              <p className="review-setup__status" aria-live="polite">
                {reviewStarted
                  ? `${mode === "auto" ? "Automated" : "Manual"} review started.`
                  : needsModels
                    ? "Select one available video and audio model."
                    : "Model selection is not required for manual review."}
              </p>
              <button
                type="button"
                className="filled-button start-button"
                disabled={!canStart || reviewStarted}
                onClick={() => setReviewStarted(true)}
              >
                {reviewStarted ? "Review started" : "Start review"}
              </button>
            </div>
          </section>
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
