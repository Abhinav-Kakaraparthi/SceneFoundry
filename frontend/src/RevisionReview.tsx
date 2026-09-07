import { useState } from "react";
import { authenticatedFetch } from "./authSession";

export type RevisionState =
  | "pending"
  | "approved"
  | "changes_requested";

type Props = {
  projectId: string;
  attemptId: string;
  revisionId: string;
  state: RevisionState;
  onUpdated: () => void;
};

async function errorDetail(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    // Use the HTTP status fallback.
  }

  return `Review request failed (HTTP ${response.status}).`;
}

export default function RevisionReview({
  projectId,
  attemptId,
  revisionId,
  state,
  onUpdated,
}: Props) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function decide(
    decision: "approved" | "changes_requested",
  ) {
    const normalizedNote = note.trim();

    if (
      busy ||
      (decision === "changes_requested" && !normalizedNote)
    ) {
      return;
    }

    setBusy(true);
    setMessage(null);

    try {
      const response = await authenticatedFetch(
        `/v1/projects/${encodeURIComponent(projectId)}` +
          `/attempts/${encodeURIComponent(attemptId)}` +
          `/revisions/${encodeURIComponent(revisionId)}/approval`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            decision,
            note: normalizedNote || null,
          }),
        },
      );

      if (!response.ok) {
        throw new Error(await errorDetail(response));
      }

      setMessage(
        decision === "approved"
          ? "Revision approved. Production is now unlocked."
          : "Changes requested. This revision remains locked.",
      );
      onUpdated();
    } catch (caught: unknown) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "The review decision could not be saved.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (state === "approved") {
    return (
      <section className="revision-review approved">
        <div>
          <span className="review-kicker">DIRECTOR GATE</span>
          <h2>Revision approved</h2>
          <p>
            The signed-in director approved this exact immutable
            SceneSpec. Veo production is unlocked.
          </p>
        </div>
        <span className="review-state">Approved</span>
      </section>
    );
  }

  if (state === "changes_requested") {
    return (
      <section className="revision-review changes">
        <div>
          <span className="review-kicker">DIRECTOR GATE</span>
          <h2>Changes requested</h2>
          <p>
            This immutable revision cannot be produced. Create a new
            child revision addressing the director note.
          </p>
        </div>
        <span className="review-state">Production locked</span>
      </section>
    );
  }

  return (
    <section
      className="revision-review pending"
      aria-labelledby="revision-review-title"
    >
      <div className="review-copy">
        <span className="review-kicker">HUMAN REVIEW REQUIRED</span>
        <h2 id="revision-review-title">Approve the scene plan</h2>
        <p>
          Review every timed shot below. Your verified Google identity
          will be attached to one immutable decision.
        </p>
        <code>{revisionId}</code>
      </div>

      <div className="review-controls">
        <label htmlFor="revision-note">Director note</label>
        <textarea
          id="revision-note"
          value={note}
          maxLength={2000}
          rows={3}
          placeholder="Optional approval note; required when requesting changes."
          disabled={busy}
          onChange={(event) => setNote(event.target.value)}
        />

        <div className="review-actions">
          <button
            type="button"
            className="request-changes"
            disabled={busy || !note.trim()}
            onClick={() => void decide("changes_requested")}
          >
            Request changes
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void decide("approved")}
          >
            {busy ? "Saving decision..." : "Approve revision"}
          </button>
        </div>

        {message && (
          <p role="status" aria-live="polite">
            {message}
          </p>
        )}
      </div>
    </section>
  );
}
