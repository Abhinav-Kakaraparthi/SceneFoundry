import { useEffect, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";

type ScreenplayFormat = "fountain" | "plain_text";

type ScreenplayVersion = {
  screenplay_id: string;
  version_id: string;
  version: number;
  parent_version_id: string | null;
  source: "imported" | "generated" | "edited";
  screenplay: {
    title: string;
    format: ScreenplayFormat;
    content: string;
  };
  content_sha256: string;
  created_by: string;
  change_note: string | null;
};

type Props = {
  projectId: string;
};

type LoadState =
  | { status: "loading" }
  | { status: "ready" }
  | { status: "error"; message: string };

const screenplayId = "screenplay_001";

async function errorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload.detail) return payload.detail;
  } catch {
    // The HTTP status remains the authoritative fallback.
  }
  return `Request failed with HTTP ${response.status}.`;
}

export default function ScreenplayWorkspace({ projectId }: Props) {
  const basePath =
    `/v1/projects/${encodeURIComponent(projectId)}` +
    `/screenplays/${screenplayId}/versions`;

  const [versions, setVersions] = useState<ScreenplayVersion[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [format, setFormat] = useState<ScreenplayFormat>("fountain");
  const [content, setContent] = useState("");
  const [changeNote, setChangeNote] = useState("");
  const [loadState, setLoadState] = useState<LoadState>({
    status: "loading",
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  function applyVersion(version: ScreenplayVersion) {
    setSelectedId(version.version_id);
    setTitle(version.screenplay.title);
    setFormat(version.screenplay.format);
    setContent(version.screenplay.content);
    setChangeNote("");
  }

  useEffect(() => {
    const controller = new AbortController();

    fetch(basePath, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(await errorMessage(response));
        }
        return (await response.json()) as ScreenplayVersion[];
      })
      .then((history) => {
        if (controller.signal.aborted) return;

        const ordered = [...history].sort(
          (left, right) => left.version - right.version,
        );
        setVersions(ordered);

        const latest = ordered.at(-1);
        if (latest) applyVersion(latest);

        setLoadState({ status: "ready" });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setLoadState({
          status: "error",
          message:
            error instanceof Error
              ? error.message
              : "Could not load screenplay history.",
        });
      });

    return () => controller.abort();
  }, [basePath]);

  const latest = versions.at(-1) ?? null;
  const selected =
    versions.find((version) => version.version_id === selectedId) ??
    latest;
  const editable =
    latest === null || selected?.version_id === latest.version_id;

  async function importFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    if (file.size > 500_000) {
      setMessage("Screenplay files must be 500 KB or smaller.");
      return;
    }

    const imported = await file.text();
    if (!imported.trim()) {
      setMessage("The selected screenplay file is empty.");
      return;
    }

    if (latest) setSelectedId(latest.version_id);

    const fileTitle = file.name
      .replace(/\.(fountain|txt)$/i, "")
      .replace(/[-_]+/g, " ")
      .trim();

    setTitle(fileTitle || "Untitled Screenplay");
    setFormat(
      file.name.toLowerCase().endsWith(".fountain")
        ? "fountain"
        : "plain_text",
    );
    setContent(imported);
    setChangeNote(
      latest
        ? `Imported ${file.name} as a new screenplay version.`
        : "",
    );
    setMessage(`${file.name} loaded locally. Review before saving.`);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || !editable) return;

    const cleanTitle = title.trim();
    const cleanContent = content.trim();
    const cleanNote = changeNote.trim();

    if (!cleanTitle || !cleanContent) {
      setMessage("A title and screenplay content are required.");
      return;
    }
    if (latest && !cleanNote) {
      setMessage("Describe what changed before saving a new version.");
      return;
    }

    setSaving(true);
    setMessage(
      latest
        ? "Saving an immutable screenplay version?"
        : "Importing the initial screenplay?",
    );

    try {
      const response = await fetch(basePath, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          parent_version_id: latest?.version_id ?? null,
          title: cleanTitle,
          format,
          content: cleanContent,
          change_note: latest ? cleanNote : null,
        }),
      });

      if (!response.ok) {
        throw new Error(await errorMessage(response));
      }

      const result = (await response.json()) as {
        created: boolean;
        version: ScreenplayVersion;
      };

      const nextHistory = [
        ...versions.filter(
          (item) => item.version_id !== result.version.version_id,
        ),
        result.version,
      ].sort((left, right) => left.version - right.version);

      setVersions(nextHistory);
      applyVersion(result.version);
      setMessage(
        result.created
          ? `Version ${result.version.version} saved.`
          : `Version ${result.version.version} was already safely stored.`,
      );
    } catch (error: unknown) {
      setMessage(
        error instanceof Error
          ? error.message
          : "The screenplay could not be saved.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (loadState.status === "loading") {
    return (
      <section id="develop" className="develop-panel">
        <p role="status" className="notice">
          Loading screenplay workspace?
        </p>
      </section>
    );
  }

  if (loadState.status === "error") {
    return (
      <section id="develop" className="develop-panel">
        <div role="alert" className="notice error">
          <h2>Develop workspace unavailable</h2>
          <p>{loadState.message}</p>
        </div>
      </section>
    );
  }

  return (
    <section
      id="develop"
      className="scene-panel develop-panel"
      aria-labelledby="develop-title"
    >
      <header className="develop-header">
        <div>
          <p className="eyebrow">DEVELOP</p>
          <h2 id="develop-title">Screenplay workspace</h2>
          <p>
            Import, review, and version the written source before scene
            planning.
          </p>
        </div>

        <div className="develop-header-actions">
          <span className="model-badge">
            <span />
            Immutable history
          </span>
          <label className="file-button">
            Import file
            <input
              type="file"
              accept=".fountain,.txt,text/plain"
              onChange={importFile}
              disabled={saving}
            />
          </label>
        </div>
      </header>

      <div className="develop-layout">
        <aside className="version-rail" aria-label="Screenplay versions">
          <div className="version-rail-heading">
            <span className="sidebar-label">VERSION HISTORY</span>
            <strong>{versions.length}</strong>
          </div>

          {versions.length === 0 ? (
            <p className="empty-history">
              Import a Fountain or text screenplay to create version one.
            </p>
          ) : (
            versions
              .slice()
              .reverse()
              .map((version) => (
                <button
                  type="button"
                  className={
                    version.version_id === selected?.version_id
                      ? "version-card active"
                      : "version-card"
                  }
                  key={version.version_id}
                  onClick={() => applyVersion(version)}
                >
                  <span>V{String(version.version).padStart(2, "0")}</span>
                  <strong>{version.screenplay.title}</strong>
                  <small>
                    {version.source} {"\u00b7"} {version.content_sha256.slice(0, 8)}
                  </small>
                </button>
              ))
          )}
        </aside>

        <form className="screenplay-editor" onSubmit={save}>
          <div className="screenplay-toolbar">
            <div>
              <span className="sidebar-label">SCREENPLAY DOCUMENT</span>
              <strong>
                {selected
                  ? selected.version_id
                  : "New screenplay"}
              </strong>
            </div>
            <span className={editable ? "edit-state" : "edit-state locked"}>
              {editable ? "Latest \u00b7 Editable" : "History \u00b7 Read only"}
            </span>
          </div>

          <div className="screenplay-fields">
            <label>
              <span>Title</span>
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={200}
                readOnly={!editable}
                required
              />
            </label>

            <label>
              <span>Format</span>
              <select
                value={format}
                onChange={(event) =>
                  setFormat(event.target.value as ScreenplayFormat)
                }
                disabled={!editable}
              >
                <option value="fountain">Fountain</option>
                <option value="plain_text">Plain text</option>
              </select>
            </label>
          </div>

          <div className="screenplay-page">
            <textarea
              aria-label="Screenplay content"
              value={content}
              onChange={(event) => setContent(event.target.value)}
              maxLength={500_000}
              readOnly={!editable}
              spellCheck
              required
            />
          </div>

          {latest && editable && (
            <label className="change-note">
              <span>Version note</span>
              <input
                value={changeNote}
                onChange={(event) => setChangeNote(event.target.value)}
                maxLength={2000}
                placeholder="Describe the creative change in this version."
                required
              />
            </label>
          )}

          <footer className="develop-footer">
            <div>
              <span>
                {content.length.toLocaleString()} characters
              </span>
              {selected && (
                <span>
                  SHA {selected.content_sha256.slice(0, 12)}
                </span>
              )}
              <p role="status" aria-live="polite">
                {message}
              </p>
            </div>

            {!editable ? (
              <button
                type="button"
                onClick={() => latest && applyVersion(latest)}
              >
                Return to latest
              </button>
            ) : (
              <button
                className="composer-button"
                type="submit"
                disabled={saving || !title.trim() || !content.trim()}
              >
                {saving
                  ? "Saving?"
                  : latest
                    ? "Save new version"
                    : "Import screenplay"}
                <span aria-hidden="true">{"\u2192"}</span>
              </button>
            )}
          </footer>
        </form>
      </div>
    </section>
  );
}
