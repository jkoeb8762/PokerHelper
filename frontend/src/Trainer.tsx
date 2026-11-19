import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  completeTrainingSession,
  createTrainingSession,
  deleteTrainingSession,
  getDecisionReplay,
  getScenario,
  getScenarios,
  getTrainingPrompt,
  getTrainingSession,
  getTrainingSessions,
  getTrainingStatistics,
  redrillTrainingSession,
  repeatTrainingSession,
  showTrainingRng,
  submitTrainingDecision,
} from "./api";
import { Shell } from "./Shell";
import type {
  FeedbackMode,
  FeedbackSeverity,
  RngMapping,
  SubmissionResponse,
  TrainingDecision,
  TrainingPrompt,
  TrainingSession,
  TrainingSummary,
} from "./types";


export function TrainerSetup() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const scenarios = useQuery({ queryKey: ["scenarios"], queryFn: getScenarios });
  const requestedScenario = searchParams.get("scenario") ?? "";
  const [scenarioChoice, setScenarioChoice] = useState(requestedScenario);
  const scenarioId = scenarioChoice || scenarios.data?.items[0]?.scenarioId || "";
  const scenario = useQuery({
    queryKey: ["scenario", scenarioId],
    queryFn: () => getScenario(scenarioId),
    enabled: Boolean(scenarioId),
  });
  const requestedNode = searchParams.get("node") ?? "ALL";
  const [position, setPosition] = useState<"ALL" | "SB" | "BB">("ALL");
  const [nodeId, setNodeId] = useState(requestedNode);
  const [target, setTarget] = useState(20);
  const [feedbackMode, setFeedbackMode] = useState<FeedbackMode>("IMMEDIATE");
  const [rngEnabled, setRngEnabled] = useState(true);
  const [acknowledged, setAcknowledged] = useState(false);

  const availableNodes = useMemo(
    () => scenario.data?.nodes.filter((node) => position === "ALL" || node.actor === position) ?? [],
    [scenario.data, position],
  );
  useEffect(() => {
    if (scenario.data && nodeId !== "ALL" && !availableNodes.some((node) => node.nodeId === nodeId)) setNodeId("ALL");
  }, [availableNodes, nodeId, scenario.data]);

  const create = useMutation({
    mutationFn: createTrainingSession,
    onSuccess: (session) => navigate(`/train/session/${encodeURIComponent(session.sessionId)}`),
  });

  function start(event: React.FormEvent) {
    event.preventDefault();
    if (!scenario.data) return;
    const selectedNode = nodeId === "ALL" ? undefined : availableNodes.find((node) => node.nodeId === nodeId);
    create.mutate({
      scenarioId: scenario.data.scenarioId,
      nodeIds: nodeId === "ALL" ? availableNodes.map((node) => node.nodeId) : [nodeId],
      heroPositions: selectedNode ? [selectedNode.actor] : position === "ALL" ? ["SB", "BB"] : [position],
      targetDecisions: target,
      feedbackMode,
      rngEnabled,
      acknowledgeApproximate: scenario.data.accuracyMode === "CERTIFIED" || acknowledged,
    });
  }

  return (
    <Shell>
      <section className="trainer-hero">
        <div>
          <p className="eyebrow">Phase 3 · deliberate practice</p>
          <h1>Build a repeatable decision habit.</h1>
          <p>Choose the positions and branches you want to practice. Every deal keeps its exact suits, solution version, and scoring snapshot.</p>
        </div>
        <div className="trainer-principle"><strong>Frequency is context.</strong><span>EV loss sets the review priority.</span></div>
      </section>
      <section className="trainer-setup content-section">
        <form onSubmit={start} className="setup-card">
          <div className="section-heading"><div><p className="eyebrow">Session setup</p><h2>Choose your drill</h2></div><span className="integrity-chip">Offline · locally saved</span></div>
          {scenarios.isPending && <TrainerLoading label="Loading validated scenarios…" />}
          {scenarios.isError && <TrainerError message={scenarios.error.message} />}
          {scenarios.data && <div className="setup-grid">
            <fieldset>
              <legend>Scenario</legend>
              <label>Solution pack
                <select value={scenarioId} onChange={(event) => { setScenarioChoice(event.target.value); setNodeId("ALL"); }}>
                  {scenarios.data.items.map((item) => <option key={item.scenarioId} value={item.scenarioId}>{item.title}</option>)}
                </select>
              </label>
              <div className="radio-field">
                <span>Hero position</span>
                {(["ALL", "SB", "BB"] as const).map((item) => (
                  <label key={item}><input type="radio" name="position" checked={position === item} onChange={() => setPosition(item)} />{item === "ALL" ? "Mix SB + BB" : item}</label>
                ))}
              </div>
              <label>Action sequence
                <select value={nodeId} onChange={(event) => setNodeId(event.target.value)}>
                  <option value="ALL">All {availableNodes.length} matching decisions</option>
                  {availableNodes.map((node) => <option key={node.nodeId} value={node.nodeId}>{node.actor} · {historyLabel(node.actionHistory)}</option>)}
                </select>
              </label>
            </fieldset>
            <fieldset>
              <legend>Practice format</legend>
              <label>Session length
                <select value={target} onChange={(event) => setTarget(Number(event.target.value))}>
                  {[5, 10, 20, 50].map((value) => <option key={value} value={value}>{value} decisions</option>)}
                </select>
              </label>
              <div className="radio-field">
                <span>Feedback</span>
                <label><input type="radio" name="feedback" checked={feedbackMode === "IMMEDIATE"} onChange={() => setFeedbackMode("IMMEDIATE")} />Immediate after each choice</label>
                <label><input type="radio" name="feedback" checked={feedbackMode === "DELAYED"} onChange={() => setFeedbackMode("DELAYED")} />Delayed until review</label>
              </div>
              <label className="check-field"><input type="checkbox" checked={rngEnabled} onChange={(event) => setRngEnabled(event.target.checked)} /><span><strong>Enable optional RNG aid</strong><small>Shows a 1–100 roll and mapping only when requested. It never chooses an action.</small></span></label>
            </fieldset>
          </div>}
          {scenario.data?.accuracyMode === "REFERENCE_MODEL" && (
            <div className="reference-consent" role="note">
              <strong>Approximate reference-model practice</strong>
              <p>This source is rake-free and uses an approximate postflop continuation model. EV loss is reproducible relative to this exact solution, not a universal claim about real-game GTO.</p>
              <label><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} />I understand how this practice feedback is scoped.</label>
            </div>
          )}
          {create.isError && <p className="inline-error" role="alert">{create.error.message}</p>}
          <div className="setup-actions">
            <Link className="outline-button" to={scenario.data ? `/study/${scenario.data.scenarioId}/${scenario.data.rootNodeId}` : "/"}>Study before training</Link>
            <button className="primary-button" disabled={!scenario.data || create.isPending || (scenario.data.accuracyMode === "REFERENCE_MODEL" && !acknowledged)}>
              {create.isPending ? "Creating session…" : `Start ${target}-decision session`}
            </button>
          </div>
        </form>
      </section>
    </Shell>
  );
}


