import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const ranks = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"];
const groups = ranks.flatMap((rowRank, row) => ranks.map((columnRank, column) => (
  row === column ? rowRank + columnRank : column > row ? rowRank + columnRank + "s" : columnRank + rowRank + "o"
)));

function wrapper(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}><App /></MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("Study browser", () => {
  it("renders a validated scenario card", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ items: [scenarioSummary] }), { status: 200 })));
    wrapper("/");
    expect(await screen.findByRole("heading", { name: "SB vs BB after folds" })).toBeInTheDocument();
    expect(screen.getByText("Study-only approximate model")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open study browser/ })).toHaveAttribute("href", "/study/sb-vs-bb-100bb-after-folds/node-000");
  });

  it("shows all 169 grouped hands and the exact suited combo values", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("/nodes/")) return new Response(JSON.stringify(node), { status: 200 });
      if (path.includes("/scenarios/")) return new Response(JSON.stringify(scenarioDetail), { status: 200 });
      throw new Error(`unexpected request ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    wrapper("/study/sb-vs-bb-100bb-after-folds/node-000?combo=AsAh");

    expect(await screen.findByRole("heading", { name: "AA" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByRole("gridcell")).toHaveLength(169));
    expect(screen.getByLabelText("AsAh")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "60.0%" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "+0.250" })).toBeInTheDocument();
  });
});

const game = {
  variant: "NLHE", format: "CASH", tableSize: 6, effectiveStackBb: "100",
  smallBlindBb: "0.5", bigBlindBb: "1", anteBb: "0", positions: ["SB", "BB"],
  rake: { policyVersion: "NO_RAKE_SOURCE_V1", rate: "0", capBb: "0", noFlopNoDrop: true },
};

const scenarioSummary = {
  scenarioId: "sb-vs-bb-100bb-after-folds", title: "SB vs BB after folds", solutionId: "solution:sha256:test",
  solutionVersion: "phase2-test", rootNodeId: "node-000", game,
  solver: { algorithm: "CFR+", iterations: 10 }, accuracy: { exploitabilityBbPerHand: "0.01" },
  trainerEligible: false, limitationCount: 1, nodeCount: 1,
};

const actions = [
  { actionId: "fold", type: "FOLD", label: "Fold", targetBb: null, isAllIn: false, sourceCode: "F" },
  { actionId: "call", type: "CALL", label: "Limp to 1 BB", targetBb: null, isAllIn: false, sourceCode: "C" },
];

const groupedHands = Object.fromEntries(groups.map((group) => [group, {
  comboCount: group.length === 2 ? 6 : group.endsWith("s") ? 4 : 12,
  reachWeight: "1", frequencies: { fold: "0.4", call: "0.6" }, evBb: { fold: "0", call: "0.25" },
}]));

const node = {
  solutionId: "solution:sha256:test", solutionVersion: "phase2-test", scenarioId: "sb-vs-bb-100bb-after-folds",
  schemaVersion: "1.0.0", nodeId: "node-000", sourceNodeIndex: 0, actor: "SB", actionHistory: [],
  potBb: "1.5", actorContributionBb: "0.5", actorStackBehindBb: "99.5", amountToCallBb: "0.5",
  actions, childNodeByAction: {}, groupedHands,
  exactCombos: { AsAh: { group: "AA", reachFrequency: "1", frequencies: { fold: "0.4", call: "0.6" }, evBb: { fold: "0", call: "0.25" } } },
};

const scenarioDetail = {
  ...scenarioSummary,
  description: "Test scenario",
  assumedPriorActions: [],
  tree: {},
  nodes: [{ nodeId: "node-000", actor: "SB", actionHistory: [], potBb: "1.5", actorStackBehindBb: "99.5", amountToCallBb: "0.5", actions, childNodeByAction: {} }],
};
