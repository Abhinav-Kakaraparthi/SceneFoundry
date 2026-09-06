import GenerateVideo from "./GenerateVideo";
import type { VeoPreviewRecord } from "./VeoPreview";
import type { AnimationRecord } from "./ShotAnimation";
import type { PreviewRecord } from "./ShotPreview";
import ShotMedia from "./ShotMedia";
import BriefForm from "./BriefForm";
import StudioShell from "./StudioShell";
import { useEffect, useState } from "react";

type Shot = {
  shot_id: string;
  action: string;
  frames: { start: number; end: number };
};

type Scene = {
  scene_id: string;
  fps: number;
  shots: Shot[];
};

type Budget = {
  allowance_micro_usd: number;
  accounted_micro_usd: number;
  reserved_micro_usd: number;
  available_micro_usd: number;
};

type Workspace =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; scene: Scene; budget: Budget; veoPreviews: VeoPreviewRecord[]; previews: PreviewRecord[]; animations: AnimationRecord[] };

const projectId = "demo_cafe";
const initialAttemptId = "9480269091d94b628b5cf97af3075260";
const basePath = `/v1/projects/${projectId}`;

const dollars = (micro: number) => `$${(micro / 1_000_000).toFixed(6)}`;
const seconds = (frames: number, fps: number) =>
  `${(frames / fps).toFixed(1)}s`;

async function readJson<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });
  if (!response.ok) {
    throw new Error(`Could not load workspace data (HTTP ${response.status}).`);
  }
  return (await response.json()) as T;
}

