import type { VeoPreviewRecord } from "./VeoPreview";
import type { AnimationRecord } from "./ShotAnimation";
import type { PreviewRecord } from "./ShotPreview";
import BriefForm from "./BriefForm";
import ShotBoard, { type Scene } from "./ShotBoard";
import StudioShell from "./StudioShell";
import ScreenplayWorkspace from "./ScreenplayWorkspace";
import { useEffect, useState } from "react";


type Budget = {
  allowance_micro_usd: number;
  accounted_micro_usd: number;
  reserved_micro_usd: number;
  available_micro_usd: number;
};

type RevisionStatusRecord = {
  revision: {
    revision_id: string;
    version: number;
    scene: Scene;
  };
  state: "pending" | "approved" | "changes_requested";
};

type Workspace =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      revisionId: string;
      scene: Scene;
      budget: Budget;
      veoPreviews: VeoPreviewRecord[];
      previews: PreviewRecord[];
      animations: AnimationRecord[];
    };

const projectId = "demo_cafe";
const initialAttemptId = "9480269091d94b628b5cf97af3075260";
const basePath = `/v1/projects/${projectId}`;

const dollars = (micro: number) => `$${(micro / 1_000_000).toFixed(6)}`;

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
      readJson<RevisionStatusRecord[]>(
        `${basePath}/attempts/${attemptId}/revisions/status`,
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
      .then(([statuses, veoPreviews, budget, previews, animations]) => {
        const approved = statuses
          .filter((item) => item.state === "approved")
          .sort(
            (left, right) =>
              right.revision.version - left.revision.version,
          )[0];

        if (!approved) {
          throw new Error(
            "This scene does not have an approved production revision.",
          );
        }

        if (!controller.signal.aborted) {
          setWorkspace({
            status: "ready",
            revisionId: approved.revision.revision_id,
            scene: approved.revision.scene,
            veoPreviews,
            budget,
            previews,
            animations,
          });
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

        <ScreenplayWorkspace projectId={projectId} />

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

            <ShotBoard
              projectId={projectId}
              sourceAttemptId={attemptId}
              revisionId={workspace.revisionId}
              scene={workspace.scene}
              availableMicroUsd={workspace.budget.available_micro_usd}
              veoPreviews={workspace.veoPreviews}
              animations={workspace.animations}
              previews={workspace.previews}
              onUpdated={() => setRevision((value) => value + 1)}
            />
            <footer>Saved director output | Available video previews are shown per shot.</footer>
          </>
        )}
      </main>
    </StudioShell>
  );
}
