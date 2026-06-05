import { useEffect, useState } from 'react';
import { BindShell }    from '../components/BindShell';
import { SectionHeader } from '../fujin/components/SectionHeader';
import { DataTable }     from '../fujin/components/DataTable';
import { StatusBadge }   from '../fujin/components/StatusBadge';
import type { DataColumn }    from '../fujin/components/DataTable';
import type { DailyStat, MetricsData, ScrapeRun } from '../api/endpoints';
import { metrics } from '../api/endpoints';

const CHART_H = 72;
const CHART_LABEL_H = 16;

function TrendChart({ data }: { data: DailyStat[] }) {
  if (!data.length) return null;
  const maxCount = Math.max(...data.map((d) => d.count), 1);
  const svgW = 100;
  const svgH = CHART_H + CHART_LABEL_H;
  const gap = 0.5;
  const barW = (svgW - gap * (data.length - 1)) / data.length;
  const stride = Math.ceil(data.length / 6);

  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--fujin-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
        Daily Collection — Last {data.length} Days
      </div>
      <div style={{ background: 'var(--fujin-bg-surface)', border: '1px solid var(--fujin-border-subtle)', padding: '12px 12px 8px' }}>
        <svg
          viewBox={`0 0 ${svgW} ${svgH}`}
          preserveAspectRatio="none"
          style={{ width: '100%', height: CHART_H + CHART_LABEL_H, display: 'block' }}
          aria-label="Daily collection trend"
        >
          {data.map((d, i) => {
            const barH = maxCount > 0 ? (d.count / maxCount) * CHART_H : 0;
            const x = i * (barW + gap);
            const y = CHART_H - barH;
            const showLabel = i % stride === 0 || i === data.length - 1;
            const label = d.date.slice(5); // MM-DD
            return (
              <g key={d.date}>
                <rect
                  x={x}
                  y={y}
                  width={barW}
                  height={barH}
                  fill="var(--fujin-interactive-default)"
                  opacity={d.count === 0 ? 0.2 : 0.85}
                >
                  <title>{d.date}: {d.count}</title>
                </rect>
                {showLabel && (
                  <text
                    x={x + barW / 2}
                    y={svgH - 1}
                    textAnchor="middle"
                    fontSize={4}
                    fill="var(--fujin-text-muted)"
                  >
                    {label}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

const KPI_GRID: React.CSSProperties = {
  display:             'grid',
  gridTemplateColumns: 'repeat(5, 1fr)',
  gap:                 12,
  marginBottom:        24,
};

const TILE: React.CSSProperties = {
  background: 'var(--fujin-bg-surface)',
  border:     '1px solid var(--fujin-border-subtle)',
  padding:    16,
};

const TILE_LABEL: React.CSSProperties = {
  fontSize:      11,
  fontWeight:    600,
  color:         'var(--fujin-text-muted)',
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  marginBottom:  8,
};

const TILE_VALUE: React.CSSProperties = {
  fontSize:   24,
  fontWeight: 700,
  color:      'var(--fujin-text-primary)',
  lineHeight: 1,
};

const COLUMNS: DataColumn<ScrapeRun>[] = [
  { key: 'run_at',    label: 'Run At',    sortable: true, width: 160 },
  {
    key:    'result',
    label:  'Result',
    width:  90,
    render: (row) => {
      const variant = row.result === 'success' ? 'success' : row.result === 'failure' ? 'danger' : 'warning';
      return <StatusBadge status={variant} label={row.result} />;
    },
  },
  { key: 'new_items', label: 'New Items', sortable: true, width: 100 },
  {
    key:    'duration',
    label:  'Duration',
    width:  90,
    render: (row) => `${row.duration.toFixed(1)}s`,
  },
];

export default function MetricsPage() {
  const [data,    setData]    = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    metrics.get()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  const s = data?.stats;

  return (
    <BindShell>
      <SectionHeader title="Metrics" description="Collection statistics and scrape history." />

      <div style={{ ...KPI_GRID, marginTop: 20 }}>
        {[
          { label: 'Total Magnets', value: s?.total },
          { label: 'Today',         value: s?.today },
          { label: 'Last 7 Days',   value: s?.last_7_days },
          { label: 'Last 30 Days',  value: s?.last_30_days },
          { label: 'Last Collected', value: s?.last_date ?? '—', small: true },
        ].map((t) => (
          <div key={t.label} style={TILE}>
            <div style={TILE_LABEL}>{t.label}</div>
            <div style={{ ...TILE_VALUE, fontSize: t.small ? 14 : 24 }}>
              {t.value ?? '—'}
            </div>
          </div>
        ))}
      </div>

      {data?.daily_counts && data.daily_counts.length > 0 && (
        <TrendChart data={data.daily_counts} />
      )}

      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--fujin-text-primary)' }}>Scrape History</div>
        {data && (
          <div style={{ fontSize: 11, color: 'var(--fujin-text-muted)' }}>
            {data.success_rate != null
              ? `${data.success_rate}% success over last ${data.runs.length} runs`
              : 'No runs recorded'}
          </div>
        )}
      </div>

      <DataTable
        columns={COLUMNS}
        rows={data?.runs ?? []}
        rowKey="run_at"
        loading={loading}
        emptyMessage="No scrape runs recorded yet."
        pageSize={20}
      />

      {data && (
        <div style={{ marginTop: 16, fontSize: 11, color: 'var(--fujin-text-muted)' }}>
          Last updated: {data.now}
        </div>
      )}
    </BindShell>
  );
}