export default function App() {
  const [attemptId, setAttemptId] = useState(() => {
    const saved = new URL(window.location.href).searchParams.get("attempt");
    return saved && /^[a-f0-9]{32}$/.test(saved) ? saved : initialAttemptId;
  });

  function selectAttempt(id: string) {
    const url = new URL(window.location.href);
    url.searchParams.set("attempt", id);
    window.history.replaceState(null, "", url);
    setAttemptId(id);
  }
  const [workspace, setWorkspace] = useState<Workspace>({ status: "loading" });
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setWorkspace({ status: "loading" });

    Promise.all([
      readJson<Scene>(
        `${basePath}/attempts/${attemptId}/scene`,
        controller.signal,
      ),
      readJson<VeoPreviewRecord[]>(
        `/v1/veo/projects/${projectId}/attempts/${attemptId}/previews`,
        controller.signal,
      ),
      readJson<Budget>(`${basePath}/budget`, controller.signal),
      readJson<PreviewRecord[]>(
        `${basePath}/attempts/${attemptId}/previews`,
        controller.signal,
      ),
      readJson<AnimationRecord[]>(
        `${basePath}/attempts/${attemptId}/animations`,
        controller.signal,
      ),
    ])
      .then(([scene, veoPreviews, budget, previews, animations]) => {
        if (!controller.signal.aborted) {
          setWorkspace({ status: "ready", scene, veoPreviews, budget, previews, animations });
        }
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setWorkspace({
            status: "error",
            message: error instanceof Error ? error.message : "Request failed.",
          });
        }
      });

    return () => controller.abort();
  }, [revision, attemptId]);

  return (
    <StudioShell projectId={projectId} attemptId={attemptId}>
      <main id="overview">
        <div className="heading">
          <div>
            <p className="eyebrow">DIRECTOR WORKSPACE</p>
            <h1>The scene, before the set.</h1>
          </div>
          <button
            onClick={() => setRevision((value) => value + 1)}
            disabled={workspace.status === "loading"}
          >
            {workspace.status === "loading" ? "Loading…" : "Refresh"}
          </button>
        </div>

        <BriefForm projectId={projectId} onCreated={selectAttempt} />

        {workspace.status === "loading" && (
          <p role="status" className="notice">Loading saved production data…</p>
        )}

        {workspace.status === "error" && (
          <div role="alert" className="notice error">
            <h2>Workspace unavailable</h2>
            <p>{workspace.message}</p>
            <p>Check that the local backend is running, then select Refresh.</p>
          </div>
        )}

        {workspace.status === "ready" && (
          <>
            <section id="budget-overview" className="metrics" aria-label="Project budget">
              {[
                ["Allowance", workspace.budget.allowance_micro_usd],
                ["Calculated spend", workspace.budget.accounted_micro_usd],
                ["Reserved", workspace.budget.reserved_micro_usd],
                ["Available", workspace.budget.available_micro_usd],
              ].map(([label, value]) => (
                <div className="metric" key={label}>
                  <span>{label}</span>
                  <strong>{dollars(Number(value))}</strong>
                </div>
              ))}
            </section>
            <p className="billing-note">
              Application accounting in USD. Calculated spend is not a confirmed cloud invoice.
            </p>

            <section className="scene-panel" aria-labelledby="scene-title">
              <div className="scene-heading">
                <div>
                  <p className="eyebrow">SAVED SCENE / {workspace.scene.scene_id}</p>
                  <h2 id="scene-title">Shot sequence</h2>
                </div>
                <span className="scene-meta">
                  {workspace.scene.shots.length} shots · {workspace.scene.fps} fps
                  {" · "}
                  {seconds(
                    workspace.scene.shots.at(-1)?.frames.end ?? 0,
                    workspace.scene.fps,
                  )}
                </span>
              </div>

              <div className="timeline" aria-label="Relative shot durations">
                {workspace.scene.shots.map((shot, index) => (
                  <div
                    key={shot.shot_id}
                    style={{ flex: shot.frames.end - shot.frames.start }}
                    title={`${shot.shot_id}: ${seconds(
                      shot.frames.end - shot.frames.start,
                      workspace.scene.fps,
                    )}`}
                  >
                    {String(index + 1).padStart(2, "0")}
                  </div>
                ))}
              </div>

              <ol className="shots">
                {workspace.scene.shots.map((shot, index) => (
                  <li id={shot.shot_id} key={shot.shot_id}>
                    <span className="shot-number">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <div>
                      <div className="shot-heading">
                        <h3>{shot.shot_id}</h3>
                        <span>
                          {seconds(shot.frames.start, workspace.scene.fps)}
                          {" – "}
                          {seconds(shot.frames.end, workspace.scene.fps)}
                        </span>
                      </div>
                      <p>{shot.action}</p>
                      <GenerateVideo
                        key={`${attemptId}:${shot.shot_id}`}
                        projectId={projectId}
                        sourceAttemptId={attemptId}
                        shotId={shot.shot_id}
                        frameCount={shot.frames.end - shot.frames.start}
                        fps={workspace.scene.fps}
                        availableMicroUsd={workspace.budget.available_micro_usd}
                        hasVideo={workspace.veoPreviews.some(
                          (item) =>
                            item.source_attempt_id === attemptId &&
                            item.shot_id === shot.shot_id,
                        )}
                        onUpdated={() => setRevision((value) => value + 1)}
                      />
                      <ShotMedia
                        projectId={projectId}
                        shotId={shot.shot_id}
                        veo={workspace.veoPreviews.find(
                          (item) =>
                            item.source_attempt_id === attemptId &&
                            item.shot_id === shot.shot_id,
                        )}
                        animation={workspace.animations.find(
                          (item) =>
                            item.source_attempt_id === attemptId &&
                            item.shot_id === shot.shot_id,
                        )}
                        preview={workspace.previews.find(
                          (item) =>
                            item.source_attempt_id === attemptId &&
                            item.shot_id === shot.shot_id,
                        )}
                      />
                      <span className="frame-label">
                        FRAMES {shot.frames.start}–{shot.frames.end} · END EXCLUSIVE
                      </span>
                    </div>
                  </li>
                ))}
              </ol>
            </section>
            <footer>Saved director output | Available video previews are shown per shot.</footer>
          </>
        )}
      </main>
    </StudioShell>
  );
}