export function TrainingRoom() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [submission, setSubmission] = useState<SubmissionResponse | null>(null);
  const session = useQuery({ queryKey: ["training-session", sessionId], queryFn: () => getTrainingSession(sessionId), enabled: Boolean(sessionId) });
  const prompt = useQuery({
    queryKey: ["training-prompt", sessionId],
    queryFn: () => getTrainingPrompt(sessionId),
    enabled: Boolean(sessionId && session.data?.status === "ACTIVE" && !submission),
  });
  const submit = useMutation({
    mutationFn: ({ promptId, optionId }: { promptId: string; optionId: string }) => submitTrainingDecision(sessionId, promptId, optionId),
    onSuccess: async (result) => {
      setSubmission(result);
      await queryClient.invalidateQueries({ queryKey: ["training-session", sessionId] });
    },
  });
  const rng = useMutation({
    mutationFn: () => showTrainingRng(sessionId),
    onSuccess: (result) => queryClient.setQueryData<TrainingPrompt>(["training-prompt", sessionId], (current) => current ? { ...current, rngRoll: result.roll, rngMapping: result.mapping } : current),
  });
  const end = useMutation({
    mutationFn: () => completeTrainingSession(sessionId),
    onSuccess: (result) => navigate(`/sessions/${encodeURIComponent(result.sessionId)}`),
  });

  async function next() {
    setSubmission(null);
    queryClient.removeQueries({ queryKey: ["training-prompt", sessionId] });
    await queryClient.invalidateQueries({ queryKey: ["training-session", sessionId] });
  }

  if (session.isError) return <Shell><TrainerError message={session.error.message} /></Shell>;
  if (!session.data) return <Shell><TrainerLoading label="Opening local training session…" /></Shell>;
  if (submission?.feedbackVisible && submission.decision.referenceSnapshot) {
    return <Shell><DecisionFeedback decision={submission.decision} session={submission.session} onNext={submission.session.status === "ACTIVE" ? next : undefined} /></Shell>;
  }
  if (submission && !submission.feedbackVisible) {
    return <Shell><RecordedDecision submission={submission} onNext={submission.session.status === "ACTIVE" ? next : undefined} /></Shell>;
  }
  if (session.data.status !== "ACTIVE") {
    return <Shell><section className="completion-state"><p className="eyebrow">Session saved</p><h1>{session.data.status === "COMPLETED" ? "Practice complete." : "Session ended."}</h1><p>Review the exact decisions and source-model feedback whenever you are ready.</p><Link className="primary-button" to={`/sessions/${encodeURIComponent(sessionId)}`}>Open session review</Link></section></Shell>;
  }
  if (prompt.isError) return <Shell><TrainerError message={prompt.error.message} /></Shell>;
  if (!prompt.data) return <Shell><TrainerLoading label="Dealing an exact range-weighted combo…" /></Shell>;

  const current = prompt.data;
  return (
    <Shell>
      <section className="trainer-toolbar">
        <div><p className="eyebrow">{session.data.drillType.replaceAll("_", " ")}</p><h1>{current.heroPosition} decision</h1></div>
        <div className="hand-progress"><strong>Decision {current.sequence} of {current.targetDecisions}</strong><span>{session.data.feedbackMode === "IMMEDIATE" ? "Immediate feedback" : "Delayed feedback"}</span></div>
      </section>
      <div className="trainer-context">
        <span>{historyLabel(current.actionHistory)} · {current.heroPosition} to act</span>
        <dl><div><dt>Pot</dt><dd>{current.potBb} BB</dd></div><div><dt>To call</dt><dd>{current.amountToCallBb} BB</dd></div><div><dt>Behind</dt><dd>{current.actorStackBehindBb} BB</dd></div></dl>
      </div>
      <section className="decision-stage" aria-labelledby="decision-hand">
        <div className="accuracy-ribbon"><strong>{current.accuracyMode === "REFERENCE_MODEL" ? "Reference-model practice" : "Accuracy-certified solution"}</strong><span>{current.solutionVersion}</span></div>
        <p className="eyebrow">Your exact combo</p>
        <h2 id="decision-hand" className="sr-only">{current.heroCombo}</h2>
        <ExactCards combo={current.heroCombo} />
        <strong className="combo-code">{current.heroCombo} <span>· {current.groupedHand}</span></strong>
        <div className="decision-actions" aria-label="Available actions">
          {current.offeredOptions.map((option) => (
            <button key={option.actionId} disabled={submit.isPending} onClick={() => submit.mutate({ promptId: current.promptId, optionId: option.actionId })}>
              {option.label}{option.isAllIn && <small>All-in</small>}
            </button>
          ))}
        </div>
        <div className="decision-utilities">
          {current.rngAvailable && <button className="text-button" disabled={rng.isPending} onClick={() => rng.mutate()}>{current.rngRoll ? "RNG shown" : "Show optional RNG"}</button>}
          <button className="text-button danger-text" disabled={end.isPending} onClick={() => { if (window.confirm("End this session and keep completed decisions?")) end.mutate(); }}>End session</button>
        </div>
        {current.rngRoll && current.rngMapping && <RngAid roll={current.rngRoll} mapping={current.rngMapping} />}
        {(submit.isError || rng.isError || end.isError) && <p className="inline-error" role="alert">{submit.error?.message ?? rng.error?.message ?? end.error?.message}</p>}
      </section>
    </Shell>
  );
}


