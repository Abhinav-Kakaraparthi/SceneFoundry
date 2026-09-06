import { useEffect, useRef, useState } from "react";
import type { VeoPreviewRecord } from "./VeoPreview";
import { veoVideoUrl } from "./videoUrl";

type Props = {
  projectId: string;
  shotIds: string[];
  previews: VeoPreviewRecord[];
};

export default function SceneReel({
  projectId,
  shotIds,
  previews,
}: Props) {
  const video = useRef<HTMLVideoElement>(null);
  const [open, setOpen] = useState(false);
  const [requestedIndex, setRequestedIndex] = useState(0);
  const [continuous, setContinuous] = useState(false);
  const [failedAttempt, setFailedAttempt] = useState<string | null>(null);

  const ordered = shotIds.flatMap((shotId) => {
    const preview = previews.find((item) => item.shot_id === shotId);
    return preview ? [preview] : [];
  });

  const activeIndex = Math.min(
    requestedIndex,
    Math.max(ordered.length - 1, 0),
  );
  const current = ordered[activeIndex];
  const currentAttempt = current?.video_attempt_id;

  useEffect(() => {
    if (!continuous || !currentAttempt) return;

    const playback = video.current?.play();
    playback?.catch(() => setContinuous(false));
  }, [continuous, currentAttempt]);

  if (!current) return null;

  const complete = ordered.length === shotIds.length;
  const duration = ordered.reduce(
    (total, preview) => total + preview.frame_count / preview.fps,
    0,
  );

  function moveTo(index: number) {
    setFailedAttempt(null);
    setRequestedIndex(index);
  }

  function handleEnded() {
    if (activeIndex < ordered.length - 1) {
      setContinuous(true);
      moveTo(activeIndex + 1);
    } else {
      setContinuous(false);
    }
  }

  return (
    <section className="scene-reel" aria-label="Scene review reel">
      <div className="reel-summary">
        <div className="reel-icon" aria-hidden="true">
          <span>▶</span>
        </div>

        <div className="reel-copy">
          <span className="media-kicker">SCENE REVIEW</span>
          <strong>
            {complete ? "Full cinematic sequence" : "Partial cinematic sequence"}
          </strong>
          <small>
            {ordered.length} of {shotIds.length} shots · {duration.toFixed(1)}s
            {" · "}Private streamed media
          </small>
        </div>

        <button
          className="reel-toggle"
          type="button"
          aria-expanded={open}
          aria-controls="scene-reel-player"
          onClick={() => {
            setContinuous(false);
            setOpen((value) => !value);
          }}
        >
          {open ? "Close review" : "Review scene"}
          <span aria-hidden="true">{open ? "×" : "↗"}</span>
        </button>
      </div>

      {open && (
        <div id="scene-reel-player" className="reel-player">
          <header className="reel-player-header">
            <div>
              <span>
                SHOT {String(activeIndex + 1).padStart(2, "0")}
                {" / "}
                {String(ordered.length).padStart(2, "0")}
              </span>
              <strong>{current.shot_id}</strong>
            </div>

            <span className={complete ? "reel-complete" : "reel-partial"}>
              {complete ? "Complete sequence" : "Missing planned shots"}
            </span>
          </header>

          {failedAttempt === current.video_attempt_id ? (
            <div className="reel-error" role="alert">
              <strong>This clip could not be loaded.</strong>
              <span>You can continue to another available shot.</span>
            </div>
          ) : (
            <video
              ref={video}
              key={current.video_attempt_id}
              src={veoVideoUrl(projectId, current)}
              controls
              playsInline
              preload="metadata"
              width={1280}
              height={720}
              aria-label={`Scene review: ${current.shot_id}`}
              onPlay={() => setContinuous(true)}
              onPause={() => setContinuous(false)}
              onEnded={handleEnded}
              onError={() => {
                setContinuous(false);
                setFailedAttempt(current.video_attempt_id);
              }}
            />
          )}

          <footer className="reel-controls">
            <button
              type="button"
              disabled={activeIndex === 0}
              onClick={() => moveTo(activeIndex - 1)}
            >
              ← Previous
            </button>

            <div className="reel-dots" aria-label="Available cinematic shots">
              {ordered.map((preview, index) => (
                <button
                  key={preview.video_attempt_id}
                  type="button"
                  className={index === activeIndex ? "active" : ""}
                  aria-label={`Show ${preview.shot_id}`}
                  aria-current={index === activeIndex ? "true" : undefined}
                  onClick={() => moveTo(index)}
                />
              ))}
            </div>

            <button
              type="button"
              disabled={activeIndex === ordered.length - 1}
              onClick={() => moveTo(activeIndex + 1)}
            >
              Next →
            </button>
          </footer>
        </div>
      )}
    </section>
  );
}