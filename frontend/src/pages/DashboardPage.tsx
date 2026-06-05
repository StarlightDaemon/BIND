import { useCallback, useEffect, useRef, useState } from 'react';
import { BindShell }    from '../components/BindShell';
import { SectionHeader } from '../fujin/components/SectionHeader';
import { DataTable }     from '../fujin/components/DataTable';
import { StatusBadge }   from '../fujin/components/StatusBadge';
import { useToast }      from '../fujin/components/FujinToastProvider';
import type { DataColumn }    from '../fujin/components/DataTable';
import type { DashboardData, Magnet } from '../api/endpoints';
import { dashboard } from '../api/endpoints';

const KPI_STYLE: React.CSSProperties = {
  display:             'grid',
  gridTemplateColumns: 'repeat(3, 1fr)',
  gap:                 16,
  marginBottom:        24,
};

const TILE: React.CSSProperties = {
  background:  'var(--fujin-bg-surface)',
  border:      '1px solid var(--fujin-border-subtle)',
  padding:     16,
};

const TILE_LABEL: React.CSSProperties = {
  fontFamily:    'var(--fujin-font-base, Verdana, sans-serif)',
  fontSize:      11,
  fontWeight:    600,
  color:         'var(--fujin-text-muted)',
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  marginBottom:  8,
};

const TILE_VALUE: React.CSSProperties = {
  fontFamily: 'var(--fujin-font-base, Verdana, sans-serif)',
  fontSize:   28,
  fontWeight: 700,
  color:      'var(--fujin-text-primary)',
  lineHeight: 1,
};

const COLUMNS: DataColumn<Magnet>[] = [
  { key: 'title', label: 'Title',     sortable: true },
  { key: 'date',  label: 'Collected', sortable: true, width: 120 },
  { key: 'hash',  label: 'Hash',      width: 100,
    render: (row) => (
      <span style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--fujin-text-muted)' }}>
        {row.hash.slice(0, 8)}…
      </span>
    ),
  },
];