function RecordedDecision({ submission, onNext }: { submission: SubmissionResponse; onNext?: () => void }) {
  return <section className="recorded-state"><div className="recorded-check" aria-hidden="true">✓</div><p className="eyebrow">Decision {submission.decision.sequence} recorded</p><h1>{submission.decision.heroCombo} is saved.</h1><p>Feedback is delayed for this session. The immutable strategy snapshot and EV calculation will appear in review.</p>{onNext ? <button className="primary-button" onClick={onNext}>Deal next combo</button> : <Link className="primary-button" to={`/sessions/${encodeURIComponent(submission.session.sessionId)}`}>Review completed session</Link>}</section>;
}


function DecisionFeedback({ decision, session, onNext }: { decision: TrainingDecision; session: TrainingSession; onNext?: () => void }) {
  const selected = decision.referenceSnapshot?.find((item) => item.optionId === decision.selectedOptionId);
  const highest = decision.referenceSnapshot?.find((item) => item.optionId === decision.highestEvOptionId);
  const labels = Object.fromEntries((decision.offeredOptions ?? []).map((option) => [option.actionId, option.label]));
  return (
    <section className="feedback-page">
      <header className={`feedback-hero severity-${decision.feedbackSeverity?.toLowerCase()}`}>
        <div><p className="eyebrow">{decision.heroCombo} · You chose {labels[decision.selectedOptionId] ?? decision.selectedOptionId}</p><h1>{severityLabel(decision.feedbackSeverity)}</h1><p>{decision.interpretation}</p></div>
        <div className="loss-callout"><span>Source-model EV loss</span><strong>{formatLoss(decision.evLossBb)}</strong></div>
      </header>
      <div className="feedback-grid">
        <div className="feedback-main">
          <div className="feedback-cards"><ExactCards combo={decision.heroCombo} /><div><strong>{decision.groupedHand}</strong><span>Exact suits retained</span></div></div>
          <table className="feedback-table">
            <caption>Reference frequencies and decision-point action EVs</caption>
            <thead><tr><th>Action</th><th>Reference mix</th><th>Action EV</th><th>Result</th></tr></thead>
            <tbody>{decision.referenceSnapshot?.map((item) => <tr key={item.optionId} className={item.optionId === decision.selectedOptionId ? "chosen-row" : ""}><th>{labels[item.optionId] ?? item.optionId}</th><td>{percent(item.frequency)}</td><td>{signedBb(item.actionEvBb)}</td><td>{item.optionId === decision.selectedOptionId ? "Your choice" : item.optionId === decision.highestEvOptionId ? "Highest EV" : ""}</td></tr>)}</tbody>
          </table>
          {selected && highest && <div className="calculation-box"><span>Exact calculation</span><strong>{highest.actionEvBb} − {selected.actionEvBb} = {decision.evLossBb} BB</strong><small>Calculated before display rounding under scoring policy {decision.scoringPolicyVersion}.</small></div>}
        </div>
        <aside className="feedback-aside">
          <p className="eyebrow">Why this result is reproducible</p>
          <dl><div><dt>Solution</dt><dd>{decision.solutionVersion}</dd></div><div><dt>Mode</dt><dd>{decision.accuracyMode === "REFERENCE_MODEL" ? "Approximate reference model" : "Certified"}</dd></div><div><dt>Combo reach</dt><dd>{percent(decision.comboReachWeight ?? "0")}</dd></div><div><dt>Node</dt><dd>{decision.nodeId}</dd></div></dl>
          <p>Frequencies describe the mix. EV loss—not rarity—determines the severity label.</p>
          {decision.rngRoll && <p className="rng-record">RNG shown during decision: <strong>{decision.rngRoll}</strong></p>}
          <Link to={`/study/${encodeURIComponent(decision.scenarioId ?? session.scenarioId)}/${encodeURIComponent(decision.nodeId ?? session.selectedNodeIds[0])}?combo=${encodeURIComponent(decision.heroCombo)}`}>Review this exact combo in Study</Link>
        </aside>
      </div>
      <div className="feedback-footer"><Link className="outline-button" to={`/sessions/${encodeURIComponent(session.sessionId)}`}>Session review</Link>{onNext ? <button className="primary-button" onClick={onNext}>Deal next combo</button> : <Link className="primary-button" to={`/sessions/${encodeURIComponent(session.sessionId)}`}>Review completed session</Link>}</div>
    </section>
  );
}


