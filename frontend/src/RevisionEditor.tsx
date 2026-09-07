import { useState } from "react";
import { authenticatedFetch } from "./authSession";
import type { Scene } from "./ShotBoard";

type Props = {
  projectId: string;
  attemptId: string;
  parentRevisionId: string;
  reviewNote: string | null;
  scene: Scene;
  onCreated: () => void;
};

type CreateRevisionResponse = {
  created: boolean;
  revision: {
    revision_id: string;
  };
  invalidated_artifacts: string[];
};

async function errorDetail(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") return payload.detail;
  } catch {
    // Use the status fallback.
  }

  return `Revision could not be created (HTTP ${response.status}).`;
}

export default function RevisionEditor({
  projectId,
  attemptId,
  parentRevisionId,
  reviewNote,
  scene,
  onCreated,
}: Props) {
  const [draft, setDraft] = useState<Scene>(scene);
  const [changeNote, setChangeNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const changed = draft.shots.some(
    (shot, index) =>
      shot.action.trim() !== scene.shots[index]?.action,
  );
  const valid =
    changed &&
    Boolean(changeNote.trim()) &&
    draft.shots.every((shot) => Boolean(shot.action.trim()));

  function updateAction(shotId: string, action: string) {
    setDraft((current) => ({
      ...current,
      shots: current.shots.map((shot) =>
        shot.shot_id === shotId ? { ...shot, action } : shot,
      ),
    }));
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !valid) return;

    setBusy(true);
    setMessage(null);

    try {
      const response = await authenticatedFetch(
        `/v1/projects/${encodeURIComponent(projectId)}` +
          `/attempts/${encodeURIComponent(attemptId)}/revisions`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            parent_revision_id: parentRevisionId,
            change_note: changeNote.trim(),
            scene: {
              ...draft,
              shots: draft.shots.map((shot) => ({
                ...shot,
                action: shot.action.trim(),
              })),
            },
          }),
        },
      );

      if (!response.ok) {
        throw new Error(await errorDetail(response));
      }

      const result =
        (await response.json()) as CreateRevisionResponse;

      setMessage(
        `${result.revision.revision_id} created. ` +
          `${result.invalidated_artifacts.length} artifact types invalidated.`,
      );
      onCreated();
    } catch (caught: unknown) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "The child revision could not be created.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="revision-editor"
      aria-labelledby="revision-editor-title"
    >
      <header>
        <div>
          <span className="review-kicker">DIRECTOR CORRECTION</span>
          <h2 id="revision-editor-title">Create a child revision</h2>
          <p>
            Edit only the directions that need correction. Lineage and
            regeneration impact are calculated by the server.
          </p>
        </div>
        <code>{parentRevisionId}</code>
      </header>

      {reviewNote && (
        <div className="revision-request-note">
          <strong>Requested change</strong>
          <p>{reviewNote}</p>
        </div>
      )}

      <form onSubmit={submit}>
        <fieldset disabled={busy}>
          <legend>Shot directions</legend>

          <div className="revision-shot-list">
            {draft.shots.map((shot, index) => (
              <label key={shot.shot_id}>
                <span>
                  {String(index + 1).padStart(2, "0")} / {shot.shot_id}
                </span>
                <textarea
                  value={shot.action}
                  maxLength={2000}
                  rows={3}
                  onChange={(event) =>
                    updateAction(shot.shot_id, event.target.value)
                  }
                />
              </label>
            ))}
          </div>

          <label className="revision-change-note">
            <span>Correction summary</span>
            <input
              value={changeNote}
              maxLength={2000}
              placeholder="Describe how this revision addresses the review."
              onChange={(event) => setChangeNote(event.target.value)}
            />
          </label>

          <div className="revision-editor-actions">
            <span>
              Fresh approval will be required before Veo production.
            </span>
            <button type="submit" disabled={!valid || busy}>
              {busy ? "Creating revision..." : "Create child revision"}
              <span aria-hidden="true">{"\u2192"}</span>
            </button>
          </div>
        </fieldset>

        {message && (
          <p role="status" aria-live="polite">
            {message}
          </p>
        )}
      </form>
    </section>
  );
}
