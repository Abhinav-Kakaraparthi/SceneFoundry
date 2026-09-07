import { authenticatedFetch } from "./authSession";

export type ProjectGenre =
  | "action"
  | "comedy"
  | "documentary"
  | "drama"
  | "fantasy"
  | "romance"
  | "science_fiction"
  | "thriller";

export type VisualStyle =
  | "anime"
  | "cinematic_realism"
  | "documentary"
  | "graphic_novel"
  | "neo_noir"
  | "retro_futurism"
  | "stop_motion"
  | "watercolor";

export type AspectRatio = "9:16" | "16:9";

export type ProductionProject = {
  project_id: string;
  creation_id: string;
  created_by: string;
  title: string;
  premise: string;
  genre: ProjectGenre;
  visual_style: VisualStyle;
  aspect_ratio: AspectRatio;
  episode_count: number;
  seconds_per_episode: number;
  budget_micro_usd: number;
  status: "development";
  created_at: string;
};

export type CreateProductionInput = {
  creation_id: string;
  title: string;
  premise: string;
  genre: ProjectGenre;
  visual_style: VisualStyle;
  aspect_ratio: AspectRatio;
  episode_count: number;
  seconds_per_episode: number;
  budget_cents: number;
};

type CreateProductionResponse = {
  created: boolean;
  project: ProductionProject;
};

export const genreOptions: ReadonlyArray<{
  value: ProjectGenre;
  label: string;
}> = [
  { value: "action", label: "Action" },
  { value: "comedy", label: "Comedy" },
  { value: "documentary", label: "Documentary" },
  { value: "drama", label: "Drama" },
  { value: "fantasy", label: "Fantasy" },
  { value: "romance", label: "Romance" },
  { value: "science_fiction", label: "Science fiction" },
  { value: "thriller", label: "Thriller" },
];

export const styleOptions: ReadonlyArray<{
  value: VisualStyle;
  label: string;
  description: string;
}> = [
  {
    value: "cinematic_realism",
    label: "Cinematic realism",
    description: "Natural texture, controlled light, and grounded detail.",
  },
  {
    value: "neo_noir",
    label: "Neo-noir",
    description: "Hard shadows, practical light, and dramatic contrast.",
  },
  {
    value: "anime",
    label: "Anime",
    description: "Expressive framing with polished illustrated motion.",
  },
  {
    value: "graphic_novel",
    label: "Graphic novel",
    description: "Bold composition, inked contrast, and selective color.",
  },
  {
    value: "retro_futurism",
    label: "Retro futurism",
    description: "Analog technology, luminous color, and imagined futures.",
  },
  {
    value: "documentary",
    label: "Documentary",
    description: "Observational camera language and available light.",
  },
  {
    value: "stop_motion",
    label: "Stop motion",
    description: "Tactile materials and deliberately handcrafted movement.",
  },
  {
    value: "watercolor",
    label: "Watercolor",
    description: "Soft pigment, atmospheric edges, and painterly motion.",
  },
];

async function responseDetail(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    // The HTTP status remains the authoritative fallback.
  }

  return `Production request failed (HTTP ${response.status}).`;
}

export function newCreationId(): string {
  return crypto.randomUUID().replaceAll("-", "");
}

export async function listProductions(
  signal?: AbortSignal,
): Promise<ProductionProject[]> {
  const response = await authenticatedFetch("/v1/projects", {
    signal,
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(await responseDetail(response));
  }

  return (await response.json()) as ProductionProject[];
}

export async function createProduction(
  input: CreateProductionInput,
): Promise<CreateProductionResponse> {
  const response = await authenticatedFetch("/v1/projects", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new Error(await responseDetail(response));
  }

  return (await response.json()) as CreateProductionResponse;
}

export async function getProduction(
  projectId: string,
  signal?: AbortSignal,
): Promise<ProductionProject> {
  const encodedId = encodeURIComponent(projectId);
  const response = await authenticatedFetch(
    `/v1/projects/${encodedId}`,
    {
      signal,
      headers: { Accept: "application/json" },
    },
  );

  if (!response.ok) {
    throw new Error(await responseDetail(response));
  }

  return (await response.json()) as ProductionProject;
}