export function SessionHistory() {
  const sessions = useQuery({ queryKey: ["training-sessions"], queryFn: getTrainingSessions });
  const statistics = useQuery({ queryKey: ["training-statistics"], queryFn: getTrainingStatistics });
  return (
    <Shell>
      <section className="review-header"><div><p className="eyebrow">Local training history</p><h1>Review what costs EV.</h1><p>Every result remains tied to its exact combo, action sequence, and immutable solution version.</p></div><Link className="primary-button" to="/train">Start a new session</Link></section>
      {statistics.data && <StatisticsOverview summary={statistics.data} />}
      <section className="session-list content-section">
        <div className="section-heading"><div><p className="eyebrow">Saved locally</p><h2>Training sessions</h2></div><span>{sessions.data?.items.length ?? 0} sessions</span></div>
        {(sessions.isPending || statistics.isPending) && <TrainerLoading label="Loading local history…" />}
        {sessions.isError && <TrainerError message={sessions.error.message} />}
        {sessions.data?.items.length === 0 && <div className="empty-card"><h3>No sessions yet</h3><p>A session stores exact dealt cards, your choices, solution references, and reproducible feedback.</p><Link to="/train">Create the first drill</Link></div>}
        <div className="session-cards">{sessions.data?.items.map((session) => <Link key={session.sessionId} to={`/sessions/${encodeURIComponent(session.sessionId)}`} className="session-card"><div><span className={`status-pill status-${session.status.toLowerCase()}`}>{session.status.toLowerCase()}</span><span>{session.drillType.replaceAll("_", " ").toLowerCase()}</span></div><h3>{session.heroPositions.join(" + ")} · {session.summary.decisionsCompleted} decisions</h3><dl><div><dt>Total loss</dt><dd>{formatBb(session.summary.totalEvLossBb, 2)}</dd></div><div><dt>Average</dt><dd>{formatBb(session.summary.averageEvLossBb, 3)}/decision</dd></div><div><dt>Solution</dt><dd>{session.solutionVersion}</dd></div></dl><small>{new Date(session.startedAt).toLocaleString()}</small></Link>)}</div>
      </section>
    </Shell>
  );
}


