import { useEffect, useState } from 'react';
import { BindShell }    from '../components/BindShell';
import { SectionHeader } from '../fujin/components/SectionHeader';
import type { LogsData } from '../api/endpoints';
import { logs as logsApi } from '../api/endpoints';

type LogType = 'security' | 'daemon';

const TAB: (active: boolean) => React.CSSProperties = (active) => ({
  fontFamily:      'inherit',
  fontSize:        12,
  fontWeight:      active ? 600 : 400,
  color:           active ? 'var(--fujin-text-primary)' : 'var(--fujin-text-muted)',
  padding:         '6px 16px',
  background:      active ? 'var(--fujin-bg-elevated)' : 'transparent',
  border:          '1px solid var(--fujin-border-subtle)',
  borderBottom:    active ? '1px solid var(--fujin-bg-elevated)' : '1px solid var(--fujin-border-subtle)',
  cursor:          'pointer',
  marginBottom:    -1,
  position:        'relative',
  zIndex:          active ? 1 : 0,
});

export default function LogsPage() {
  const [logType, setLogType] = useState<LogType>('security');
  const [data,    setData]    = useState<LogsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    logsApi.get(logType)
      .then(setData)
      .finally(() => setLoading(false));
  }, [logType]);

  return (
    <BindShell>
      <SectionHeader
        title="System Logs"
        description="Monitor system activity, security events, and scraper history."
      />

      <div style={{ marginTop: 20 }}>
        <div style={{ display: 'flex', gap: 0, marginBottom: 0 }}>
          {(['security', 'daemon'] as LogType[]).map((t) => (
            <button key={t} style={TAB(logType === t)} onClick={() => setLogType(t)}>
              {t === 'security' ? 'Security Log' : 'Daemon Log'}
            </button>
          ))}
        </div>

        <div style={{
          background:  'var(--fujin-bg-surface)',
          border:      '1px solid var(--fujin-border-subtle)',
        }}>
          <div style={{
            display:        'flex',
            justifyContent: 'space-between',
            padding:        '8px 12px',
            borderBottom:   '1px solid var(--fujin-border-subtle)',
            fontSize:        11,
            color:          'var(--fujin-text-muted)',
          }}>
            <span>File: {data?.log_file ?? '—'}</span>
            <span>Last {data?.line_count ?? 0} lines (Newest First)</span>
          </div>

          <div style={{
            height:     540,
            overflowY:  'auto',
            fontFamily: 'monospace',
            fontSize:   12,
            lineHeight: 1.6,
            padding:    '8px 12px',
            color:      'var(--fujin-text-secondary)',
          }}>
            {loading ? (
              <span style={{ color: 'var(--fujin-text-muted)' }}>Loading…</span>
            ) : data && data.logs.length > 0 ? (
              data.logs.map((line, i) => (
                <div key={i} style={{ borderBottom: '1px solid var(--fujin-bg-elevated)', padding: '2px 0' }}>
                  {line || ' '}
                </div>
              ))
            ) : (
              <span style={{ color: 'var(--fujin-text-muted)' }}>No log entries found.</span>
            )}
          </div>
        </div>
      </div>
    </BindShell>
  );
}
