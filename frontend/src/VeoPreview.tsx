import { useState } from "react";

export type VeoPreviewRecord = {
  source_attempt_id: string;
  video_attempt_id: string;
  shot_id: string;
  model: string;
  fps: number;
  frame_count: number;
  video_sha256: string;
  caption: string;
};

export default function VeoPreview({
  preview,
}: {
  preview: VeoPreviewRecord | undefined;
}) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  if (!preview) return null;

  const url = `/v1/veo/${encodeURIComponent(preview.video_attempt_id)}/video`;
  if (failedUrl === url) {
    return <p role="alert">The saved Veo video could not be loaded.</p>;
  }

  return (
    <figure className="shot-animation">
      <video
        key={url}
        src={url}
        controls
        playsInline
        preload="metadata"
        width={1280}
        height={720}
        style={{ width: "100%", height: "auto", borderRadius: 12 }}
        aria-label={`Veo cinematic preview for ${preview.shot_id}`}
        onError={() => setFailedUrl(url)}
      />
      <figcaption>
        {preview.caption} / {(preview.frame_count / preview.fps).toFixed(1)} seconds
      </figcaption>
    </figure>
  );
}
