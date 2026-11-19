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
  practiceAvailable: boolean;
  accuracyMode: "CERTIFIED" | "REFERENCE_MODEL";
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
  practiceAvailable: boolean;
  accuracyMode: "CERTIFIED" | "REFERENCE_MODEL";
}

export type FeedbackMode = "IMMEDIATE" | "DELAYED";
export type SessionStatus = "ACTIVE" | "COMPLETED" | "ABANDONED";
export type FeedbackSeverity = "NO_MATERIAL_EV_LOSS" | "SMALL_EV_LOSS" | "SIGNIFICANT_MISTAKE" | "MAJOR_MISTAKE";

export interface SummaryBreakdown {
  key: string;
  decisions: number;
  totalEvLossBb: DecimalString;
  averageEvLossBb: DecimalString;
}

export interface CalibrationAction {
  optionId: string;
  observedFrequency: DecimalString;
  referenceFrequency: DecimalString;
  deviationPp: DecimalString;
}

export interface CalibrationBucket {
  scenarioId: string;
  solutionId: string;
  nodeId: string;
  groupedHand: string;
  sampleSize: number;
  actions: CalibrationAction[];
}

export interface TrainingSummary {
  decisionsCompleted: number;
  totalEvLossBb: DecimalString;
  averageEvLossBb: DecimalString;
  evLossPer100DecisionsBb: DecimalString;
  severityCounts: Record<FeedbackSeverity, number>;
  byPosition: SummaryBreakdown[];
  byActionSequence: SummaryBreakdown[];
  byScenario: SummaryBreakdown[];
  byGroupedHand: SummaryBreakdown[];
  frequencyCalibration: { minimumSample: number; buckets: CalibrationBucket[] };
}

export interface TrainingSession {
  sessionId: string;
  schemaVersion: string;
  status: SessionStatus;
  scenarioId: string;
  solutionId: string;
  solutionVersion: string;
  selectedNodeIds: string[];
  heroPositions: Array<"SB" | "BB">;
  targetDecisions: number;
  feedbackMode: FeedbackMode;
  scoringPolicyVersion: string;
  samplingPolicyVersion: string;
  accuracyMode: "CERTIFIED" | "REFERENCE_MODEL";
  approximateAcknowledgedAt: string | null;
  rngEnabled: boolean;
  drillType: "STANDARD" | "REPEAT" | "MISTAKE_REVIEW" | "CLOSE_DECISIONS";
  sourceSessionId: string | null;
  startedAt: string;
  completedAt: string | null;
  summary: TrainingSummary;
}

export interface PromptOption extends ActionOption {
  resolvedAction: Record<string, string | boolean>;
}

export interface RngMapping {
  optionId: string;
  label: string;
  start: number;
  end: number;
}

export interface TrainingPrompt {
  promptId: string;
  sessionId: string;
  sequence: number;
  targetDecisions: number;
  scenarioId: string;
  solutionId: string;
  solutionVersion: string;
  nodeId: string;
  heroPosition: "SB" | "BB";
  heroCombo: string;
  groupedHand: string;
  comboReachWeight: DecimalString;
  actionHistory: HistoryAction[];
  potBb: DecimalString;
  amountToCallBb: DecimalString;
  actorStackBehindBb: DecimalString;
  offeredOptions: PromptOption[];
  feedbackMode: FeedbackMode;
  accuracyMode: "CERTIFIED" | "REFERENCE_MODEL";
  rngAvailable: boolean;
  rngRoll: number | null;
  rngMapping: RngMapping[] | null;
  presentedAt: string;
}

export interface ReferenceSnapshot {
  optionId: string;
  frequency: DecimalString;
  actionEvBb: DecimalString;
}

export interface TrainingDecision {
  decisionId: string;
  promptId?: string;
  sessionId: string;
  sequence: number;
  scenarioId?: string;
  gameConfigId?: string;
  solutionId?: string;
  solutionVersion?: string;
  nodeId?: string;
  heroPosition?: "SB" | "BB";
  actionHistoryKey?: string;
  heroCombo: string;
  groupedHand: string;
  offeredOptions?: PromptOption[];
  selectedOptionId: string;
  selectedResolvedAction?: Record<string, string | boolean>;
  comboReachWeight?: DecimalString;
  referenceSnapshot?: ReferenceSnapshot[];
  highestEvOptionId?: string;
  evLossBb?: DecimalString;
  feedbackSeverity?: FeedbackSeverity;
  strategyStatus?: string;
  scoringPolicyVersion?: string;
  accuracyMode?: "CERTIFIED" | "REFERENCE_MODEL";
  rngRoll?: number | null;
  rngMapping?: RngMapping[] | null;
  presentedAt?: string;
  answeredAt: string;
  interpretation?: string;
  feedbackPending?: boolean;
}

export interface TrainingSessionDetail extends TrainingSession {
  decisions: TrainingDecision[];
}

export interface SubmissionResponse {
  session: TrainingSession;
  recorded: boolean;
  feedbackVisible: boolean;
  decision: TrainingDecision;
}

export interface CreateSessionInput {
  scenarioId: string;
  nodeIds?: string[];
  heroPositions: Array<"SB" | "BB">;
  targetDecisions: number;
  feedbackMode: FeedbackMode;
  rngEnabled: boolean;
  acknowledgeApproximate: boolean;
}

export interface DecisionReplayResponse {
  session: TrainingSession;
  decision: TrainingDecision;
  assumptions: Assumptions;
}
