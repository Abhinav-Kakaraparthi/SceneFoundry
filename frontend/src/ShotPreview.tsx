import { useState } from "react";

type Props = {
  sourceAttemptId: string;
  shotId: string;
};

const preview = {
  sourceAttemptId: "9480269091d94b628b5cf97af3075260",
  shotId: "shot_002",
  layoutAttemptId: "a38eea61fc0341398b237a36fc6d01c8",
  revisionId: "c6654546b39c406cb4badb8f9409dc09",
};

export default function ShotPreview({ sourceAttemptId, shotId }: Props) {
  const [failed, setFailed] = useState(false);

  if (
    sourceAttemptId !== preview.sourceAttemptId ||
    shotId !== preview.shotId
  ) {
    return null;
  }

  const imageUrl =
    `/v1/previews/${preview.layoutAttemptId}` +
    `/revisions/${preview.revisionId}/image`;

  return (
    <figure className="shot-preview">
      {failed ? (
        <p role="status">
          Preview unavailable. Check that the backend and local render file are available.
        </p>
      ) : (
        <a href={imageUrl} target="_blank" rel="noreferrer">
          <img
            src={imageUrl}
            alt="Primitive hand and sleeve above a red envelope on a table."
            width={640}
            height={360}
            loading="lazy"
            onError={() => setFailed(true)}
          />
        </a>
      )}
      <figcaption>
        Blocking preview · Manual composition correction · Procedural hand
      </figcaption>
    </figure>
  );
}
