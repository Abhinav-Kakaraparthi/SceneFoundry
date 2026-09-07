import type { ProductionProject } from "./productionCatalog";

export type ProductionDefaults = Readonly<{
  researchObjective: string;
  researchQueries: readonly [string, string];
  sceneBrief: string;
}>;

function readable(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function bounded(value: string, maximum: number): string {
  const clean = value.replace(/\s+/g, " ").trim();
  if (clean.length <= maximum) return clean;
  return `${clean.slice(0, maximum - 3).trimEnd()}...`;
}

export function createProductionDefaults(
  project: ProductionProject,
): ProductionDefaults {
  const genre = readable(project.genre);
  const style = readable(project.visual_style);

  return Object.freeze({
    researchObjective: bounded(
      `Ground the visual design of ${project.title}, a ${genre} production, ` +
        `using credible real-world references. Focus on ${style} production ` +
        `design, ${project.aspect_ratio} composition, and this premise: ` +
        project.premise,
      1000,
    ),
    researchQueries: [
      bounded(
        `${genre} ${style} cinematography production design references`,
        240,
      ),
      bounded(
        `${project.title} visual cultural location references ` +
          project.premise,
        240,
      ),
    ] as const,
    sceneBrief: bounded(
      `Create a ${project.seconds_per_episode}-second ${style} ` +
        `${genre} scene composed for ${project.aspect_ratio}. ` +
        project.premise,
      4000,
    ),
  });
}
