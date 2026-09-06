import { useState } from "react";
import GenerateVideo from "./GenerateVideo";
import ShotMedia from "./ShotMedia";
import type { AnimationRecord } from "./ShotAnimation";
import type { PreviewRecord } from "./ShotPreview";
import type { VeoPreviewRecord } from "./VeoPreview";

export type Shot = {
  shot_id: string;
  action: string;
  frames: { start: number; end: number };
};

export type Scene = {
  scene_id: string;
  fps: number;
  shots: Shot[];
};

type Props = {
  projectId: string;
  sourceAttemptId: string;
  scene: Scene;
  availableMicroUsd: number;
  veoPreviews: VeoPreviewRecord[];
  animations: AnimationRecord[];
  previews: PreviewRecord[];
  onUpdated: () => void;
};

type ShotState = {
  key: "final" | "motion" | "layout" | "planned";
  label: string;
};

const seconds = (frames: number, fps: number) =>
  `${(frames / fps).toFixed(1)}s`;

function getState(
  veo: VeoPreviewRecord | undefined,
  animation: AnimationRecord | undefined,
  preview: PreviewRecord | undefined,
): ShotState {
  if (veo) return { key: "final", label: "Cinematic ready" };
  if (animation) return { key: "motion", label: "Motion ready" };
  if (preview) return { key: "layout", label: "Layout ready" };
  return { key: "planned", label: "Direction ready" };
}

