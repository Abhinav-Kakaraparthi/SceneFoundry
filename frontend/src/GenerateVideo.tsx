import { useState } from "react";

type Props = {
  projectId: string;
  sourceAttemptId: string;
  shotId: string;
  frameCount: number;
  fps: number;
  availableMicroUsd: number;
  hasVideo: boolean;
  onUpdated: () => void;
};

async function post(path: string, body?: object): Promise<Record<string, unknown>> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Video request failed (HTTP ${response.status}).`,
    );
  }
  return data as Record<string, unknown>;
}

export default function GenerateVideo(props: Props) {
  const storageKey =
    `scenefoundry:veo:${props.projectId}:${props.sourceAttemptId}:${props.shotId}`;
  const [attemptId, setAttemptId] = useState<string | null>(
    () => localStorage.getItem(storageKey),
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const duration = props.frameCount / props.fps;
  const supported = props.fps === 24 && [4, 6, 8].includes(duration);
  const estimate = duration * 100_000;
  const base = `/v1/veo/projects/${encodeURIComponent(props.projectId)}`;

  async function generate() {
    if (busy || attemptId || props.hasVideo || !supported) return;
    if (props.availableMicroUsd < estimate) return;

    setBusy(true);
    setMessage("");
    try {
      if (localStorage.getItem(storageKey)) {
        setAttemptId(localStorage.getItem(storageKey));
        setMessage("An attempt is already saved. Check its progress.");
        return;
      }
      const id = crypto.randomUUID().replaceAll("-", "");
      localStorage.setItem(storageKey, id);
      setAttemptId(id);

      await post(
        `${base}/attempts/${props.sourceAttemptId}/shots/${props.shotId}/videos`,
        { attempt_id: id },
      );
      setMessage("Submitted. Check progress shortly.");
      props.onUpdated();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Submission could not finish.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function checkProgress() {
    if (busy || !attemptId) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await post(
        `${base}/videos/${encodeURIComponent(attemptId)}/refresh`,
      );
      if (result.status === "succeeded") {
        localStorage.removeItem(storageKey);
        setAttemptId(null);
        props.onUpdated();
      } else if (result.status === "running") {
        setMessage("Veo is still generating. Check again shortly.");
      } else if (result.status === "needs_review") {
        setMessage(
          typeof result.message === "string"
            ? result.message
            : "This attempt needs review. Its ID is preserved.",
        );
      } else {
        throw new Error("Unexpected video status. The attempt ID is preserved.");
      }
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Could not check progress.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (props.hasVideo && !attemptId) return null;
  if (!supported && !attemptId) {
    return <p>Veo generation supports 24 fps shots lasting 4, 6, or 8 seconds.</p>;
  }

  return (
    <div className="video-generation">
      {attemptId ? (
        <>
          <button type="button" disabled={busy} onClick={checkProgress}>
            {busy ? "Working..." : "Check video progress"}
          </button>
          <p><small>Video attempt: {attemptId}</small></p>
        </>
      ) : (
        <>
          <button
            type="button"
            disabled={busy || props.availableMicroUsd < estimate}
            onClick={generate}
          >
            {busy ? "Submitting..." : "Generate video"}
          </button>
          <p>
            Estimated reservation: ${(estimate / 1_000_000).toFixed(2)}.
            Includes audio.
          </p>
          {props.availableMicroUsd < estimate && (
            <p>Insufficient available application budget.</p>
          )}
        </>
      )}
      {message && <p role="status">{message}</p>}
    </div>
  );
}
