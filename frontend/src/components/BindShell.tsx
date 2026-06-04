import type { ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ToolShell } from '../fujin/components/ToolShell';
import type { NavItem } from '../fujin/components/ToolShell';
import { useAuth } from '../context/AuthContext';

function IconHome()     { return <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1L1 7h2v7h4v-4h2v4h4V7h2L8 1z"/></svg>; }
function IconMagnets()  { return <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zm0 2a5 5 0 1 1 0 10A5 5 0 0 1 8 3zm0 2a3 3 0 1 0 0 6A3 3 0 0 0 8 5z"/></svg>; }
function IconMetrics()  { return <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M1 14V9h3v5H1zm5 0V6h3v8H6zm5 0V2h3v12h-3z"/></svg>; }
function IconSettings() { return <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M8 5a3 3 0 1 0 0 6A3 3 0 0 0 8 5zm0 1.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3zM6.5 0l-.5 2.1a6 6 0 0 0-1.5.9L2.4 2.2 0 6l1.7 1.3a5.9 5.9 0 0 0 0 1.4L0 10l2.4 3.8 2.1-.8a6 6 0 0 0 1.5.9L6.5 16h3l.5-2.1a6 6 0 0 0 1.5-.9l2.1.8L16 10l-1.7-1.3c0-.5.1-.9 0-1.4L16 6l-2.4-3.8-2.1.8a6 6 0 0 0-1.5-.9L9.5 0h-3z"/></svg>; }
function IconLogs()     { return <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M2 3h12v1H2V3zm0 3h12v1H2V6zm0 3h8v1H2V9zm0 3h6v1H2v-1z"/></svg>; }

const NAV_ROUTES = [
  { path: '/',         label: 'Dashboard',   icon: <IconHome /> },
  { path: '/magnets',  label: 'Magnets',     icon: <IconMagnets /> },
  { path: '/metrics',  label: 'Metrics',     icon: <IconMetrics /> },
  { path: '/settings', label: 'Settings',    icon: <IconSettings /> },
  { path: '/logs',     label: 'System Logs', icon: <IconLogs /> },
];

function LogoMark() {
  return (
    <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 14, letterSpacing: 2 }}>
      BIND
    </span>
  );
}

interface BindShellProps {
  children: ReactNode;
}

export function BindShell({ children }: BindShellProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, authenticated } = useAuth();

  const navItems: NavItem[] = NAV_ROUTES.map((r) => ({
    icon:    r.icon,
    label:   r.label,
    active:  location.pathname === r.path,
    onClick: () => navigate(r.path),
  }));

  const footer = authenticated ? (
    <button
      onClick={() => { void logout(); }}
      style={{
        width:      '100%',
        background: 'transparent',
        border:     '1px solid var(--fujin-border-subtle)',
        color:      'var(--fujin-text-muted)',
        fontFamily: 'inherit',
        fontSize:   12,
        padding:    '6px 8px',
        cursor:     'pointer',
        textAlign:  'center',
      }}
    >
      Sign out
    </button>
  ) : undefined;

  return (
    <ToolShell navItems={navItems} logo={<LogoMark />} footer={footer}>
      <div style={{ padding: 24 }}>
        {children}
      </div>
    </ToolShell>
  );
}
