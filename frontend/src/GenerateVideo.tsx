import { useEffect, useRef, useState } from "react";
import { authenticatedFetch } from "./authSession";

type Props = {
  projectId: string;
  sourceAttemptId: string;
  revisionId: string;
  shotId: string;
  frameCount: number;
  fps: number;
  availableMicroUsd: number;
  hasVideo: boolean;
  locked: boolean;
  onUpdated: () => void;
};

async function post(path: string, body?: object): Promise<Record<string, unknown>> {
  const response = await authenticatedFetch(path, {
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
    `scenefoundry:veo:${props.projectId}:${props.sourceAttemptId}:` +
    `${props.revisionId}:${props.shotId}`;
  const [attemptId, setAttemptId] = useState<string | null>(
    () => localStorage.getItem(storageKey),
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [autoChecking, setAutoChecking] = useState(true);
  const automaticChecks = useRef(0);
  const checking = useRef(false);
  const duration = props.frameCount / props.fps;
  const supported = props.fps === 24 && [4, 6, 8].includes(duration);
  const estimate = duration * 100_000;
  const base = `/v1/veo/projects/${encodeURIComponent(props.projectId)}`;

  async function generate() {
    if (
      busy ||
      attemptId ||
      props.hasVideo ||
      props.locked ||
      !supported
    ) return;
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
        {
          attempt_id: id,
          revision_id: props.revisionId,
        },
      );
      setMessage("Submitted. Check progress shortly.");
      props.onUpdated();
    } catch (error) {
      setAutoChecking(false);
      setMessage(
        error instanceof Error ? error.message : "Submission could not finish.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function checkProgress() {
    if (busy || checking.current || !attemptId) return;
    checking.current = true;
    setBusy(true);
    setMessage("");
    try {
      const result = await post(
        `${base}/videos/${encodeURIComponent(attemptId)}/refresh`,
      );
      if (result.status === "succeeded") {
        setAutoChecking(false);
        localStorage.removeItem(storageKey);
        setAttemptId(null);
        props.onUpdated();
      } else if (result.status === "running") {
        setMessage("Veo is still generating.");
      } else if (result.status === "needs_review") {
        setAutoChecking(false);
        setMessage(
          typeof result.message === "string"
            ? result.message
            : "This attempt needs review. Its ID is preserved.",
        );
      } else {
        throw new Error("Unexpected video status. The attempt ID is preserved.");
      }
    } catch (error) {
      setAutoChecking(false);
      setMessage(
        error instanceof Error ? error.message : "Could not check progress.",
      );
    } finally {
      checking.current = false;
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!attemptId || busy || !autoChecking) return;
    if (automaticChecks.current >= 15) {
      setAutoChecking(false);
      setMessage("Automatic checks paused. You can check progress manually.");
      return;
    }
    const timer = window.setTimeout(() => {
      automaticChecks.current += 1;
      void checkProgress();
    }, 20_000);
    return () => window.clearTimeout(timer);
  }, [attemptId, busy, autoChecking, checkProgress]);

  if (props.hasVideo && !attemptId) return null;
  if (props.locked && !attemptId) {
    return (
      <div className="video-generation locked">
        <strong>Production locked</strong>
        <p>
          The signed-in director must approve this exact revision
          before Veo can be requested.
        </p>
      </div>
    );
  }
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
          {autoChecking && (
            <p role="status">Progress updates automatically every 20 seconds.</p>
          )}
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
