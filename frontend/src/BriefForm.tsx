import { useState } from "react";
import type { FormEvent } from "react";

type Props = {
  projectId: string;
  onCreated: (attemptId: string) => void;
};

const examples = [
  {
    label: "Tense exchange",
    prompt:
      "Create a 12-second cinematic scene in a quiet late-night café. A courier places a sealed red envelope on the table, the recipient hesitates, then secretly hides it inside their jacket.",
  },
  {
    label: "Midnight discovery",
    prompt:
      "Create a 12-second suspense scene at an empty railway station. A traveler discovers an old brass key beneath a bench and notices a locked antique suitcase across the platform.",
  },
  {
    label: "Product reveal",
    prompt:
      "Create a polished 12-second studio reveal. Begin in darkness, introduce a sculpted premium device with moving light, then end on a confident centered hero frame.",
  },
];

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
    setMessage("Gemini is directing your shot sequence…");

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
    setMessage("Checking the preserved generation attempt…");

    try {
      const response = await fetch(
        `${basePath}/attempts/${attemptId}/scene`,
      );

      if (response.ok) {
        complete(attemptId);
      } else if (response.status === 409) {
        setMessage(
          "No completed scene is available yet. The attempt may still be running or need inspection.",
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
    <section
      className="scene-panel composer-panel"
      aria-labelledby="brief-title"
    >
      <form onSubmit={submit} className="brief-form">
        <header className="composer-header">
          <div>
            <p className="eyebrow">NEW PRODUCTION</p>
            <h2 id="brief-title">Direct a new scene</h2>
            <p>
              Describe the visible story. SceneFoundry will structure the timing
              and shots.
            </p>
          </div>

          <span className="model-badge">
            <span />
            Gemini Director
          </span>
        </header>

        <div className="composer-body">
          <div className="composer-main">
            <div className="field-heading">
              <label htmlFor="scene-brief">Scene direction</label>
              <span>{brief.length.toLocaleString()} / 4,000</span>
            </div>

            <div className="prompt-suggestions" aria-label="Scene examples">
              {examples.map((example) => (
                <button
                  key={example.label}
                  className="suggestion-chip"
                  type="button"
                  disabled={busy || attemptId !== null}
                  onClick={() => setBrief(example.prompt)}
                >
                  {example.label}
                </button>
              ))}
            </div>

            <div className="composer-input">
              <textarea
                id="scene-brief"
                value={brief}
                onChange={(event) => setBrief(event.target.value)}
                placeholder="Example: In a quiet café, a courier places a sealed red envelope on the table…"
                rows={7}
                maxLength={4000}
                required
                disabled={busy || attemptId !== null}
                aria-describedby="brief-hint brief-budget"
              />
              <span className="input-corner" aria-hidden="true">
                DIRECT
              </span>
            </div>

            <p id="brief-hint" className="composer-hint">
              Include the setting, characters, visible action, mood, and desired
              duration for the strongest result.
            </p>
          </div>

          <aside className="composer-guide" aria-label="Generation workflow">
            <span className="sidebar-label">PRODUCTION FLOW</span>

            <div className="guide-step">
              <span>01</span>
              <div>
                <strong>Direct</strong>
                <small>Gemini converts your brief into timed shots.</small>
              </div>
            </div>

            <div className="guide-step">
              <span>02</span>
              <div>
                <strong>Review</strong>
                <small>Inspect actions, timing, blocking, and layouts.</small>
              </div>
            </div>

            <div className="guide-step">
              <span>03</span>
              <div>
                <strong>Generate</strong>
                <small>Create selected cinematic shots with Veo.</small>
              </div>
            </div>

            <div className="composer-specs">
              <span>
                <small>Director hold</small>
                <strong>$0.05</strong>
              </span>
              <span>
                <small>Output</small>
                <strong>Timed shots</strong>
              </span>
            </div>
          </aside>
        </div>

        <footer className="composer-footer">
          <div>
            <p id="brief-budget" className="billing-note">
              The reservation is released or settled after generation.
            </p>
            {attemptId && (
              <p className="attempt-reference">Attempt: {attemptId}</p>
            )}
            <p role="status" aria-live="polite">
              {message}
            </p>
          </div>

          {attemptId ? (
            <button
              className="composer-button"
              type="button"
              onClick={checkResult}
              disabled={busy}
            >
              {busy ? "Checking…" : "Check saved result"}
              <span aria-hidden="true">↗</span>
            </button>
          ) : (
            <button
              className="composer-button"
              type="submit"
              disabled={busy || !brief.trim()}
            >
              {busy ? "Directing…" : "Build scene plan"}
              <span aria-hidden="true">→</span>
            </button>
          )}
        </footer>
      </form>
    </section>
  );
}