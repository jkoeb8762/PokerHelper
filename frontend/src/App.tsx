import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, NavLink, Route, Routes, useParams, useSearchParams } from "react-router-dom";
import { getAssumptions, getNode, getScenario, getScenarios } from "./api";
import type { ActionOption, Assumptions, GroupStrategy, ScenarioDetail, SolutionNode } from "./types";

const RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"];
const ACTION_COLORS = ["#d36b5e", "#61a7a2", "#e5af54", "#8f7ec1"];

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" to="/" aria-label="PokerHelper home">
          <span className="brand-mark" aria-hidden="true">PH</span>
          <span><strong>PokerHelper</strong><small>Local study lab</small></span>
        </Link>
        <nav aria-label="Primary navigation">
          <NavLink to="/" end>Study</NavLink>
          <span className="nav-disabled" title="Planned for Phase 3">Train <em>soon</em></span>
        </nav>
        <div className="local-status"><span aria-hidden="true" /> Local · v0.2</div>
      </header>
      <main id="main-content">{children}</main>
      <footer>Built for deliberate, post-session study. No live-table integration.</footer>
    </div>
  );
}

function ScenarioSelection() {
  const scenarios = useQuery({ queryKey: ["scenarios"], queryFn: getScenarios });
  return (
    <Shell>
      <section className="hero-panel">
        <p className="eyebrow">Phase 2 · Study browser</p>
        <h1>Start with the decision tree.</h1>
        <p>Walk every supported branch, inspect the full range, then drop down to the exact suits behind each mix.</p>
      </section>
      <section className="content-section" aria-labelledby="available-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Validated packs</p><h2 id="available-heading">Available situations</h2></div>
          <span className="integrity-chip">SHA-256 verified</span>
        </div>
        {scenarios.isPending && <Loading label="Loading local solution catalog…" />}
        {scenarios.isError && <ErrorState message={scenarios.error.message} />}
        {scenarios.data?.items.length === 0 && <ErrorState message="No validated solution packs are installed." />}
        <div className="scenario-grid">
          {scenarios.data?.items.map((scenario) => (
            <article className="scenario-card" key={scenario.scenarioId}>
              <div className="card-topline"><span>NLHE · CASH</span><span>{scenario.nodeCount} nodes</span></div>
              <h3>{scenario.title}</h3>
              <p>Six-max table after four folds. Explore the complete SB and BB branch set.</p>
              <dl className="scenario-facts">
                <div><dt>Stack</dt><dd>{scenario.game.effectiveStackBb} BB</dd></div>
                <div><dt>Blinds</dt><dd>{scenario.game.smallBlindBb}/{scenario.game.bigBlindBb}</dd></div>
                <div><dt>Rake</dt><dd>{Number(scenario.game.rake.rate) === 0 ? "No rake" : `${Number(scenario.game.rake.rate) * 100}%`}</dd></div>
              </dl>
              {!scenario.trainerEligible && <p className="study-badge">Study-only approximate model</p>}
              <Link className="primary-button" to={`/study/${scenario.scenarioId}/${scenario.rootNodeId}`}>Open study browser <span aria-hidden="true">→</span></Link>
              <small className="version-note">{scenario.solutionVersion}</small>
            </article>
          ))}
        </div>
      </section>
    </Shell>
  );
}