export default function DashboardPage() {
  const [data,            setData]           = useState<DashboardData | null>(null);
  const [lastChecked,     setLastChecked]    = useState<string>('');
  const [loading,         setLoading]        = useState(true);
  const [triggering,      setTriggering]     = useState(false);
  const [scrapingEnabled, setScrapingEnabled] = useState<boolean | null>(null);
  const [enabling,        setEnabling]       = useState(false);
  const prevHashRef = useRef('');
  const toast = useToast();

  const load = useCallback(async () => {
    try {
      const d = await dashboard.stats();
      const hash = JSON.stringify(d);
      if (hash !== prevHashRef.current) {
        prevHashRef.current = hash;
        setData({
          magnets:        d.recent_magnets,
          magnet_count:   d.magnet_count,
          display_count:  d.recent_magnets.length,
          system_status:  d.system_status,
          status_message: d.status_message,
        });
        setScrapingEnabled(d.scraping_enabled);
      }
      setLastChecked(new Date().toLocaleTimeString());
    } catch {
      // silently ignore poll failures
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 10_000);
    return () => clearInterval(id);
  }, [load]);

  const handleEnable = async () => {
    setEnabling(true);
    try {
      const result = await dashboard.enableScraping();
      if (result.ok) {
        setScrapingEnabled(true);
        toast.show({ status: 'success', message: 'Scraping enabled. The daemon is starting up.' });
      } else {
        toast.show({ status: 'danger', message: result.message });
      }
    } catch {
      toast.show({ status: 'danger', message: 'Failed to enable scraping.' });
    } finally {
      setEnabling(false);
    }
  };

  const handleTrigger = async () => {
    setTriggering(true);
    try {
      const result = await dashboard.triggerScrape();
      toast.show({ status: result.ok ? 'success' : 'warning', message: result.message });
    } catch {
      toast.show({ status: 'danger', message: 'Failed to contact server.' });
    } finally {
      setTriggering(false);
    }
  };

  const statusVariant = (s: DashboardData['system_status']) => {
    if (s === 'online')  return 'success' as const;
    if (s === 'offline') return 'danger'  as const;
    return 'neutral' as const;
  };

  return (
    <BindShell>
      <SectionHeader title="Dashboard" description="Book Indexing Network Daemon" />

      {scrapingEnabled === false && (
        <div style={{
          marginTop:    20,
          marginBottom: 16,
          padding:      '16px 20px',
          background:   'var(--fujin-bg-surface)',
          border:       '1px solid var(--fujin-interactive-default)',
          display:      'flex',
          alignItems:   'center',
          gap:          16,
          flexWrap:     'wrap',
        }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{
              fontFamily:  'var(--fujin-font-base, Verdana, sans-serif)',
              fontWeight:  600,
              fontSize:    13,
              color:       'var(--fujin-text-primary)',
              marginBottom: 4,
            }}>
              Archiving is paused
            </div>
            <div style={{
              fontFamily: 'var(--fujin-font-base, Verdana, sans-serif)',
              fontSize:   12,
              color:      'var(--fujin-text-muted)',
            }}>
              BIND is ready but will not collect magnets until you begin archiving.
            </div>
          </div>
          <button
            onClick={() => { void handleEnable(); }}
            disabled={enabling}
            style={{
              fontFamily:  'inherit',
              fontSize:    13,
              fontWeight:  600,
              padding:     '8px 20px',
              border:      '1px solid var(--fujin-interactive-default)',
              background:  'var(--fujin-interactive-default)',
              color:       'var(--fujin-text-primary)',
              cursor:      enabling ? 'not-allowed' : 'pointer',
              whiteSpace:  'nowrap',
              opacity:     enabling ? 0.6 : 1,
            }}
          >
            {enabling ? 'Starting…' : 'Begin Archiving'}
          </button>
        </div>
      )}

      <div style={{ ...KPI_STYLE, marginTop: 20 }}>
        <div style={TILE}>
          <div style={TILE_LABEL}>Total Magnets</div>
          <div style={TILE_VALUE}>{data ? data.magnet_count.toLocaleString() : '—'}</div>
        </div>
        <div style={TILE}>
          <div style={TILE_LABEL}>System Status</div>
          <div style={{ marginTop: 4 }}>
            {data ? (
              <StatusBadge
                status={statusVariant(data.system_status)}
                label={data.system_status}
                size="md"
              />
            ) : '—'}
          </div>
          {data && (
            <div style={{ marginTop: 6, fontSize: 11, color: 'var(--fujin-text-muted)' }}>
              {data.status_message}
            </div>
          )}
        </div>
        <div style={TILE}>
          <div style={TILE_LABEL}>Feed Access</div>
          <div style={{ marginTop: 6, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <a
              href="/feed.xml"
              style={{
                display:      'inline-block',
                padding:      '5px 12px',
                border:       '1px solid var(--fujin-interactive-default)',
                background:   'var(--fujin-interactive-default)',
                color:        'var(--fujin-text-primary)',
                fontFamily:   'inherit',
                fontSize:     12,
                textDecoration: 'none',
              }}
            >
              RSS Feed
            </a>
            <button
              onClick={() => { void handleTrigger(); }}
              disabled={triggering}
              style={{
                fontFamily: 'inherit',
                fontSize:   12,
                padding:    '5px 12px',
                border:     '1px solid var(--fujin-border-subtle)',
                background: 'transparent',
                color:      triggering ? 'var(--fujin-text-muted)' : 'var(--fujin-text-secondary)',
                cursor:     triggering ? 'not-allowed' : 'pointer',
              }}
            >
              {triggering ? 'Triggering…' : 'Run Now'}
            </button>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ fontFamily: 'inherit', fontWeight: 600, fontSize: 13, color: 'var(--fujin-text-primary)' }}>
          Recent Index
        </div>
        {lastChecked && (
          <div style={{ fontSize: 11, color: 'var(--fujin-text-muted)' }}>
            Last checked: {lastChecked}
          </div>
        )}
      </div>

      <DataTable
        columns={COLUMNS}
        rows={data?.magnets ?? []}
        rowKey="hash"
        loading={loading}
        emptyMessage="No magnets indexed yet."
        rowActions={(row) => (
          <a
            href={row.magnet}
            style={{
              fontSize:       11,
              padding:        '3px 8px',
              border:         '1px solid var(--fujin-border-subtle)',
              color:          'var(--fujin-text-secondary)',
              textDecoration: 'none',
            }}
          >
            Download
          </a>
        )}
      />
    </BindShell>
  );
}
