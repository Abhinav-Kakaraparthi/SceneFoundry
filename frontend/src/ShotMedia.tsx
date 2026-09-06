import { useState } from "react";
import ShotAnimation, { type AnimationRecord } from "./ShotAnimation";
import ShotPreview, { type PreviewRecord } from "./ShotPreview";
import VeoPreview, { type VeoPreviewRecord } from "./VeoPreview";

type MediaKey = "veo" | "animation" | "preview";

type Props = {
  projectId: string;
  shotId: string;
  veo: VeoPreviewRecord | undefined;
  animation: AnimationRecord | undefined;
  preview: PreviewRecord | undefined;
};

type MediaTab = {
  key: MediaKey;
  label: string;
  detail: string;
};

export default function ShotMedia({
  projectId,
  shotId,
  veo,
  animation,
  preview,
}: Props) {
  const [requested, setRequested] = useState<MediaKey>("veo");
  const tabs: MediaTab[] = [];

  if (veo) {
    tabs.push({
      key: "veo",
      label: "Cinematic",
      detail: "Veo · 720p · Audio",
    });
  }

  if (animation) {
    tabs.push({
      key: "animation",
      label: "Motion",
      detail: "Blender blocking",
    });
  }

  if (preview) {
    tabs.push({
      key: "preview",
      label: "Layout",
      detail: "Composition still",
    });
  }

  if (tabs.length === 0) return null;

  const firstTab = tabs[0];
  if (!firstTab) return null;

  const active = tabs.some((tab) => tab.key === requested)
    ? requested
    : firstTab.key;

  return (
    <section className="shot-media" aria-label={`Media for ${shotId}`}>
      <header className="media-toolbar">
        <div>
          <span className="media-kicker">SHOT OUTPUT</span>
          <strong>{veo ? "Production render ready" : "Previsualization"}</strong>
        </div>

        <span className={`media-state ${veo ? "ready" : ""}`}>
          <span />
          {veo ? "Final available" : "Blocking only"}
        </span>
      </header>

      <div className="media-tablist" role="tablist" aria-label="Shot media">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            id={`${shotId}-${tab.key}-tab`}
            className="media-tab"
            type="button"
            role="tab"
            aria-selected={active === tab.key}
            aria-controls={`${shotId}-media-panel`}
            onClick={() => setRequested(tab.key)}
          >
            <span>{tab.label}</span>
            <small>{tab.detail}</small>
          </button>
        ))}
      </div>

      <div
        id={`${shotId}-media-panel`}
        className="media-stage"
        role="tabpanel"
        aria-labelledby={`${shotId}-${active}-tab`}
      >
        {active === "veo" && (
          <VeoPreview projectId={projectId} preview={veo} />
        )}
        {active === "animation" && (
          <ShotAnimation animation={animation} />
        )}
        {active === "preview" && <ShotPreview preview={preview} />}
      </div>
    </section>
  );
}