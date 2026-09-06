import { useState } from "react";

export type AnimationRecord = {
  source_attempt_id: string;
  layout_attempt_id: string;
  layout_revision_id: string;
  animation_id: string;
  render_id: string;
  shot_id: string;
  fps: number;
  frame_count: number;
  video_sha256: string;
  caption: string;
};

type Props = {
  animation: AnimationRecord | undefined;
};

export default function ShotAnimation({ animation }: Props) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  if (!animation) return null;

  const videoUrl =
    `/v1/previews/animations/${encodeURIComponent(animation.animation_id)}` +
    `/renders/${encodeURIComponent(animation.render_id)}/video`;

  return (
    <figure className="shot-animation">
      {failedUrl === videoUrl ? (
        <p role="status">
          Animation unavailable. Check that the backend and local video are available.
        </p>
      ) : (
        <video
          key={videoUrl}
          controls
          playsInline
          preload="metadata"
          width={640}
          height={360}
          aria-label={`Blocking animation for ${animation.shot_id}`}
          onError={() => setFailedUrl(videoUrl)}
        >
          <source src={videoUrl} type="video/mp4" />
          Your browser does not support this video.
        </video>
      )}
      <figcaption>
        {animation.caption}
        {" / "}
        {(animation.frame_count / animation.fps).toFixed(1)} seconds
      </figcaption>
    </figure>
  );
}