export default function ShotBoard({
  projectId,
  sourceAttemptId,
  scene,
  availableMicroUsd,
  veoPreviews,
  animations,
  previews,
  onUpdated,
}: Props) {
  const [selectedShotId, setSelectedShotId] = useState(() => {
    const hash = window.location.hash.slice(1);
    return scene.shots.some((shot) => shot.shot_id === hash)
      ? hash
      : (scene.shots[0]?.shot_id ?? "");
  });

  const records = scene.shots.map((shot, index) => {
    const veo = veoPreviews.find(
      (item) =>
        item.source_attempt_id === sourceAttemptId &&
        item.shot_id === shot.shot_id,
    );
    const animation = animations.find(
      (item) =>
        item.source_attempt_id === sourceAttemptId &&
        item.shot_id === shot.shot_id,
    );
    const preview = previews.find(
      (item) =>
        item.source_attempt_id === sourceAttemptId &&
        item.shot_id === shot.shot_id,
    );

    return {
      shot,
      index,
      veo,
      animation,
      preview,
      state: getState(veo, animation, preview),
      outputCount:
        Number(Boolean(veo)) +
        Number(Boolean(animation)) +
        Number(Boolean(preview)),
    };
  });

  const requestedIndex = records.findIndex(
    (record) => record.shot.shot_id === selectedShotId,
  );
  const selectedIndex = requestedIndex >= 0 ? requestedIndex : 0;
  const current = records[selectedIndex];

  const cinematicCount = records.filter((record) => record.veo).length;
  const totalOutputs = records.reduce(
    (total, record) => total + record.outputCount,
    0,
  );
  const totalFrames = scene.shots.at(-1)?.frames.end ?? 0;
  const completion =
    records.length === 0
      ? 0
      : Math.round((cinematicCount / records.length) * 100);

  function selectShot(shotId: string) {
    const url = new URL(window.location.href);
    url.hash = shotId;
    window.history.replaceState(null, "", url);
    setSelectedShotId(shotId);
  }

  return (
    <section
      className="scene-panel production-board"
      aria-labelledby="scene-title"
    >
      <header className="scene-heading production-heading">
        <div>
          <p className="eyebrow">SAVED SCENE / {scene.scene_id}</p>
          <h2 id="scene-title">Production board</h2>
          <p className="production-subtitle">
            Select a shot to review its direction, status, and outputs.
          </p>
        </div>

        <div className="production-summary" aria-label="Scene summary">
          <span>
            <small>Shots</small>
            <strong>{records.length}</strong>
          </span>
          <span>
            <small>Final</small>
            <strong>
              {cinematicCount}/{records.length}
            </strong>
          </span>
          <span>
            <small>Outputs</small>
            <strong>{totalOutputs}</strong>
          </span>
          <span>
            <small>Runtime</small>
            <strong>{seconds(totalFrames, scene.fps)}</strong>
          </span>
        </div>
      </header>

      <div className="production-progress">
        <div>
          <span>Cinematic completion</span>
          <strong>{completion}%</strong>
        </div>
        <span className="progress-track" aria-hidden="true">
          <span style={{ width: `${completion}%` }} />
        </span>
      </div>

      <div
        className="production-timeline"
        role="tablist"
        aria-label="Scene shots"
      >
        {records.map((record) => {
          const selected = record.index === selectedIndex;

          return (
            <button
              key={record.shot.shot_id}
              id={`timeline-${record.shot.shot_id}`}
              className={`timeline-shot ${record.state.key}`}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls="shot-focus-panel"
              title={`${record.shot.shot_id}: ${record.state.label}`}
              style={{
                flex:
                  record.shot.frames.end - record.shot.frames.start,
              }}
              onClick={() => selectShot(record.shot.shot_id)}
            >
              <span>
                {String(record.index + 1).padStart(2, "0")}
                <i aria-hidden="true" />
              </span>
              <strong>{record.shot.shot_id}</strong>
              <small>{record.state.label}</small>
            </button>
          );
        })}
      </div>

      {current ? (
        <article
          id="shot-focus-panel"
          className="focus-shot"
          data-state={current.state.key}
          role="tabpanel"
          aria-labelledby={`timeline-${current.shot.shot_id}`}
        >
          <header className="focus-shot-header">
            <div className="shot-identity">
              <span className="shot-number">
                {String(current.index + 1).padStart(2, "0")}
              </span>
              <div>
                <h3>{current.shot.shot_id}</h3>
                <span className={`shot-status ${current.state.key}`}>
                  <span />
                  {current.state.label}
                </span>
              </div>
            </div>

            <span className="shot-time">
              {seconds(current.shot.frames.start, scene.fps)}
              {" – "}
              {seconds(current.shot.frames.end, scene.fps)}
            </span>
          </header>

          <div className="focus-shot-content">
            <div className="shot-direction">
              <span className="media-kicker">SHOT DIRECTION</span>
              <p>{current.shot.action}</p>
            </div>

            <div className="shot-specs" aria-label="Shot specifications">
              <span>
                <small>Duration</small>
                <strong>
                  {seconds(
                    current.shot.frames.end -
                      current.shot.frames.start,
                    scene.fps,
                  )}
                </strong>
              </span>
              <span>
                <small>Frames</small>
                <strong>
                  {current.shot.frames.end - current.shot.frames.start}
                </strong>
              </span>
              <span>
                <small>Frame rate</small>
                <strong>{scene.fps} fps</strong>
              </span>
              <span>
                <small>Outputs</small>
                <strong>{current.outputCount}</strong>
              </span>
            </div>

            <GenerateVideo
              key={`${sourceAttemptId}:${current.shot.shot_id}`}
              projectId={projectId}
              sourceAttemptId={sourceAttemptId}
              shotId={current.shot.shot_id}
              frameCount={
                current.shot.frames.end - current.shot.frames.start
              }
              fps={scene.fps}
              availableMicroUsd={availableMicroUsd}
              hasVideo={Boolean(current.veo)}
              onUpdated={onUpdated}
            />

            <ShotMedia
              projectId={projectId}
              shotId={current.shot.shot_id}
              veo={current.veo}
              animation={current.animation}
              preview={current.preview}
            />

            <span className="frame-label">
              SOURCE FRAMES {current.shot.frames.start}–
              {current.shot.frames.end}
              {" · "}END EXCLUSIVE
            </span>
          </div>

          <footer className="focus-navigation">
            <button
              type="button"
              disabled={selectedIndex === 0}
              onClick={() =>
                selectShot(records[selectedIndex - 1]!.shot.shot_id)
              }
            >
              <span aria-hidden="true">←</span>
              Previous shot
            </button>

            <span className="focus-position">
              Shot {selectedIndex + 1} of {records.length}
            </span>

            <button
              type="button"
              disabled={selectedIndex === records.length - 1}
              onClick={() =>
                selectShot(records[selectedIndex + 1]!.shot.shot_id)
              }
            >
              Next shot
              <span aria-hidden="true">→</span>
            </button>
          </footer>
        </article>
      ) : (
        <p className="board-empty">This scene does not contain any shots.</p>
      )}
    </section>
  );
}