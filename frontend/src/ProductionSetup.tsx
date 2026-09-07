import { useEffect, useState } from "react";
import BriefForm from "./BriefForm";
import ProductionResearch from "./ProductionResearch";
import { getProduction } from "./productionCatalog";
import {
  createProductionDefaults,
  type ProductionDefaults,
} from "./productionPrompts";

type Props = {
  projectId: string;
  selectedResearchId: string | null;
  onSelected: (researchId: string | null) => void;
  onCreated: (attemptId: string) => void;
};

export default function ProductionSetup({
  projectId,
  selectedResearchId,
  onSelected,
  onCreated,
}: Props) {
  const catalogProject = projectId.startsWith("project_");
  const [defaults, setDefaults] =
    useState<ProductionDefaults | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!catalogProject) return;

    const controller = new AbortController();
    setDefaults(null);
    setError(null);

    getProduction(projectId, controller.signal)
      .then((project) => {
        if (!controller.signal.aborted) {
          setDefaults(createProductionDefaults(project));
        }
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            reason instanceof Error
              ? reason.message
              : "Production configuration could not be loaded.",
          );
        }
      });

    return () => controller.abort();
  }, [catalogProject, projectId]);

  if (!catalogProject) {
    return (
      <>
        <ProductionResearch
          projectId={projectId}
          selectedResearchId={selectedResearchId}
          onSelected={onSelected}
        />
        <BriefForm
          projectId={projectId}
          researchId={selectedResearchId}
          onCreated={onCreated}
        />
      </>
    );
  }

  if (error) {
    return (
      <div className="notice">
        <h2>Production configuration unavailable</h2>
        <p>{error}</p>
      </div>
    );
  }

  if (!defaults) {
    return (
      <div className="notice">
        <h2>Loading production configuration</h2>
        <p>Preparing the immutable creative direction.</p>
      </div>
    );
  }

  return (
    <>
      <ProductionResearch
        projectId={projectId}
        selectedResearchId={selectedResearchId}
        onSelected={onSelected}
        initialResearchObjective={defaults.researchObjective}
        initialResearchQueries={defaults.researchQueries}
      />
      <BriefForm
        projectId={projectId}
        researchId={selectedResearchId}
        initialBrief={defaults.sceneBrief}
        onCreated={onCreated}
      />
    </>
  );
}
