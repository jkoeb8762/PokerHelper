import type { Assumptions, ScenarioDetail, ScenarioSummary, SolutionNode } from "./types";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const message = payload?.error?.message ?? `Request failed with status ${response.status}`;
    throw new Error(message);
  }
  return payload as T;
}

export function getScenarios(): Promise<{ items: ScenarioSummary[] }> {
  return getJson("/api/v1/scenarios");
}

export function getScenario(scenarioId: string): Promise<ScenarioDetail> {
  return getJson(`/api/v1/scenarios/${encodeURIComponent(scenarioId)}`);
}

export function getNode(solutionId: string, nodeId: string): Promise<SolutionNode> {
  return getJson(`/api/v1/solutions/${encodeURIComponent(solutionId)}/nodes/${encodeURIComponent(nodeId)}`);
}

export function getAssumptions(solutionId: string): Promise<Assumptions> {
  return getJson(`/api/v1/solutions/${encodeURIComponent(solutionId)}/assumptions`);
}
