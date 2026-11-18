export type DecimalString = string;

export interface ActionOption {
  actionId: string;
  type: "FOLD" | "CHECK" | "CALL" | "RAISE_TO";
  label: string;
  targetBb: DecimalString | null;
  isAllIn: boolean;
  sourceCode: string;
}

export interface HistoryAction {
  actor: string;
  type: string;
  targetBb: DecimalString | null;
  isAllIn: boolean;
  label: string;
}

export interface HandStrategy {
  group: string;
  reachFrequency: DecimalString;
  frequencies: Record<string, DecimalString>;
  evBb: Record<string, DecimalString>;
}

export interface GroupStrategy {
  comboCount: number;
  reachWeight: DecimalString;
  frequencies: Record<string, DecimalString>;
  evBb: Record<string, DecimalString>;
}

export interface SolutionNode {
  solutionId: string;
  solutionVersion: string;
  scenarioId: string;
  schemaVersion: string;
  nodeId: string;
  sourceNodeIndex: number;
  actor: "SB" | "BB";
  actionHistory: HistoryAction[];
  potBb: DecimalString;
  actorContributionBb: DecimalString;
  actorStackBehindBb: DecimalString;
  amountToCallBb: DecimalString;
  actions: ActionOption[];
  childNodeByAction: Record<string, string>;
  groupedHands: Record<string, GroupStrategy>;
  exactCombos: Record<string, HandStrategy>;
}

export interface GameMetadata {
  variant: string;
  format: string;
  tableSize: number;
  effectiveStackBb: DecimalString;
  smallBlindBb: DecimalString;
  bigBlindBb: DecimalString;
  anteBb: DecimalString;
  positions: string[];
  rake: {
    policyVersion: string;
    rate: DecimalString;
    capBb: DecimalString;
    noFlopNoDrop: boolean;
  };
}

export interface NodeSummary {
  nodeId: string;
  actor: "SB" | "BB";
  actionHistory: HistoryAction[];
  potBb: DecimalString;
  actorStackBehindBb: DecimalString;
  amountToCallBb: DecimalString;
  actions: ActionOption[];
  childNodeByAction: Record<string, string>;
}

export interface ScenarioSummary {
  scenarioId: string;
  title: string;
  solutionId: string;
  solutionVersion: string;
  rootNodeId: string;
  game: GameMetadata;
  solver: Record<string, string | number>;
  accuracy: Record<string, string | null>;
  trainerEligible: boolean;
  limitationCount: number;
  nodeCount: number;
}

export interface ScenarioDetail extends ScenarioSummary {
  description: string;
  assumedPriorActions: Array<{ actor: string; type: string }>;
  tree: Record<string, string | number | boolean | string[]>;
  nodes: NodeSummary[];
}

export interface Assumptions {
  solutionId: string;
  version: string;
  generatedAt: string;
  authorization: Record<string, string | boolean>;
  source: Record<string, string>;
  game: GameMetadata;
  tree: Record<string, unknown>;
  solver: Record<string, string | number>;
  accuracy: Record<string, string | null>;
  limitations: string[];
  trainerEligible: boolean;
}
