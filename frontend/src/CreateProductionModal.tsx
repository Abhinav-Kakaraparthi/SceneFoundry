import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";
import {
  createProduction,
  genreOptions,
  newCreationId,
  styleOptions,
  type AspectRatio,
  type CreateProductionInput,
  type ProductionProject,
  type ProjectGenre,
  type VisualStyle,
} from "./productionCatalog";

type Props = {
  open: boolean;
  onClose: () => void;
  onCreated: (
    project: ProductionProject,
    created: boolean,
  ) => void;
};

type Draft = Omit<CreateProductionInput, "budget_cents"> & {
  budget_dollars: string;
};

function createDraft(): Draft {
  return {
    creation_id: newCreationId(),
    title: "",
    premise: "",
    genre: "drama",
    visual_style: "cinematic_realism",
    aspect_ratio: "16:9",
    episode_count: 1,
    seconds_per_episode: 12,
    budget_dollars: "3.00",
  };
}

function budgetCents(value: string): number | null {
  const normalized = value.trim();
  if (!/^\d{1,4}(?:\.\d{1,2})?$/.test(normalized)) {
    return null;
  }

  const [dollars, fraction = ""] = normalized.split(".");
  const cents =
    Number(dollars) * 100 +
    Number(fraction.padEnd(2, "0"));

  return cents <= 100_000 ? cents : null;
}

