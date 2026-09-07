import { useEffect, useState } from "react";
import DirectorWorkspace from "./DirectorWorkspace";
import ProductionDashboard from "./ProductionDashboard";
import StudioShell from "./StudioShell";
import type { ProductionProject } from "./productionCatalog";

type Selection = {
  projectId: string;
  projectTitle: string;
  initialAttemptId: string | null;
};

const demoSelection: Selection = {
  projectId: "demo_cafe",
  projectTitle: "The Red Envelope",
  initialAttemptId: "9480269091d94b628b5cf97af3075260",
};

function readSelection(): Selection | null {
  const url = new URL(window.location.href);
  const projectId = url.searchParams.get("project");
  const attemptId = url.searchParams.get("attempt");

  if (
    projectId &&
    /^[A-Za-z0-9_-]{1,64}$/.test(projectId)
  ) {
    const rawTitle = url.searchParams.get("title")?.trim();
    return {
      projectId,
      projectTitle: rawTitle?.slice(0, 120) || "Untitled production",
      initialAttemptId:
        attemptId && /^[a-f0-9]{32}$/.test(attemptId)
          ? attemptId
          : null,
    };
  }

  if (attemptId && /^[a-f0-9]{32}$/.test(attemptId)) {
    return {
      ...demoSelection,
      initialAttemptId: attemptId,
    };
  }

  return null;
}

function writeSelection(selection: Selection | null) {
  const url = new URL(window.location.href);

  if (!selection) {
    url.searchParams.delete("project");
    url.searchParams.delete("title");
    url.searchParams.delete("attempt");
    url.hash = "";
  } else {
    url.searchParams.set("project", selection.projectId);
    url.searchParams.set("title", selection.projectTitle);

    if (selection.initialAttemptId) {
      url.searchParams.set(
        "attempt",
        selection.initialAttemptId,
      );
    } else {
      url.searchParams.delete("attempt");
    }

    url.hash = "overview";
  }

  window.history.pushState(null, "", url);
}

export default function App() {
  const [selection, setSelection] =
    useState<Selection | null>(readSelection);

  useEffect(() => {
    const restore = () => setSelection(readSelection());
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);

  function showDashboard() {
    writeSelection(null);
    setSelection(null);
  }

  function openProject(project: ProductionProject) {
    const next: Selection = {
      projectId: project.project_id,
      projectTitle: project.title,
      initialAttemptId: null,
    };
    writeSelection(next);
    setSelection(next);
  }

  function openDemo() {
    writeSelection(demoSelection);
    setSelection(demoSelection);
  }

  if (selection) {
    return (
      <DirectorWorkspace
        key={selection.projectId}
        projectId={selection.projectId}
        projectTitle={selection.projectTitle}
        initialAttemptId={selection.initialAttemptId}
        onHome={showDashboard}
      />
    );
  }

  return (
    <StudioShell
      projectId={null}
      projectTitle={null}
      attemptId={null}
      onHome={showDashboard}
    >
      <ProductionDashboard
        onOpen={openProject}
        onOpenDemo={openDemo}
      />
    </StudioShell>
  );
}
