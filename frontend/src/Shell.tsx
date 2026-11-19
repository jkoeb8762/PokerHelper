import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="topbar">
        <Link className="brand" to="/" aria-label="PokerHelper home">
          <span className="brand-mark" aria-hidden="true">PH</span>
          <span><strong>PokerHelper</strong><small>Local study lab</small></span>
        </Link>
        <nav aria-label="Primary navigation">
          <NavLink to="/" end>Study</NavLink>
          <NavLink to="/train">Train</NavLink>
          <NavLink to="/sessions">Review</NavLink>
        </nav>
        <div className="local-status"><span aria-hidden="true" /> Local · v0.3</div>
      </header>
      <main id="main-content" tabIndex={-1}>{children}</main>
      <footer>Built for deliberate, post-session study. No live-table integration.</footer>
    </div>
  );
}
