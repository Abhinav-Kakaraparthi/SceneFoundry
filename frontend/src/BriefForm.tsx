import { useState } from "react";
import type { FormEvent } from "react";

type Props = {
  projectId: string;
  onCreated: (attemptId: string) => void;
};

export default function BriefForm({ projectId, onCreated }: Props) {
  const storageKey = `scenefoundry:pending:${projectId}`;
  const [brief, setBrief] = useState("");
  const [attemptId, setAttemptId] = useState<string | null>(() => {
    try {
      return sessionStorage.getItem(storageKey);
    } catch {
      return null;
    }
  });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const basePath = `/v1/projects/${encodeURIComponent(projectId)}`;

  function complete(id: string) {
    sessionStorage.removeItem(storageKey);
    setAttemptId(null);
    setMessage("Scene saved. Loading the production workspace…");
    onCreated(id);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = brief.trim();
    if (busy || attemptId || !text || text.length > 4000) return;

    setBusy(true);
    setMessage("Generating your scene…");

    try {
      const id = crypto.randomUUID().replaceAll("-", "");
      sessionStorage.setItem(storageKey, id);
      setAttemptId(id);

      const response = await fetch(`${basePath}/attempts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ attempt_id: id, brief: text }),
      });

      if (!response.ok) {
        throw new Error(
          `Submission returned HTTP ${response.status}. Check the saved result before taking further action.`,
        );
      }

      complete(id);
    } catch (error: unknown) {
      setMessage(
        error instanceof Error ? error.message : "Submission did not complete.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function checkResult() {
    if (busy || !attemptId) return;
    setBusy(true);
    setMessage("Checking the saved attempt…");

    try {
      const response = await fetch(
        `${basePath}/attempts/${attemptId}/scene`,
      );

      if (response.ok) {
        complete(attemptId);
      } else if (response.status === 409) {
        setMessage(
          "No completed scene is available yet. The attempt may be running or need inspection.",
        );
      } else if (response.status === 404) {
        setMessage(
          "The attempt was not found. Keep its ID so we can investigate before submitting again.",
        );
      } else {
        throw new Error(`Could not check the result (HTTP ${response.status}).`);
      }
    } catch (error: unknown) {
      setMessage(
        error instanceof Error ? error.message : "Could not check the result.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="scene-panel" aria-labelledby="brief-title">
      <form onSubmit={submit} className="brief-form">
        <h2 id="brief-title">Direct a new scene</h2>
        <label htmlFor="scene-brief">Scene brief</label>
        <textarea
          id="scene-brief"
          value={brief}
          onChange={(event) => setBrief(event.target.value)}
          placeholder="Describe the characters, visible action, and duration."
          rows={5}
          maxLength={4000}
          required
          disabled={busy || attemptId !== null}
          aria-describedby="brief-budget"
        />
        <p id="brief-budget" className="billing-note">
          Reserves $0.05 from this project's application budget.
          Actual calculated usage is recorded after generation.
        </p>

        {attemptId ? (
          <>
            <p className="attempt-reference">Attempt: {attemptId}</p>
            <button type="button" onClick={checkResult} disabled={busy}>
              {busy ? "Working…" : "Check saved result"}
            </button>
          </>
        ) : (
          <button type="submit" disabled={busy || !brief.trim()}>
            {busy ? "Working…" : "Generate scene"}
          </button>
        )}

        <p role="status" aria-live="polite">{message}</p>
      </form>
    </section>
  );
}
