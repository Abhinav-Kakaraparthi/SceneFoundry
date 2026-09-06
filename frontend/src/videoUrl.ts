import type { VeoPreviewRecord } from "./VeoPreview";

export function veoVideoUrl(
  projectId: string,
  preview: VeoPreviewRecord,
): string {
  const project = encodeURIComponent(projectId);
  const attempt = encodeURIComponent(preview.video_attempt_id);

  return preview.cloud_video
    ? `/v1/projects/${project}/videos/${attempt}/content`
    : `/v1/veo/${attempt}/video`;
}