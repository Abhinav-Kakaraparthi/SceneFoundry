import { useEffect, useMemo, useState } from "react";
import { useAuth } from "./AuthGate";
import CreateProductionModal from "./CreateProductionModal";
import {
  listProductions,
  styleOptions,
  type ProductionProject,
} from "./productionCatalog";

type Props = {
  onOpen: (project: ProductionProject) => void;
  onOpenDemo: () => void;
};

const dollars = (microUsd: number) =>
  `$${(microUsd / 1_000_000).toFixed(2)}`;

const label = (value: string) =>
  value
    .split("_")
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(" ");

function projectRuntime(project: ProductionProject): string {
  const total =
    project.episode_count * project.seconds_per_episode;
  return `${project.episode_count} ${
    project.episode_count === 1 ? "episode" : "episodes"
  } · ${total}s total`;
}

export default function ProductionDashboard({
  onOpen,
  onOpenDemo,
}: Props) {
  const { user } = useAuth();
  const [projects, setProjects] = useState<ProductionProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [reload, setReload] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    listProductions(controller.signal)
      .then((records) => {
        if (!controller.signal.aborted) {
          setProjects(records);
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
              : "Production history could not be loaded.",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [reload]);

  const configuredBudget = useMemo(
    () =>
      projects.reduce(
        (total, project) => total + project.budget_micro_usd,
        0,
      ),
    [projects],
  );

  const firstName =
    user.name.trim().split(/\s+/)[0] || "Director";

  function created(
    project: ProductionProject,
    wasCreated: boolean,
  ) {
    setProjects((current) => [
      project,
      ...current.filter(
        (item) => item.project_id !== project.project_id,
      ),
    ]);
    setModalOpen(false);
    setMessage(
      wasCreated
        ? `${project.title} is ready for development.`
        : `${project.title} was already safely created.`,
    );
  }

  return (
    <>
      <main className="production-dashboard" id="productions">
        <header className="dashboard-hero">
          <div>
            <p className="eyebrow">PRODUCTION CATALOG</p>
            <h1>Good to see you, {firstName}.</h1>
            <p>
              Build grounded stories, review every decision, and
              produce only approved cinematic shots.
            </p>
          </div>

          <button
            className="dashboard-create-button"
            type="button"
            onClick={() => {
              setMessage(null);
              setModalOpen(true);
            }}
          >
            Start a new production
            <span aria-hidden="true">→</span>
          </button>
        </header>

        <section
          className="dashboard-summary"
          aria-label="Production summary"
        >
          <div>
            <span>Productions</span>
            <strong>{projects.length}</strong>
          </div>
          <div>
            <span>In development</span>
            <strong>{projects.length}</strong>
          </div>
          <div>
            <span>Configured budget</span>
            <strong>{dollars(configuredBudget)}</strong>
          </div>
          <div>
            <span>Production stack</span>
            <strong>Parallel · Gemini · Veo</strong>
          </div>
        </section>

        {message && (
          <p className="dashboard-message" role="status">
            {message}
          </p>
        )}

        {error && (
          <div className="dashboard-message error" role="alert">
            <span>{error}</span>
            <button
              type="button"
              onClick={() => setReload((value) => value + 1)}
            >
              Retry
            </button>
          </div>
        )}

        <section
          className="dashboard-demo"
          aria-labelledby="demo-production-title"
        >
          <div className="dashboard-demo-art" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>

          <div className="dashboard-demo-copy">
            <div>
              <p className="eyebrow">LIVE REFERENCE PRODUCTION</p>
              <span className="dashboard-status">
                <i aria-hidden="true" />
                Approved
              </span>
            </div>
            <h2 id="demo-production-title">The Red Envelope</h2>
            <p>
              A grounded late-night café exchange with immutable
              Parallel evidence, Gemini direction, human approval,
              and production-ready shots.
            </p>
            <div className="dashboard-demo-meta">
              <span>Neo-noir</span>
              <span>16:9</span>
              <span>12 seconds</span>
              <span>3 directed shots</span>
            </div>
          </div>

          <button type="button" onClick={onOpenDemo}>
            Continue production
            <span aria-hidden="true">→</span>
          </button>
        </section>

        <section
          className="dashboard-library"
          aria-labelledby="production-library-title"
        >
          <div className="dashboard-library-heading">
            <div>
              <p className="eyebrow">YOUR PRODUCTIONS</p>
              <h2 id="production-library-title">
                Production library
              </h2>
            </div>
            <span>
              {loading
                ? "Loading…"
                : `${projects.length} ${
                    projects.length === 1
                      ? "production"
                      : "productions"
                  }`}
            </span>
          </div>

          {loading ? (
            <div className="dashboard-loading" role="status">
              <span aria-hidden="true" />
              Loading your production history…
            </div>
          ) : projects.length === 0 ? (
            <div className="dashboard-empty">
              <span className="dashboard-empty-mark" aria-hidden="true">
                +
              </span>
              <h3>Your next production starts here.</h3>
              <p>
                Establish the premise, visual language, format,
                runtime, and budget before the agents begin.
              </p>
              <button
                type="button"
                onClick={() => setModalOpen(true)}
              >
                Create first production
              </button>
            </div>
          ) : (
            <div className="production-card-grid">
              {projects.map((project) => {
                const style = styleOptions.find(
                  (option) =>
                    option.value === project.visual_style,
                );

                return (
                  <article
                    className="production-card"
                    key={project.project_id}
                  >
                    <div
                      className="production-card-art"
                      data-style={project.visual_style}
                    >
                      <span>{project.aspect_ratio}</span>
                      <i aria-hidden="true" />
                    </div>

                    <div className="production-card-body">
                      <div className="production-card-heading">
                        <span>{label(project.genre)}</span>
                        <span className="production-state">
                          Development
                        </span>
                      </div>

                      <h3>{project.title}</h3>
                      <p>{project.premise}</p>

                      <div className="production-card-meta">
                        <span>{style?.label ?? label(project.visual_style)}</span>
                        <span>{projectRuntime(project)}</span>
                        <span>{dollars(project.budget_micro_usd)} limit</span>
                      </div>
                    </div>

                    <footer className="production-card-footer">
                      <span>
                        {project.project_id.slice(-10)}
                      </span>
                      <button
                        type="button"
                        onClick={() => onOpen(project)}
                      >
                        Open production
                        <span aria-hidden="true">→</span>
                      </button>
                    </footer>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </main>

      <CreateProductionModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={created}
      />
    </>
  );
}
