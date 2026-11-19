import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";


function renderApp(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></QueryClientProvider>);
}


afterEach(() => vi.restoreAllMocks());


describe("Preflop Trainer", () => {
  it("covers setup, exact-combo decision, and immediate EV feedback", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      const method = init?.method ?? "GET";
      if (path === "/api/v1/scenarios") return json({ items: [scenario] });
      if (path.includes("/api/v1/scenarios/")) return json(scenarioDetail);
      if (path === "/api/v1/training/sessions" && method === "POST") {
        const body = JSON.parse(String(init?.body));
        expect(body.nodeIds).toEqual(["node-000"]);
        expect(body.heroPositions).toEqual(["SB"]);
        return json(session, 201);
      }
      if (path === `/api/v1/training/sessions/${encodeURIComponent(session.sessionId)}`) return json({ ...session, decisions: [] });
      if (path.endsWith("/prompt") && method === "GET") return json(prompt);
      if (path.endsWith("/decisions") && method === "POST") return json({ session: { ...session, summary: { ...summary, decisionsCompleted: 1 } }, recorded: true, feedbackVisible: true, decision });
      throw new Error(`Unexpected request: ${method} ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderApp("/train?scenario=sb-vs-bb-100bb-after-folds&node=node-000");

    expect(await screen.findByRole("heading", { name: "Choose your drill" })).toBeInTheDocument();
    fireEvent.click(await screen.findByLabelText("I understand how this practice feedback is scoped."));
    fireEvent.click(screen.getByRole("button", { name: "Start 20-decision session" }));

    expect(await screen.findByText(/AsKs/, { selector: ".combo-code" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Call" }));

    expect(await screen.findByRole("heading", { name: "Small EV loss" })).toBeInTheDocument();
    expect(screen.getByText("0.005 BB", { selector: ".loss-callout strong" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "55.0%" })).toBeInTheDocument();
    expect(screen.getByText("phase2-hu-sb-bb-100bb-v1.1")).toBeInTheDocument();
  });

  it("renders saved metrics, exact history, and targeted drill controls", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith(`/training/sessions/${encodeURIComponent(session.sessionId)}`)) return json({ ...session, status: "COMPLETED", completedAt: session.startedAt, summary: reviewSummary, decisions: [decision] });
      throw new Error(`Unexpected request: ${path}`);
    }));
    renderApp(`/sessions/${encodeURIComponent(session.sessionId)}`);

    expect(await screen.findByRole("heading", { name: "SB practice review" })).toBeInTheDocument();
    expect(screen.getAllByText("AsKs").length).toBeGreaterThan(0);
    expect(screen.getAllByText("0.01 BB").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Redrill mistakes" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Practice close mixes" })).toBeInTheDocument();
    expect(screen.getByText(/Frequency calibration unlocks at 50 comparable decisions/)).toBeInTheDocument();
  });
});


function json(value: unknown, status = 200) { return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } }); }

const game = {
  variant: "NLHE", format: "CASH", tableSize: 6, effectiveStackBb: "100", smallBlindBb: "0.5", bigBlindBb: "1", anteBb: "0", positions: ["SB", "BB"],
  rake: { policyVersion: "NO_RAKE_SOURCE_V1", rate: "0", capBb: "0", noFlopNoDrop: true },
};
const actions = [
  { actionId: "fold", type: "FOLD", label: "Fold", targetBb: null, isAllIn: false, sourceCode: "F" },
  { actionId: "call", type: "CALL", label: "Call", targetBb: null, isAllIn: false, sourceCode: "C" },
  { actionId: "raise-to-2.5", type: "RAISE_TO", label: "Raise to 2.5 BB", targetBb: "2.5", isAllIn: false, sourceCode: "R2.5" },
];
const scenario = {
  scenarioId: "sb-vs-bb-100bb-after-folds", title: "SB vs BB after folds", solutionId: "solution:sha256:test", solutionVersion: "phase2-hu-sb-bb-100bb-v1.1", rootNodeId: "node-000", game,
  solver: { algorithm: "CFR+", iterations: 800 }, accuracy: { exploitabilityBbPerHand: "0.0008" }, trainerEligible: false, practiceAvailable: true, accuracyMode: "REFERENCE_MODEL", limitationCount: 5, nodeCount: 18,
};
const scenarioDetail = {
  ...scenario, description: "Test", assumedPriorActions: [], tree: {}, nodes: [{ nodeId: "node-000", actor: "SB", actionHistory: [], potBb: "1.5", actorStackBehindBb: "99.5", amountToCallBb: "0.5", actions, childNodeByAction: {} }],
};
const summary = {
  decisionsCompleted: 0, totalEvLossBb: "0", averageEvLossBb: "0", evLossPer100DecisionsBb: "0",
  severityCounts: { NO_MATERIAL_EV_LOSS: 0, SMALL_EV_LOSS: 0, SIGNIFICANT_MISTAKE: 0, MAJOR_MISTAKE: 0 },
  byPosition: [], byActionSequence: [], byScenario: [], byGroupedHand: [], frequencyCalibration: { minimumSample: 50, buckets: [] },
};
const session = {
  sessionId: "session:test", schemaVersion: "1.0.0", status: "ACTIVE", scenarioId: scenario.scenarioId, solutionId: scenario.solutionId, solutionVersion: scenario.solutionVersion,
  selectedNodeIds: ["node-000"], heroPositions: ["SB"], targetDecisions: 20, feedbackMode: "IMMEDIATE", scoringPolicyVersion: "1", samplingPolicyVersion: "UNIFORM_NODE_REACH_WEIGHTED_COMBO_V1", accuracyMode: "REFERENCE_MODEL", approximateAcknowledgedAt: "2026-11-19T00:00:00Z", rngEnabled: true, drillType: "STANDARD", sourceSessionId: null, startedAt: "2026-11-19T00:00:00Z", completedAt: null, summary,
};
const prompt = {
  promptId: "prompt:test", sessionId: session.sessionId, sequence: 1, targetDecisions: 20, scenarioId: scenario.scenarioId, solutionId: scenario.solutionId, solutionVersion: scenario.solutionVersion,
  nodeId: "node-000", heroPosition: "SB", heroCombo: "AsKs", groupedHand: "AKs", comboReachWeight: "1", actionHistory: [], potBb: "1.5", amountToCallBb: "0.5", actorStackBehindBb: "99.5",
  offeredOptions: actions.map((item) => ({ ...item, resolvedAction: { actor: "SB", type: item.type, isAllIn: false } })), feedbackMode: "IMMEDIATE", accuracyMode: "REFERENCE_MODEL", rngAvailable: true, rngRoll: null, rngMapping: null, presentedAt: session.startedAt,
};
const decision = {
  decisionId: "decision:test", promptId: prompt.promptId, sessionId: session.sessionId, sequence: 1, scenarioId: scenario.scenarioId, gameConfigId: "game:sha256:test", solutionId: scenario.solutionId, solutionVersion: scenario.solutionVersion,
  nodeId: "node-000", heroPosition: "SB", actionHistoryKey: "SB opening decision", heroCombo: "AsKs", groupedHand: "AKs", offeredOptions: prompt.offeredOptions, selectedOptionId: "call", selectedResolvedAction: { actor: "SB", type: "CALL", isAllIn: false }, comboReachWeight: "1",
  referenceSnapshot: [{ optionId: "fold", frequency: "0.025", actionEvBb: "0" }, { optionId: "call", frequency: "0.55", actionEvBb: "0.179" }, { optionId: "raise-to-2.5", frequency: "0.425", actionEvBb: "0.184" }], highestEvOptionId: "raise-to-2.5", evLossBb: "0.005", feedbackSeverity: "SMALL_EV_LOSS", strategyStatus: "SUPPORTED_MIX", scoringPolicyVersion: "1", accuracyMode: "REFERENCE_MODEL", rngRoll: null, rngMapping: null, presentedAt: session.startedAt, answeredAt: session.startedAt, interpretation: "Calling is part of the reference mix.",
};
const reviewSummary = { ...summary, decisionsCompleted: 1, totalEvLossBb: "0.005", averageEvLossBb: "0.005", evLossPer100DecisionsBb: "0.5", severityCounts: { ...summary.severityCounts, SMALL_EV_LOSS: 1 }, byPosition: [{ key: "SB", decisions: 1, totalEvLossBb: "0.005", averageEvLossBb: "0.005" }], byActionSequence: [{ key: "SB opening decision", decisions: 1, totalEvLossBb: "0.005", averageEvLossBb: "0.005" }], byScenario: [{ key: scenario.scenarioId, decisions: 1, totalEvLossBb: "0.005", averageEvLossBb: "0.005" }], byGroupedHand: [{ key: "AKs", decisions: 1, totalEvLossBb: "0.005", averageEvLossBb: "0.005" }] };