function StudyView() {
  const { scenarioId = "", nodeId = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [assumptionsOpen, setAssumptionsOpen] = useState(false);
  const scenario = useQuery({ queryKey: ["scenario", scenarioId], queryFn: () => getScenario(scenarioId), enabled: Boolean(scenarioId) });
  const solutionId = scenario.data?.solutionId ?? "";
  const node = useQuery({ queryKey: ["node", solutionId, nodeId], queryFn: () => getNode(solutionId, nodeId), enabled: Boolean(solutionId && nodeId) });
  const assumptions = useQuery({ queryKey: ["assumptions", solutionId], queryFn: () => getAssumptions(solutionId), enabled: Boolean(solutionId && assumptionsOpen) });

  if (scenario.isError) return <Shell><ErrorState message={scenario.error.message} /></Shell>;
  if (node.isError) return <Shell><ErrorState message={node.error.message} /></Shell>;
  if (!scenario.data || !node.data) return <Shell><Loading label="Validating and loading strategy node…" /></Shell>;

  const requestedCombo = searchParams.get("combo");
  const availableCombos = Object.keys(node.data.exactCombos);
  const exactCombo = requestedCombo && node.data.exactCombos[requestedCombo]
    ? requestedCombo
    : node.data.exactCombos.AsAh ? "AsAh" : availableCombos[0];
  const selectedGroup = node.data.exactCombos[exactCombo].group;
  const selectCombo = (combo: string) => setSearchParams({ combo }, { replace: true });

  return (
    <Shell>
      <section className="study-header">
        <div>
          <Link className="back-link" to="/">← All situations</Link>
          <p className="eyebrow">{scenario.data.title}</p>
          <h1>{node.data.actor} to act <span>· {historyTitle(node.data)}</span></h1>
        </div>
        <button className="secondary-button" onClick={() => setAssumptionsOpen(true)}>Assumptions & provenance</button>
      </section>
      <ContextStrip scenario={scenario.data} node={node.data} />
      {!scenario.data.trainerEligible && (
        <div className="model-warning" role="note">
          <strong>Approximate study model</strong>
          <span>This pack reproduces its source exactly, but it does not solve postflop play or rake and is not approved for EV-loss grading.</span>
        </div>
      )}
      <div className="study-layout">
        <aside className="tree-panel" aria-label="Decision tree">
          <p className="eyebrow">Action tree</p>
          <h2>All decision nodes</h2>
          <NodeTree scenario={scenario.data} currentNodeId={node.data.nodeId} exactCombo={exactCombo} />
        </aside>
        <section className="range-panel" aria-labelledby="range-heading">
          <div className="panel-heading">
            <div><p className="eyebrow">Grouped range</p><h2 id="range-heading">169 starting hands</h2></div>
            <span>{node.data.actor} reach-weighted</span>
          </div>
          <RangeMatrix node={node.data} selectedGroup={selectedGroup} onSelectGroup={(group) => {
            const first = Object.keys(node.data.exactCombos).find((combo) => node.data.exactCombos[combo].group === group);
            if (first) selectCombo(first);
          }} />
          <ActionLegend actions={node.data.actions} />
        </section>
        <aside className="detail-panel" aria-labelledby="hand-heading">
          <HandDetail node={node.data} exactCombo={exactCombo} onSelectCombo={selectCombo} />
          <BranchActions scenarioId={scenarioId} node={node.data} exactCombo={exactCombo} />
        </aside>
      </div>
      {assumptionsOpen && (
        <AssumptionsPanel
          assumptions={assumptions.data}
          loading={assumptions.isPending}
          onClose={() => setAssumptionsOpen(false)}
        />
      )}
    </Shell>
  );
}

function ContextStrip({ scenario, node }: { scenario: ScenarioDetail; node: SolutionNode }) {
  const rake = Number(scenario.game.rake.rate);
  return (
    <dl className="context-strip" aria-label="Current game assumptions">
      <div><dt>Effective stack</dt><dd>{scenario.game.effectiveStackBb} BB</dd></div>
      <div><dt>Blinds</dt><dd>{scenario.game.smallBlindBb} / {scenario.game.bigBlindBb} BB</dd></div>
      <div><dt>Pot</dt><dd>{node.potBb} BB</dd></div>
      <div><dt>To call</dt><dd>{node.amountToCallBb} BB</dd></div>
      <div><dt>{node.actor} behind</dt><dd>{node.actorStackBehindBb} BB</dd></div>
      <div><dt>Rake model</dt><dd>{rake === 0 ? "No rake" : `${rake * 100}% · cap ${scenario.game.rake.capBb}`}</dd></div>
      <div className="version-context"><dt>Solution</dt><dd>{scenario.solutionVersion}</dd></div>
    </dl>
  );
}

function NodeTree({ scenario, currentNodeId, exactCombo }: { scenario: ScenarioDetail; currentNodeId: string; exactCombo: string }) {
  return (
    <ol className="node-list">
      {scenario.nodes.map((node, index) => (
        <li key={node.nodeId}>
          <Link className={node.nodeId === currentNodeId ? "active" : ""} to={`/study/${scenario.scenarioId}/${node.nodeId}?combo=${encodeURIComponent(exactCombo)}`}>
            <span className="node-index">{String(index + 1).padStart(2, "0")}</span>
            <span><strong>{node.actor} decision</strong><small>{historyTitle(node)}</small></span>
          </Link>
        </li>
      ))}
    </ol>
  );
}

function RangeMatrix({ node, selectedGroup, onSelectGroup }: { node: SolutionNode; selectedGroup: string; onSelectGroup: (group: string) => void }) {
  const buttonRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const groups = useMemo(() => RANKS.flatMap((rowRank, row) => RANKS.map((columnRank, column) => {
    if (row === column) return rowRank + columnRank;
    return column > row ? rowRank + columnRank + "s" : columnRank + rowRank + "o";
  })), []);

  function moveFocus(index: number, key: string) {
    const row = Math.floor(index / 13);
    const column = index % 13;
    let next = index;
    if (key === "ArrowRight") next = row * 13 + Math.min(12, column + 1);
    if (key === "ArrowLeft") next = row * 13 + Math.max(0, column - 1);
    if (key === "ArrowDown") next = Math.min(12, row + 1) * 13 + column;
    if (key === "ArrowUp") next = Math.max(0, row - 1) * 13 + column;
    buttonRefs.current[next]?.focus();
  }

  return (
    <div className="matrix-scroll" aria-label="Scrollable range matrix">
      <div className="range-matrix" role="grid" aria-label={`${node.actor} strategy by starting hand`}>
        {groups.map((group, index) => {
          const strategy = node.groupedHands[group];
          const description = frequencyDescription(node.actions, strategy);
          return (
            <button
              type="button"
              role="gridcell"
              aria-selected={group === selectedGroup}
              aria-label={`${group}: ${description}`}
              className={`range-cell ${group === selectedGroup ? "selected" : ""}`}
              key={group}
              ref={(element) => { buttonRefs.current[index] = element; }}
              onClick={() => onSelectGroup(group)}
              onKeyDown={(event) => {
                if (event.key.startsWith("Arrow")) {
                  event.preventDefault();
                  moveFocus(index, event.key);
                }
              }}
            >
              <span className="cell-fill" style={{ background: strategyBackground(node.actions, strategy) }} aria-hidden="true" />
              <strong>{group}</strong>
              <span className="cell-mix" aria-hidden="true">{dominantMix(node.actions, strategy)}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function HandDetail({ node, exactCombo, onSelectCombo }: { node: SolutionNode; exactCombo: string; onSelectCombo: (combo: string) => void }) {
  const strategy = node.exactCombos[exactCombo];
  const combos = Object.keys(node.exactCombos).filter((combo) => node.exactCombos[combo].group === strategy.group);
  return (
    <div>
      <p className="eyebrow">Selected exact combo</p>
      <div className="hand-title-row">
        <div><h2 id="hand-heading">{strategy.group}</h2><span>{strategy.reachFrequency === "1" ? "100% root reach" : `${percent(strategy.reachFrequency)} node reach`}</span></div>
        <div className="cards" aria-label={exactCombo}>{cardFace(exactCombo.slice(0, 2))}{cardFace(exactCombo.slice(2, 4))}</div>
      </div>
      <label className="combo-label">Exact suits
        <select value={exactCombo} onChange={(event) => onSelectCombo(event.target.value)}>
          {combos.map((combo) => <option key={combo} value={combo}>{prettyCombo(combo)} · {combo}</option>)}
        </select>
      </label>
      <table className="strategy-table">
        <caption>Action frequencies and decision-point EV for {exactCombo}</caption>
        <thead><tr><th>Action</th><th>Frequency</th><th>EV (BB)</th></tr></thead>
        <tbody>
          {node.actions.map((action, index) => (
            <tr key={action.actionId}>
              <th><span className="legend-dot" style={{ backgroundColor: ACTION_COLORS[index] }} />{action.label}</th>
              <td>{percent(strategy.frequencies[action.actionId])}</td>
              <td className={Number(strategy.evBb[action.actionId]) >= 0 ? "positive" : "negative"}>{signed(strategy.evBb[action.actionId])}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="ev-note">EV excludes chips already committed before this decision. Values preserve exact suits and blockers.</p>
    </div>
  );
}

function BranchActions({ scenarioId, node, exactCombo }: { scenarioId: string; node: SolutionNode; exactCombo: string }) {
  return (
    <div className="branch-section">
      <p className="eyebrow">Continue this branch</p>
      <div className="branch-actions">
        {node.actions.map((action) => {
          const child = node.childNodeByAction[action.actionId];
          return child ? (
            <Link key={action.actionId} to={`/study/${scenarioId}/${child}?combo=${encodeURIComponent(exactCombo)}`}>{action.label}<span>Next decision →</span></Link>
          ) : (
            <div className="terminal-action" key={action.actionId}><strong>{action.label}</strong><span>Branch ends preflop</span></div>
          );
        })}
      </div>
    </div>
  );
}

function ActionLegend({ actions }: { actions: ActionOption[] }) {
  return <div className="action-legend" aria-label="Strategy color legend">{actions.map((action, index) => <span key={action.actionId}><i style={{ backgroundColor: ACTION_COLORS[index] }} />{action.label}</span>)}</div>;
}

function AssumptionsPanel({ assumptions, loading, onClose }: { assumptions?: Assumptions; loading: boolean; onClose: () => void }) {
  useEffect(() => {
    const listener = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, [onClose]);
  return (
    <div className="drawer-scrim" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) onClose(); }}>
      <aside className="assumptions-drawer" role="dialog" aria-modal="true" aria-labelledby="assumptions-heading">
        <button className="drawer-close" onClick={onClose} aria-label="Close assumptions">×</button>
        <p className="eyebrow">Traceable inputs</p>
        <h2 id="assumptions-heading">Assumptions & provenance</h2>
        {loading && <Loading label="Loading provenance…" />}
        {assumptions && <>
          <dl className="assumption-list">
            <div><dt>Solution</dt><dd>{assumptions.version}</dd></div>
            <div><dt>Game</dt><dd>{assumptions.game.variant} · {assumptions.game.effectiveStackBb} BB · SB vs BB</dd></div>
            <div><dt>Blinds / ante</dt><dd>{assumptions.game.smallBlindBb}/{assumptions.game.bigBlindBb} BB · {assumptions.game.anteBb} ante</dd></div>
            <div><dt>Rake</dt><dd>{Number(assumptions.game.rake.rate) === 0 ? "None in source model" : assumptions.game.rake.policyVersion}</dd></div>
            <div><dt>Solver</dt><dd>{String(assumptions.solver.algorithm)} · {String(assumptions.solver.iterations)} iterations</dd></div>
            <div><dt>Source</dt><dd>{assumptions.source.name} @ {assumptions.source.commit.slice(0, 12)}</dd></div>
            <div><dt>License</dt><dd>{String(assumptions.authorization.license)} · redistribution permitted</dd></div>
            <div><dt>Exploitability</dt><dd>{(Number(assumptions.accuracy.exploitabilityBbPerHand) * 1000).toFixed(3)} mbb/hand inside source model</dd></div>
            <div><dt>EV baseline</dt><dd>{String(assumptions.solver.evBaseline)}</dd></div>
          </dl>
          <h3>Known limitations</h3>
          <ul className="limitations">{assumptions.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
          <div className="integrity-box"><strong>Integrity status: validated</strong><span>Every node hash and all 1,326 exact combos were checked before publication.</span></div>
        </>}
      </aside>
    </div>
  );
}

function Loading({ label }: { label: string }) { return <div className="loading-state" role="status"><span className="spinner" />{label}</div>; }
function ErrorState({ message }: { message: string }) { return <div className="error-state" role="alert"><strong>Study data unavailable</strong><span>{message}</span><Link to="/">Return to situations</Link></div>; }

function historyTitle(node: Pick<SolutionNode, "actionHistory"> | { actionHistory: Array<{ actor: string; label?: string; type: string }> }) {
  if (!node.actionHistory.length) return "Opening decision";
  return node.actionHistory.map((action) => `${action.actor} ${action.label ?? action.type.toLowerCase()}`).join(" · ");
}

function percent(value: string) {
  const valuePercent = Number(value) * 100;
  if (valuePercent > 0 && valuePercent < 0.01) return "<0.01%";
  return `${valuePercent.toFixed(valuePercent > 0 && valuePercent < 0.1 ? 2 : 1)}%`;
}
function signed(value: string) { const number = Number(value); return `${number >= 0 ? "+" : ""}${number.toFixed(3)}`; }
function frequencyDescription(actions: ActionOption[], strategy: GroupStrategy) { return actions.map((action) => `${action.label} ${percent(strategy.frequencies[action.actionId])}`).join(", "); }
function dominantMix(actions: ActionOption[], strategy: GroupStrategy) { return actions.map((action) => Number(strategy.frequencies[action.actionId]) > 0.009 ? action.label.charAt(0) : "").filter(Boolean).join("/"); }

function strategyBackground(actions: ActionOption[], strategy: GroupStrategy) {
  let start = 0;
  const stops: string[] = [];
  actions.forEach((action, index) => {
    const end = start + Number(strategy.frequencies[action.actionId]) * 100;
    stops.push(`${ACTION_COLORS[index]} ${start}%`, `${ACTION_COLORS[index]} ${end}%`);
    start = end;
  });
  return `linear-gradient(90deg, ${stops.join(", ")})`;
}

function cardFace(card: string) {
  const suit = card[1];
  const symbols: Record<string, string> = { s: "♠", h: "♥", d: "♦", c: "♣" };
  return <span className={`card-face suit-${suit}`}><strong>{card[0]}</strong><i>{symbols[suit]}</i></span>;
}
function prettyCombo(combo: string) {
  const symbols: Record<string, string> = { s: "♠", h: "♥", d: "♦", c: "♣" };
  return `${combo[0]}${symbols[combo[1]]} ${combo[2]}${symbols[combo[3]]}`;
}

export default function App() {
  return <Routes><Route path="/" element={<ScenarioSelection />} /><Route path="/study/:scenarioId/:nodeId" element={<StudyView />} /><Route path="*" element={<ScenarioSelection />} /></Routes>;
}