function StatisticsOverview({ summary }: { summary: TrainingSummary }) {
  return <section className="stats-overview" aria-label="All-time training statistics"><div><span>Decisions</span><strong>{summary.decisionsCompleted}</strong></div><div><span>Total EV loss</span><strong>{formatBb(summary.totalEvLossBb, 2)}</strong></div><div><span>Average loss</span><strong>{formatBb(summary.averageEvLossBb, 3)}<small>/decision</small></strong></div><div><span>EV loss / 100 decisions</span><strong>{formatBb(summary.evLossPer100DecisionsBb, 2)}</strong></div></section>;
}


export function SessionReview() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [severity, setSeverity] = useState("ALL");
  const [sort, setSort] = useState("LOSS");
  const session = useQuery({ queryKey: ["training-session", sessionId], queryFn: () => getTrainingSession(sessionId), enabled: Boolean(sessionId) });
  const launch = useMutation({
    mutationFn: (kind: "REPEAT" | "MISTAKES" | "CLOSE_DECISIONS") => kind === "REPEAT" ? repeatTrainingSession(sessionId) : redrillTrainingSession(sessionId, kind),
    onSuccess: (created) => navigate(`/train/session/${encodeURIComponent(created.sessionId)}`),
  });
  const remove = useMutation({
    mutationFn: () => deleteTrainingSession(sessionId),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["training-sessions"] }); navigate("/sessions"); },
  });
  const decisions = useMemo(() => {
    const source = session.data?.decisions ?? [];
    const filtered = severity === "ALL" ? source : source.filter((item) => item.feedbackSeverity === severity);
    return [...filtered].sort((a, b) => sort === "LOSS" ? Number(b.evLossBb ?? -1) - Number(a.evLossBb ?? -1) : a.sequence - b.sequence);
  }, [session.data, severity, sort]);

  if (session.isError) return <Shell><TrainerError message={session.error.message} /></Shell>;
  if (!session.data) return <Shell><TrainerLoading label="Recalculating immutable session summary…" /></Shell>;
  const detail = session.data;
  const priority = detail.decisions.filter((item) => item.evLossBb !== undefined).sort((a, b) => Number(b.evLossBb) - Number(a.evLossBb)).slice(0, 3);
  return (
    <Shell>
      <section className="session-review-header"><div><Link className="back-link" to="/sessions">All sessions</Link><p className="eyebrow">{detail.status.toLowerCase()} · {detail.drillType.replaceAll("_", " ").toLowerCase()}</p><h1>{detail.heroPositions.join(" + ")} practice review</h1><p>{detail.solutionVersion} · {detail.accuracyMode === "REFERENCE_MODEL" ? "reference-model EV" : "certified EV"}</p></div><div className="review-actions"><button className="outline-button" onClick={() => launch.mutate("REPEAT")}>Repeat selection</button><button className="primary-button" disabled={!detail.decisions.length} onClick={() => launch.mutate("MISTAKES")}>Redrill mistakes</button></div></section>
      <StatisticsOverview summary={detail.summary} />
      <div className="review-layout">
        <aside className="priority-panel"><p className="eyebrow">Priority review</p><h2>Most costly choices</h2>{priority.length ? <ol>{priority.map((item) => <li key={item.decisionId}><Link to={`/sessions/${encodeURIComponent(sessionId)}/decisions/${encodeURIComponent(item.decisionId)}`}><strong>{item.heroCombo}</strong><span>{formatLoss(item.evLossBb)} · {severityLabel(item.feedbackSeverity)}</span></Link></li>)}</ol> : <p>No scored decisions yet.</p>}<button className="outline-button" disabled={!detail.decisions.length} onClick={() => launch.mutate("CLOSE_DECISIONS")}>Practice close mixes</button></aside>
        <section className="decision-history"><div className="history-controls"><div><p className="eyebrow">Decision history</p><h2>Exact hands and choices</h2></div><label>Filter <select value={severity} onChange={(event) => setSeverity(event.target.value)}><option value="ALL">All severities</option>{severityOptions.map((item) => <option key={item} value={item}>{severityLabel(item)}</option>)}</select></label><label>Sort <select value={sort} onChange={(event) => setSort(event.target.value)}><option value="LOSS">EV loss</option><option value="SEQUENCE">Decision order</option></select></label></div>
          <div className="table-scroll"><table className="history-table"><thead><tr><th>#</th><th>Exact combo</th><th>Position</th><th>Choice</th><th>EV loss</th><th>Result</th></tr></thead><tbody>{decisions.map((item) => <tr key={item.decisionId}><td>{item.sequence}</td><th><Link to={`/sessions/${encodeURIComponent(sessionId)}/decisions/${encodeURIComponent(item.decisionId)}`}>{item.heroCombo}<small>{item.groupedHand}</small></Link></th><td>{item.heroPosition ?? "—"}</td><td>{optionLabel(item, item.selectedOptionId)}</td><td>{item.evLossBb === undefined ? "After session" : formatLoss(item.evLossBb)}</td><td>{item.feedbackSeverity ? severityLabel(item.feedbackSeverity) : "Feedback delayed"}</td></tr>)}</tbody></table></div>
        </section>
      </div>
      <section className="breakdown-section"><div><p className="eyebrow">Grouped results</p><h2>Where the loss came from</h2></div><Breakdown title="By position" items={detail.summary.byPosition} /><Breakdown title="By action sequence" items={detail.summary.byActionSequence.slice(0, 6)} />{detail.summary.frequencyCalibration.buckets.length ? <Calibration summary={detail.summary} /> : <div className="calibration-empty"><strong>Frequency calibration unlocks at {detail.summary.frequencyCalibration.minimumSample} comparable decisions.</strong><span>Comparable means the same scenario, solution, node, grouped hand, and action set.</span></div>}</section>
      <section className="data-controls"><div><strong>Local data control</strong><span>Deleting this session transactionally removes its decisions and cached summary from the configured local data directory.</span></div><button className="danger-button" onClick={() => { if (window.confirm("Permanently delete this local training session?")) remove.mutate(); }}>Delete session</button></section>
      {(launch.isError || remove.isError) && <p className="inline-error" role="alert">{launch.error?.message ?? remove.error?.message}</p>}
    </Shell>
  );
}


