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
  const cinematicCount = veoPreviews.filter(
    (item) => item.source_attempt_id === sourceAttemptId,
  ).length;

  const totalOutputs =
    veoPreviews.filter(
      (item) => item.source_attempt_id === sourceAttemptId,
    ).length +
    animations.filter(
      (item) => item.source_attempt_id === sourceAttemptId,
    ).length +
    previews.filter(
      (item) => item.source_attempt_id === sourceAttemptId,
    ).length;

  const totalFrames = scene.shots.at(-1)?.frames.end ?? 0;
  const completion =
    scene.shots.length === 0
      ? 0
      : Math.round((cinematicCount / scene.shots.length) * 100);

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
            Review every shot from direction through final cinematic output.
          </p>
        </div>

        <div className="production-summary" aria-label="Scene summary">
          <span>
            <small>Shots</small>
            <strong>{scene.shots.length}</strong>
          </span>
          <span>
            <small>Final</small>
            <strong>
              {cinematicCount}/{scene.shots.length}
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

      <nav className="production-timeline" aria-label="Scene shots">
        {scene.shots.map((shot, index) => {
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
          const state = getState(veo, animation, preview);

          return (
            <a
              key={shot.shot_id}
              className={`timeline-shot ${state.key}`}
              href={`#${shot.shot_id}`}
              style={{ flex: shot.frames.end - shot.frames.start }}
              title={`${shot.shot_id}: ${state.label}`}
            >
              <span>{String(index + 1).padStart(2, "0")}</span>
              <small>{state.label}</small>
            </a>
          );
        })}
      </nav>

      <ol className="shots production-shots">
        {scene.shots.map((shot, index) => {
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
          const state = getState(veo, animation, preview);
          const frameCount = shot.frames.end - shot.frames.start;
          const outputCount =
            Number(Boolean(veo)) +
            Number(Boolean(animation)) +
            Number(Boolean(preview));

          return (
            <li
              id={shot.shot_id}
              className="production-shot"
              data-state={state.key}
              key={shot.shot_id}
            >
              <header className="production-shot-header">
                <div className="shot-identity">
                  <span className="shot-number">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <h3>{shot.shot_id}</h3>
                    <span className={`shot-status ${state.key}`}>
                      <span />
                      {state.label}
                    </span>
                  </div>
                </div>

                <span className="shot-time">
                  {seconds(shot.frames.start, scene.fps)}
                  {" – "}
                  {seconds(shot.frames.end, scene.fps)}
                </span>
              </header>

              <div className="shot-content">
                <p className="shot-action">{shot.action}</p>

                <div className="shot-specs" aria-label="Shot specifications">
                  <span>
                    <small>Duration</small>
                    <strong>{seconds(frameCount, scene.fps)}</strong>
                  </span>
                  <span>
                    <small>Frames</small>
                    <strong>{frameCount}</strong>
                  </span>
                  <span>
                    <small>Frame rate</small>
                    <strong>{scene.fps} fps</strong>
                  </span>
                  <span>
                    <small>Outputs</small>
                    <strong>{outputCount}</strong>
                  </span>
                </div>

                <GenerateVideo
                  key={`${sourceAttemptId}:${shot.shot_id}`}
                  projectId={projectId}
                  sourceAttemptId={sourceAttemptId}
                  shotId={shot.shot_id}
                  frameCount={frameCount}
                  fps={scene.fps}
                  availableMicroUsd={availableMicroUsd}
                  hasVideo={Boolean(veo)}
                  onUpdated={onUpdated}
                />

                <ShotMedia
                  projectId={projectId}
                  shotId={shot.shot_id}
                  veo={veo}
                  animation={animation}
                  preview={preview}
                />

                <span className="frame-label">
                  SOURCE FRAMES {shot.frames.start}–{shot.frames.end}
                  {" · "}END EXCLUSIVE
                </span>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}