export default function CreateProductionModal({
  open,
  onClose,
  onCreated,
}: Props) {
  const titleInput = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState<Draft>(createDraft);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const focusTimer = window.setTimeout(
      () => titleInput.current?.focus(),
      0,
    );

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !saving) {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.clearTimeout(focusTimer);
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [onClose, open, saving]);

  const parsedBudget = useMemo(
    () => budgetCents(draft.budget_dollars),
    [draft.budget_dollars],
  );

  const valid =
    draft.title.trim().length > 0 &&
    draft.premise.trim().length > 0 &&
    parsedBudget !== null;

  function update<K extends keyof Draft>(
    field: K,
    value: Draft[K],
  ) {
    setDraft((current) => ({
      ...current,
      [field]: value,
    }));
    setError(null);
  }

  function requestClose() {
    if (!saving) onClose();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!valid || saving || parsedBudget === null) return;

    setSaving(true);
    setError(null);

    try {
      const result = await createProduction({
        creation_id: draft.creation_id,
        title: draft.title.trim(),
        premise: draft.premise.trim(),
        genre: draft.genre,
        visual_style: draft.visual_style,
        aspect_ratio: draft.aspect_ratio,
        episode_count: draft.episode_count,
        seconds_per_episode: draft.seconds_per_episode,
        budget_cents: parsedBudget,
      });

      setDraft(createDraft());
      onCreated(result.project, result.created);
    } catch (caught: unknown) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The production could not be created.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (!open) return null;

  return (
    <div
      className="catalog-modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          requestClose();
        }
      }}
    >
      <section
        className="catalog-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-production-title"
      >
        <header className="catalog-modal-header">
          <div>
            <p className="eyebrow">NEW PRODUCTION</p>
            <h2 id="create-production-title">
              Create your next story
            </h2>
            <p>
              Establish the creative boundaries that guide research,
              direction, and every generated shot.
            </p>
          </div>

          <button
            className="catalog-modal-close"
            type="button"
            onClick={requestClose}
            disabled={saving}
            aria-label="Close production setup"
          >
            ×
          </button>
        </header>

        <form className="catalog-form" onSubmit={submit}>
          <div className="catalog-form-section">
            <div className="catalog-section-heading">
              <span>01</span>
              <div>
                <strong>Production identity</strong>
                <small>Name the production and define its premise.</small>
              </div>
            </div>

            <label className="catalog-field">
              <span>
                Title
                <small>{draft.title.length} / 120</small>
              </span>
              <input
                ref={titleInput}
                value={draft.title}
                onChange={(event) =>
                  update("title", event.target.value)
                }
                maxLength={120}
                placeholder="Untitled production"
                required
              />
            </label>

            <label className="catalog-field">
              <span>
                Premise
                <small>{draft.premise.length} / 4,000</small>
              </span>
              <textarea
                value={draft.premise}
                onChange={(event) =>
                  update("premise", event.target.value)
                }
                maxLength={4000}
                placeholder="Describe the story, characters, conflict, and visible action."
                required
              />
            </label>
          </div>

          <div className="catalog-form-section">
            <div className="catalog-section-heading">
              <span>02</span>
              <div>
                <strong>Genre</strong>
                <small>Set the narrative language of the production.</small>
              </div>
            </div>

            <fieldset className="catalog-choice-grid">
              <legend className="sr-only">Production genre</legend>
              {genreOptions.map((option) => (
                <label
                  className={
                    draft.genre === option.value
                      ? "catalog-choice active"
                      : "catalog-choice"
                  }
                  key={option.value}
                >
                  <input
                    type="radio"
                    name="genre"
                    value={option.value}
                    checked={draft.genre === option.value}
                    onChange={() =>
                      update(
                        "genre",
                        option.value as ProjectGenre,
                      )
                    }
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </fieldset>
          </div>

          <div className="catalog-form-section">
            <div className="catalog-section-heading">
              <span>03</span>
              <div>
                <strong>Visual direction</strong>
                <small>
                  This direction propagates into Gemini and Veo prompts.
                </small>
              </div>
            </div>

            <fieldset className="catalog-style-grid">
              <legend className="sr-only">Visual direction</legend>
              {styleOptions.map((option) => (
                <label
                  className={
                    draft.visual_style === option.value
                      ? "catalog-style active"
                      : "catalog-style"
                  }
                  key={option.value}
                >
                  <input
                    type="radio"
                    name="visual-style"
                    value={option.value}
                    checked={draft.visual_style === option.value}
                    onChange={() =>
                      update(
                        "visual_style",
                        option.value as VisualStyle,
                      )
                    }
                  />
                  <span
                    className="catalog-style-swatch"
                    data-style={option.value}
                    aria-hidden="true"
                  />
                  <span className="catalog-style-copy">
                    <strong>{option.label}</strong>
                    <small>{option.description}</small>
                  </span>
                  <i aria-hidden="true" />
                </label>
              ))}
            </fieldset>
          </div>

          <div className="catalog-form-section">
            <div className="catalog-section-heading">
              <span>04</span>
              <div>
                <strong>Production format</strong>
                <small>Choose the canvas, runtime, and budget ceiling.</small>
              </div>
            </div>

            <div className="catalog-production-controls">
              <fieldset className="catalog-format-options">
                <legend>Frame</legend>
                {(["9:16", "16:9"] as AspectRatio[]).map(
                  (ratio) => (
                    <label
                      className={
                        draft.aspect_ratio === ratio
                          ? "catalog-format active"
                          : "catalog-format"
                      }
                      key={ratio}
                    >
                      <input
                        type="radio"
                        name="aspect-ratio"
                        value={ratio}
                        checked={draft.aspect_ratio === ratio}
                        onChange={() =>
                          update("aspect_ratio", ratio)
                        }
                      />
                      <span
                        className={
                          ratio === "9:16"
                            ? "format-frame portrait"
                            : "format-frame landscape"
                        }
                        aria-hidden="true"
                      />
                      <span>
                        <strong>{ratio}</strong>
                        <small>
                          {ratio === "9:16"
                            ? "Vertical"
                            : "Widescreen"}
                        </small>
                      </span>
                    </label>
                  ),
                )}
              </fieldset>

              <label className="catalog-field compact">
                <span>Episodes</span>
                <input
                  type="number"
                  min={1}
                  max={12}
                  value={draft.episode_count}
                  onChange={(event) =>
                    update(
                      "episode_count",
                      Number(event.target.value),
                    )
                  }
                  required
                />
              </label>

              <label className="catalog-field compact">
                <span>Seconds per episode</span>
                <input
                  type="number"
                  min={4}
                  max={120}
                  value={draft.seconds_per_episode}
                  onChange={(event) =>
                    update(
                      "seconds_per_episode",
                      Number(event.target.value),
                    )
                  }
                  required
                />
              </label>

              <label className="catalog-field compact">
                <span>Budget limit</span>
                <div className="catalog-money-input">
                  <span>$</span>
                  <input
                    inputMode="decimal"
                    value={draft.budget_dollars}
                    onChange={(event) =>
                      update(
                        "budget_dollars",
                        event.target.value,
                      )
                    }
                    aria-invalid={parsedBudget === null}
                    placeholder="3.00"
                    required
                  />
                </div>
              </label>
            </div>
          </div>

          {error && (
            <p className="catalog-form-error" role="alert">
              {error}
            </p>
          )}

          <footer className="catalog-form-footer">
            <div>
              <strong>Accountable by design</strong>
              <span>
                Verified owner · Immutable creation · Budget initialized
              </span>
            </div>

            <div className="catalog-form-actions">
              <button
                className="catalog-secondary-button"
                type="button"
                onClick={requestClose}
                disabled={saving}
              >
                Cancel
              </button>
              <button
                className="catalog-primary-button"
                type="submit"
                disabled={!valid || saving}
              >
                {saving ? "Creating production…" : "Create production"}
                <span aria-hidden="true">→</span>
              </button>
            </div>
          </footer>
        </form>
      </section>
    </div>
  );
}
