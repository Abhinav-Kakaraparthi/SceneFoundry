import { useEffect, useState } from "react";
import type { VeoPreviewRecord } from "./VeoPreview";
import type { AnimationRecord } from "./ShotAnimation";
import type { PreviewRecord } from "./ShotPreview";
import ProductionSetup from "./ProductionSetup";
import RevisionEditor from "./RevisionEditor";
import RevisionReview from "./RevisionReview";
import ScreenplayWorkspace from "./ScreenplayWorkspace";
import ShotBoard, { type Scene } from "./ShotBoard";
import StudioShell from "./StudioShell";

type Props = {
  projectId: string;
  projectTitle: string;
  initialAttemptId: string | null;
  onHome: () => void;
};

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
  approval: {
    note: string | null;
  } | null;
};

type Workspace =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      revisionId: string;
      revisionState: RevisionStatusRecord["state"];
      reviewNote: string | null;
      scene: Scene;
      budget: Budget;
      veoPreviews: VeoPreviewRecord[];
      previews: PreviewRecord[];
      animations: AnimationRecord[];
    };

const dollars = (micro: number) =>
  `$${(micro / 1_000_000).toFixed(6)}`;

async function readJson<T>(
  path: string,
  signal: AbortSignal,
): Promise<T> {
  const response = await fetch(path, { signal });
  if (!response.ok) {
    throw new Error(
      `Could not load workspace data (HTTP ${response.status}).`,
    );
  }
  return (await response.json()) as T;
}

export default function DirectorWorkspace({
  projectId,
  projectTitle,
  initialAttemptId,
  onHome,
}: Props) {
  const basePath = `/v1/projects/${encodeURIComponent(projectId)}`;
  const [attemptId, setAttemptId] = useState<string | null>(
    initialAttemptId,
  );
  const [workspace, setWorkspace] = useState<Workspace>(
    initialAttemptId
      ? { status: "loading" }
      : { status: "idle" },
  );
  const [revision, setRevision] = useState(0);
  const [researchId, setResearchId] = useState<string | null>(null);

  function selectAttempt(id: string) {
    const url = new URL(window.location.href);
    url.searchParams.set("attempt", id);
    window.history.replaceState(null, "", url);
    setAttemptId(id);
  }

  useEffect(() => {
    if (!attemptId) {
      setWorkspace({ status: "idle" });
      return;
    }

    const controller = new AbortController();
    setWorkspace({ status: "loading" });

    Promise.all([
      readJson<RevisionStatusRecord[]>(
        `${basePath}/attempts/${attemptId}/revisions/status`,
        controller.signal,
      ),
      readJson<VeoPreviewRecord[]>(
        `/v1/veo/projects/${encodeURIComponent(projectId)}` +
          `/attempts/${attemptId}/previews`,
        controller.signal,
      ),
      readJson<Budget>(
        `${basePath}/budget`,
        controller.signal,
      ),
      readJson<PreviewRecord[]>(
        `${basePath}/attempts/${attemptId}/previews`,
        controller.signal,
      ),
      readJson<AnimationRecord[]>(
        `${basePath}/attempts/${attemptId}/animations`,
        controller.signal,
      ),
    ])
      .then(
        ([
          statuses,
          veoPreviews,
          budget,
          previews,
          animations,
        ]) => {
          const selected = [...statuses].sort(
            (left, right) =>
              right.revision.version - left.revision.version,
          )[0];

          if (!selected) {
            throw new Error(
              "This saved scene has not entered revision review yet.",
            );
          }

          if (!controller.signal.aborted) {
            setWorkspace({
              status: "ready",
              revisionId: selected.revision.revision_id,
              revisionState: selected.state,
              reviewNote: selected.approval?.note ?? null,
              scene: selected.revision.scene,
              veoPreviews,
              budget,
              previews,
              animations,
            });
          }
        },
      )
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setWorkspace({
            status: "error",
            message:
              error instanceof Error
                ? error.message
                : "Request failed.",
          });
        }
      });

    return () => controller.abort();
  }, [attemptId, basePath, projectId, revision]);

  return (
    <StudioShell
      projectId={projectId}
      projectTitle={projectTitle}
      attemptId={attemptId}
      onHome={onHome}
    >
      <main id="overview">
        <div className="heading">
          <div>
            <p className="eyebrow">DIRECTOR WORKSPACE</p>
            <h1>{projectTitle}</h1>
          </div>

          {attemptId && (
            <button
              onClick={() =>
                setRevision((value) => value + 1)
              }
              disabled={workspace.status === "loading"}
            >
              {workspace.status === "loading"
                ? "Loading…"
                : "Refresh"}
            </button>
          )}
        </div>

        <ScreenplayWorkspace projectId={projectId} />

        <ProductionSetup
          projectId={projectId}
          selectedResearchId={researchId}
          onSelected={setResearchId}
          onCreated={selectAttempt}
        />

        {workspace.status === "idle" && (
          <div className="notice">
            <h2>No scene plan yet</h2>
            <p>
              Develop the screenplay, gather evidence, and submit
              the scene direction to create the first immutable
              production revision.
            </p>
          </div>
        )}

        {workspace.status === "loading" && (
          <p role="status" className="notice">
            Loading saved production data…
          </p>
        )}

        {workspace.status === "error" && (
          <div role="alert" className="notice error">
            <h2>Workspace unavailable</h2>
            <p>{workspace.message}</p>
            <p>
              Check that the backend is running, then select Refresh.
            </p>
          </div>
        )}

        {workspace.status === "ready" && attemptId && (
          <>
            <section
              id="budget-overview"
              className="metrics"
              aria-label="Project budget"
            >
              {[
                ["Allowance", workspace.budget.allowance_micro_usd],
                [
                  "Calculated spend",
                  workspace.budget.accounted_micro_usd,
                ],
                ["Reserved", workspace.budget.reserved_micro_usd],
                ["Available", workspace.budget.available_micro_usd],
              ].map(([itemLabel, value]) => (
                <div className="metric" key={itemLabel}>
                  <span>{itemLabel}</span>
                  <strong>{dollars(Number(value))}</strong>
                </div>
              ))}
            </section>

            <p className="billing-note">
              Application accounting in USD. Calculated spend is not
              a confirmed cloud invoice.
            </p>

            <RevisionReview
              projectId={projectId}
              attemptId={attemptId}
              revisionId={workspace.revisionId}
              state={workspace.revisionState}
              onUpdated={() =>
                setRevision((value) => value + 1)
              }
            />

            {workspace.revisionState === "changes_requested" && (
              <RevisionEditor
                projectId={projectId}
                attemptId={attemptId}
                parentRevisionId={workspace.revisionId}
                reviewNote={workspace.reviewNote}
                scene={workspace.scene}
                onCreated={() =>
                  setRevision((value) => value + 1)
                }
              />
            )}

            <ShotBoard
              projectId={projectId}
              sourceAttemptId={attemptId}
              revisionId={workspace.revisionId}
              productionLocked={
                workspace.revisionState !== "approved"
              }
              scene={workspace.scene}
              availableMicroUsd={
                workspace.budget.available_micro_usd
              }
              veoPreviews={workspace.veoPreviews}
              animations={workspace.animations}
              previews={workspace.previews}
              onUpdated={() =>
                setRevision((value) => value + 1)
              }
            />

            <footer>
              Saved director output | Available video previews are
              shown per shot.
            </footer>
          </>
        )}
      </main>
    </StudioShell>
  );
}
