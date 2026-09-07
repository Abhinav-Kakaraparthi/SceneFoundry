import {
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import { authenticatedFetch } from "./authSession";

type ResearchSource = {
  url: string;
  title: string;
  excerpts: string[];
};

type ResearchRecord = {
  research_id: string;
  studio_project_id: string;
  requested_by: string;
  request_sha256: string;
  max_results: number;
  evidence: {
    provider: "parallel";
    mode: "fast";
    search_id: string;
    objective: string;
    search_queries: string[];
    sources: ResearchSource[];
    warnings: string[];
  };
};

type ResearchResponse = {
  created: boolean;
  record: ResearchRecord;
};

type Props = {
  projectId: string;
};

const initialObjective =
  "Ground the visual design of a quiet late-night cafe exchange involving a sealed red envelope using credible real-world references.";

const initialQueries = [
  "late-night cafe interior practical lighting cinematic reference",
  "red envelope symbolism cultural context film production",
];

async function errorDetail(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    // Use the status fallback when the body is unavailable.
  }

  return `Research request failed (HTTP ${response.status}).`;
}

function cleanEvidenceText(value: string): string {
  const parsed = new DOMParser().parseFromString(
    value,
    "text/html",
  );

  return (parsed.body.textContent ?? value)
    .replace(
      /\[([^\]]*)\]\((https?:\/\/[^)]+)\)/g,
      (_match, label: string, url: string) => label || url,
    )
    .replace(/\s+/g, " ")
    .trim();
}

export default function ProductionResearch({ projectId }: Props) {
  const basePath = `/v1/projects/${projectId}/research`;
  const [objective, setObjective] = useState(initialObjective);
  const [queries, setQueries] = useState(initialQueries);
  const [records, setRecords] = useState<ResearchRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    authenticatedFetch(basePath, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(await errorDetail(response));
        }
        return (await response.json()) as ResearchRecord[];
      })
      .then((items) => {
        if (!controller.signal.aborted) {
          setRecords(items);
        }
      })
      .catch((caught: unknown) => {
        if (
          !controller.signal.aborted &&
          !(caught instanceof DOMException && caught.name === "AbortError")
        ) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Research history could not be loaded.",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [basePath]);

  const valid = useMemo(
    () =>
      objective.trim().length > 0 &&
      queries.every((query) => query.trim().length > 0) &&
      new Set(
        queries.map((query) => query.trim().toLowerCase()),
      ).size === queries.length,
    [objective, queries],
  );

  function updateQuery(index: number, value: string) {
    setQueries((current) =>
      current.map((query, position) =>
        position === index ? value : query,
      ),
    );
  }

  async function runResearch(event: FormEvent) {
    event.preventDefault();
    if (!valid || running) {
      return;
    }

    setRunning(true);
    setError(null);
    setMessage(null);

    try {
      const response = await authenticatedFetch(basePath, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          objective: objective.trim(),
          search_queries: queries.map((query) => query.trim()),
          max_results: 5,
        }),
      });

      if (!response.ok) {
        throw new Error(await errorDetail(response));
      }

      const payload = (await response.json()) as ResearchResponse;
      setRecords((current) => [
        payload.record,
        ...current.filter(
          (item) =>
            item.research_id !== payload.record.research_id,
        ),
      ]);
      setMessage(
        payload.created
          ? "Fresh web evidence captured and attributed."
          : "Identical research reused without another partner call.",
      );
    } catch (caught: unknown) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Production research failed.",
      );
    } finally {
      setRunning(false);
    }
  }

  return (
    <section
      id="research"
      className="research-workspace"
      aria-labelledby="research-title"
    >
      <header className="research-heading">
        <div>
          <p className="eyebrow">PRODUCTION INTELLIGENCE</p>
          <h2 id="research-title">Ground the scene in reality</h2>
          <p>
            Search current web sources before Gemini makes visual,
            cultural, or location-sensitive production decisions.
          </p>
        </div>
        <span className="parallel-badge">
          <span aria-hidden="true" />
          Grounded by Parallel
        </span>
      </header>

      <form className="research-form" onSubmit={runResearch}>
        <div className="research-objective">
          <label htmlFor="research-objective">Research objective</label>
          <textarea
            id="research-objective"
            value={objective}
            maxLength={1000}
            onChange={(event) => setObjective(event.target.value)}
          />
          <small>{objective.length} / 1,000</small>
        </div>

        <fieldset className="research-queries">
          <legend>Search directions</legend>
          {queries.map((query, index) => (
            <label key={index}>
              <span>Query {index + 1}</span>
              <input
                value={query}
                maxLength={200}
                onChange={(event) =>
                  updateQuery(index, event.target.value)
                }
              />
            </label>
          ))}
        </fieldset>

        <div className="research-action">
          <div>
            <strong>One bounded partner request</strong>
            <span>
              Fast mode &middot; Up to 5 citation-ready sources &middot; Exact
              retries are reused
            </span>
          </div>
          <button type="submit" disabled={!valid || running}>
            {running ? "Searching..." : "Research production"}
            <span aria-hidden="true">&#8594;</span>
          </button>
        </div>
      </form>

      {(message || error) && (
        <p
          className={`research-message${error ? " error" : ""}`}
          role={error ? "alert" : "status"}
        >
          {error || message}
        </p>
      )}

      <div className="research-results">
        <div className="research-results-heading">
          <div>
            <span className="sidebar-label">EVIDENCE LIBRARY</span>
            <strong>
              {records.length}
              {records.length === 1 ? " research run" : " research runs"}
            </strong>
          </div>
          {loading && <span>Loading history?</span>}
        </div>

        {!loading && records.length === 0 && (
          <div className="research-empty">
            <strong>No production evidence yet</strong>
            <p>
              Run the prepared research once to create a cited,
              immutable evidence record.
            </p>
          </div>
        )}

        {records.slice(0, 3).map((record) => (
          <article
            className="research-record"
            key={record.research_id}
          >
            <header>
              <div>
                <span>PARALLEL SEARCH</span>
                <strong>{record.evidence.objective}</strong>
              </div>
              <code>{record.evidence.search_id}</code>
            </header>

            <div className="research-source-grid">
              {record.evidence.sources.map((source) => (
                <a
                  className="research-source"
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                  key={`${record.research_id}:${source.url}`}
                >
                  <span className="research-source-index">
                    {String(
                      record.evidence.sources.indexOf(source) + 1,
                    ).padStart(2, "0")}
                  </span>
                  <strong>{cleanEvidenceText(source.title)}</strong>
                  <p>{cleanEvidenceText(source.excerpts[0] ?? "")}</p>
                  <span className="research-source-link">
                    Open source <span aria-hidden="true">&#8599;</span>
                  </span>
                </a>
              ))}
            </div>

            <footer>
              <span>
                {record.evidence.sources.length} cited sources
              </span>
              <span>Immutable request {record.request_sha256.slice(0, 12)}</span>
            </footer>
          </article>
        ))}
      </div>
    </section>
  );
}