function Breakdown({ title, items }: { title: string; items: TrainingSummary["byPosition"] }) {
  return <div className="breakdown-card"><h3>{title}</h3>{items.length ? <table><thead><tr><th>Group</th><th>n</th><th>Total</th><th>Average</th></tr></thead><tbody>{items.map((item) => <tr key={item.key}><th>{item.key}</th><td>{item.decisions}</td><td>{formatBb(item.totalEvLossBb, 2)}</td><td>{formatBb(item.averageEvLossBb, 3)}</td></tr>)}</tbody></table> : <p>No decisions yet.</p>}</div>;
}


function Calibration({ summary }: { summary: TrainingSummary }) {
  return <div className="calibration-card"><h3>Frequency calibration</h3>{summary.frequencyCalibration.buckets.map((bucket) => <div key={`${bucket.nodeId}-${bucket.groupedHand}`}><strong>{bucket.groupedHand} · {bucket.nodeId} · n={bucket.sampleSize}</strong><ul>{bucket.actions.map((action) => <li key={action.optionId}><span>{action.optionId}</span><span>Observed {percent(action.observedFrequency)}</span><span>Reference {percent(action.referenceFrequency)}</span><span>{signedPp(action.deviationPp)}</span></li>)}</ul></div>)}</div>;
}


