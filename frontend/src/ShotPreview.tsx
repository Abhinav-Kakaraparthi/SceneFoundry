import { useState } from "react";

export type PreviewRecord = {
  source_attempt_id: string;
  layout_attempt_id: string;
  revision_id: string;
  shot_id: string;
  caption: string;
  image_sha256: string;
  layout_sha256: string;
};

type Props = {
  preview: PreviewRecord | undefined;
};

export default function ShotPreview({ preview }: Props) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  if (!preview) return null;

  const imageUrl =
    `/v1/previews/${encodeURIComponent(preview.layout_attempt_id)}` +
    `/revisions/${encodeURIComponent(preview.revision_id)}/image`;

  return (
    <figure className="shot-preview">
      {failedUrl === imageUrl ? (
        <p role="status">
          Preview unavailable. Check that the backend and local render file are available.
        </p>
      ) : (
        <a href={imageUrl} target="_blank" rel="noreferrer">
          <img
            src={imageUrl}
            alt={`Blocking preview for ${preview.shot_id}`}
            width={640}
            height={360}
            loading="lazy"
            onError={() => setFailedUrl(imageUrl)}
          />
        </a>
      )}
      <figcaption>{preview.caption}</figcaption>
    </figure>
  );
}
