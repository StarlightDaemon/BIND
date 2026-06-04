import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { BindShell }      from '../components/BindShell';
import { SectionHeader }  from '../fujin/components/SectionHeader';
import { DataTable }      from '../fujin/components/DataTable';
import type { DataColumn }     from '../fujin/components/DataTable';
import type { Magnet, MagnetsData } from '../api/endpoints';
import { magnets as magnetsApi } from '../api/endpoints';

const COLUMNS: DataColumn<Magnet>[] = [
  { key: 'title', label: 'Title', sortable: true },
  { key: 'date',  label: 'Date',  sortable: true, width: 110 },
  {
    key:    'hash',
    label:  'Hash',
    width:  100,
    render: (row) => (
      <span style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--fujin-text-muted)' }}>
        {row.hash.slice(0, 8)}…
      </span>
    ),
  },
];

const INPUT: React.CSSProperties = {
  fontFamily:  'inherit',
  fontSize:    13,
  color:       'var(--fujin-text-primary)',
  background:  'var(--fujin-bg-elevated)',
  border:      '1px solid var(--fujin-border-subtle)',
  padding:     '6px 10px',
  outline:     'none',
  flex:        1,
  maxWidth:    360,
};

const BTN_PRIMARY: React.CSSProperties = {
  fontFamily:  'inherit',
  fontSize:    12,
  fontWeight:  600,
  padding:     '6px 14px',
  border:      '1px solid var(--fujin-interactive-default)',
  background:  'var(--fujin-interactive-default)',
  color:       'var(--fujin-text-primary)',
  cursor:      'pointer',
};

const BTN_SECONDARY: React.CSSProperties = {
  fontFamily:  'inherit',
  fontSize:    12,
  padding:     '6px 14px',
  border:      '1px solid var(--fujin-border-subtle)',
  background:  'transparent',
  color:       'var(--fujin-text-secondary)',
  cursor:      'pointer',
};

export default function MagnetsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [data,    setData]    = useState<MagnetsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [draft,   setDraft]   = useState(searchParams.get('q') ?? '');

  const query = searchParams.get('q') ?? '';
  const page  = parseInt(searchParams.get('page') ?? '1', 10);

  const load = useCallback(async (q: string, p: number) => {
    setLoading(true);
    try {
      const d = await magnetsApi.list(q || undefined, p);
      setData(d);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(query, page); }, [load, query, page]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchParams(draft ? { q: draft } : {});
  };

  const setPage = (p: number) => {
    const params: Record<string, string> = { page: String(p) };
    if (query) params.q = query;
    setSearchParams(params);
  };

  return (
    <BindShell>
      <SectionHeader title="Magnets" description="Search and download indexed audiobook magnet links." />

      <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8, marginTop: 20, marginBottom: 16 }}>
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Search by title…"
          style={INPUT}
        />
        <button type="submit" style={BTN_PRIMARY}>Search</button>
        {query && (
          <button type="button" style={BTN_SECONDARY} onClick={() => { setDraft(''); setSearchParams({}); }}>
            Clear
          </button>
        )}
      </form>

      <DataTable
        columns={COLUMNS}
        rows={data?.magnets ?? []}
        rowKey="hash"
        loading={loading}
        emptyMessage={query ? 'No results for that search.' : 'No magnets indexed yet.'}
        rowActions={(row) => (
          <a
            href={row.magnet}
            style={{ fontSize: 11, padding: '3px 8px', border: '1px solid var(--fujin-border-subtle)', color: 'var(--fujin-text-secondary)', textDecoration: 'none' }}
          >
            Download
          </a>
        )}
      />

      {data && data.total_pages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12, fontSize: 12, color: 'var(--fujin-text-muted)' }}>
          <span>
            Page {data.page} of {data.total_pages} ({data.total_count.toLocaleString()} total)
          </span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              style={{ ...BTN_SECONDARY, opacity: data.page <= 1 ? 0.4 : 1 }}
              disabled={data.page <= 1}
              onClick={() => setPage(data.page - 1)}
            >
              Previous
            </button>
            <button
              style={{ ...BTN_SECONDARY, opacity: data.page >= data.total_pages ? 0.4 : 1 }}
              disabled={data.page >= data.total_pages}
              onClick={() => setPage(data.page + 1)}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </BindShell>
  );
}