export function DecisionReplay() {
  const { sessionId = "", decisionId = "" } = useParams();
  const replay = useQuery({ queryKey: ["decision-replay", sessionId, decisionId], queryFn: () => getDecisionReplay(sessionId, decisionId), enabled: Boolean(sessionId && decisionId) });
  if (replay.isError) return <Shell><TrainerError message={replay.error.message} /></Shell>;
  if (!replay.data) return <Shell><TrainerLoading label="Loading immutable decision snapshot…" /></Shell>;
  return <Shell><div className="replay-banner"><Link to={`/sessions/${encodeURIComponent(sessionId)}`}>Back to session review</Link><span>Immutable replay · answered {new Date(replay.data.decision.answeredAt).toLocaleString()}</span></div><DecisionFeedback decision={replay.data.decision} session={replay.data.session} /></Shell>;
}


function RngAid({ roll, mapping }: { roll: number; mapping: RngMapping[] }) {
  const selected = mapping.find((item) => roll >= item.start && roll <= item.end);
  return <div className="rng-aid" role="note"><div><span>Independent study roll</span><strong>{roll}</strong></div><p>{mapping.map((item) => <span className={item === selected ? "rng-hit" : ""} key={item.optionId}>{item.start}–{item.end} {item.label}</span>)}</p><small>The roll never submits an action.</small></div>;
}


function ExactCards({ combo }: { combo: string }) {
  return <div className="trainer-cards" aria-label={combo}>{[combo.slice(0, 2), combo.slice(2, 4)].map((card) => <span className={`trainer-card suit-${card[1]}`} key={card}><strong>{card[0]}</strong><i>{{ s: "♠", h: "♥", d: "♦", c: "♣" }[card[1]]}</i></span>)}</div>;
}


function TrainerLoading({ label }: { label: string }) { return <div className="loading-state" role="status"><span className="spinner" />{label}</div>; }
function TrainerError({ message }: { message: string }) { return <div className="error-state" role="alert"><strong>Trainer unavailable</strong><span>{message}</span><Link to="/train">Return to training setup</Link></div>; }

const severityOptions: FeedbackSeverity[] = ["NO_MATERIAL_EV_LOSS", "SMALL_EV_LOSS", "SIGNIFICANT_MISTAKE", "MAJOR_MISTAKE"];
function severityLabel(value?: FeedbackSeverity) { return ({ NO_MATERIAL_EV_LOSS: "No material EV loss", SMALL_EV_LOSS: "Small EV loss", SIGNIFICANT_MISTAKE: "Significant mistake", MAJOR_MISTAKE: "Major mistake" } as Record<string, string>)[value ?? ""] ?? "Feedback recorded"; }
function historyLabel(history: Array<{ actor: string; label?: string; type: string }>) { return history.length ? history.map((item) => `${item.actor} ${item.label ?? item.type.toLowerCase()}`).join(" · ") : "Opening decision"; }
function percent(value: string) { return `${(Number(value) * 100).toFixed(1)}%`; }
function signedBb(value: string) { const number = Number(value); return `${number >= 0 ? "+" : ""}${number.toFixed(3)} BB`; }
function signedPp(value: string) { const number = Number(value); return `${number >= 0 ? "+" : ""}${number.toFixed(1)} pp`; }
function formatLoss(value?: string) { if (value === undefined) return "Pending"; const number = Number(value); return number > 0 && number < .001 ? "<0.001 BB" : `${number.toFixed(3)} BB`; }
function formatBb(value: string, places: number) { return `${Number(value).toFixed(places)} BB`; }
function optionLabel(decision: TrainingDecision, optionId: string) { return decision.offeredOptions?.find((item) => item.actionId === optionId)?.label ?? optionId; }
