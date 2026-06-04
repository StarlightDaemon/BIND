import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { UnstyledButton } from '@mantine/core';
import tokens from '../tokens.json';

const TOAST_WIDTH = 320;
const MAX_TOASTS  = 5;

export type ToastStatus = 'success' | 'danger' | 'warning' | 'info';

export interface ToastOptions {
  message:   string;
  status:    ToastStatus;
  title?:    string;
  duration?: number | false;  // ms; default 4000; false = persist until dismissed
}

interface ToastEntry extends Required<Omit<ToastOptions, 'title'>> {
  id:     string;
  title?: string;
}

interface ToastContextValue {
  show: (opts: ToastOptions) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside FujinToastProvider');
  return ctx;
}

const STATUS_COLOR: Record<ToastStatus, string> = {
  success: 'var(--fujin-status-success)',
  danger:  'var(--fujin-status-danger)',
  warning: 'var(--fujin-status-warning)',
  info:    'var(--fujin-status-info)',
};

// Internal per-toast component — manages its own enter animation and auto-dismiss timer
interface ToastItemProps {
  entry:     ToastEntry;
  onDismiss: (id: string) => void;
}

function ToastItem({ entry, onDismiss }: ToastItemProps) {
  const [visible, setVisible] = useState(false);

  // Trigger enter animation on next frame
  useEffect(() => {
    const raf = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(raf);
  }, []);

  // Auto-dismiss timer
  useEffect(() => {
    if (entry.duration === false) return;
    const t = setTimeout(() => onDismiss(entry.id), entry.duration);
    return () => clearTimeout(t);
  }, [entry.id, entry.duration, onDismiss]);

  const box: React.CSSProperties = {
    width:        TOAST_WIDTH,
    background:   'var(--fujin-bg-surface)',
    border:       `1px solid var(--fujin-border-subtle)`,
    borderLeft:   `4px solid ${STATUS_COLOR[entry.status]}`,
    borderRadius: tokens.radius.default,
    padding:      tokens.spacing.scale.md,
    boxShadow:    'var(--fujin-shadow-md)',
    display:      'flex',
    flexDirection:'column',
    gap:          tokens.spacing.scale.xs,
    pointerEvents:'auto',
    opacity:      visible ? 1 : 0,
    transform:    visible ? 'translateY(0)' : 'translateY(8px)',
    transition:   `opacity ${tokens.transition.duration.base} ${tokens.transition.easing.out},
                   transform ${tokens.transition.duration.base} ${tokens.transition.easing.out}`,
  };

  const header: React.CSSProperties = {
    display:        'flex',
    alignItems:     'center',
    justifyContent: 'space-between',
    gap:            tokens.spacing.scale.sm,
  };

  const titleStyle: React.CSSProperties = {
    fontFamily:  tokens.typography.fontFamily.base,
    fontSize:    tokens.typography.fontSize.sm,
    fontWeight:  tokens.typography.fontWeight.semibold,
    color:       'var(--fujin-text-primary)',
    flex:        1,
  };

  const messageStyle: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.base,
    fontSize:   tokens.typography.fontSize.xs,
    color:      'var(--fujin-text-secondary)',
    lineHeight: tokens.typography.lineHeight.base,
  };

  const closeBtn: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.base,
    fontSize:   tokens.typography.fontSize.md,
    color:      'var(--fujin-text-muted)',
    cursor:     'pointer',
    lineHeight: 1,
    flexShrink: 0,
  };

  return (
    <div style={box}>
      <div style={header}>
        {entry.title && <span style={titleStyle}>{entry.title}</span>}
        <UnstyledButton
          onClick={() => onDismiss(entry.id)}
          style={{ ...closeBtn, marginLeft: entry.title ? undefined : 'auto' }}
          aria-label="Dismiss notification"
        >
          ×
        </UnstyledButton>
      </div>
      <p style={{ ...messageStyle, margin: 0 }}>{entry.message}</p>
    </div>
  );
}

export interface FujinToastProviderProps {
  children: ReactNode;
}

export function FujinToastProvider({ children }: FujinToastProviderProps) {
  const [toasts, setToasts] = useState<ToastEntry[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = useCallback((opts: ToastOptions) => {
    const entry: ToastEntry = {
      id:       crypto.randomUUID(),
      status:   opts.status,
      message:  opts.message,
      title:    opts.title,
      duration: opts.duration ?? 4000,
    };
    setToasts((prev) => {
      const next = [...prev, entry];
      return next.length > MAX_TOASTS ? next.slice(next.length - MAX_TOASTS) : next;
    });
  }, []);

  const container: React.CSSProperties = {
    position:      'fixed',
    bottom:        tokens.spacing.scale.xl,
    right:         tokens.spacing.scale.xl,
    zIndex:        9999,
    display:       'flex',
    flexDirection: 'column-reverse',
    gap:           tokens.spacing.scale.sm,
    pointerEvents: 'none',
  };

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      {createPortal(
        <div style={container} role="status" aria-live="polite" aria-label="Notifications">
          {toasts.map((entry) => (
            <ToastItem key={entry.id} entry={entry} onDismiss={dismiss} />
          ))}
        </div>,
        document.body
      )}
    </ToastContext.Provider>
  );
}
