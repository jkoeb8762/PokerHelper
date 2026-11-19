import type {
  Assumptions,
  CreateSessionInput,
  DecisionReplayResponse,
  RngMapping,
  ScenarioDetail,
  ScenarioSummary,
  SubmissionResponse,
  SolutionNode,
  TrainingPrompt,
  TrainingSession,
  TrainingSessionDetail,
  TrainingSummary,
} from "./types";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const message = payload?.error?.message ?? `Request failed with status ${response.status}`;
    throw new Error(message);
  }
  return payload as T;
}

async function sendJson<T>(path: string, method: "POST" | "DELETE", body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: { Accept: "application/json", ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) return undefined as T;
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

export function createTrainingSession(input: CreateSessionInput): Promise<TrainingSession> {
  return sendJson("/api/v1/training/sessions", "POST", input);
}

export function getTrainingSessions(): Promise<{ items: TrainingSession[] }> {
  return getJson("/api/v1/training/sessions");
}

export function getTrainingStatistics(): Promise<TrainingSummary> {
  return getJson("/api/v1/training/statistics");
}

export function getTrainingSession(sessionId: string): Promise<TrainingSessionDetail> {
  return getJson(`/api/v1/training/sessions/${encodeURIComponent(sessionId)}`);
}

export function getTrainingPrompt(sessionId: string): Promise<TrainingPrompt> {
  return getJson(`/api/v1/training/sessions/${encodeURIComponent(sessionId)}/prompt`);
}

export function showTrainingRng(sessionId: string): Promise<{ roll: number; mapping: RngMapping[] }> {
  return sendJson(`/api/v1/training/sessions/${encodeURIComponent(sessionId)}/prompt/rng`, "POST");
}

export function submitTrainingDecision(sessionId: string, promptId: string, selectedOptionId: string): Promise<SubmissionResponse> {
  return sendJson(`/api/v1/training/sessions/${encodeURIComponent(sessionId)}/decisions`, "POST", { promptId, selectedOptionId });
}

export function completeTrainingSession(sessionId: string): Promise<TrainingSession> {
  return sendJson(`/api/v1/training/sessions/${encodeURIComponent(sessionId)}/complete`, "POST");
}

export function repeatTrainingSession(sessionId: string): Promise<TrainingSession> {
  return sendJson(`/api/v1/training/sessions/${encodeURIComponent(sessionId)}/repeat`, "POST");
}

export function redrillTrainingSession(sessionId: string, mode: "MISTAKES" | "CLOSE_DECISIONS"): Promise<TrainingSession> {
  return sendJson(`/api/v1/training/sessions/${encodeURIComponent(sessionId)}/redrill`, "POST", { mode });
}

export function getDecisionReplay(sessionId: string, decisionId: string): Promise<DecisionReplayResponse> {
  return getJson(`/api/v1/training/sessions/${encodeURIComponent(sessionId)}/decisions/${encodeURIComponent(decisionId)}`);
}

export function deleteTrainingSession(sessionId: string): Promise<void> {
  return sendJson(`/api/v1/training/sessions/${encodeURIComponent(sessionId)}`, "DELETE");
}
