import { Box, Loader, Pagination, Table, Text, UnstyledButton } from '@mantine/core';
import { useState } from 'react';
import type { ReactNode } from 'react';
import tokens from '../tokens.json';

export type SortDirection = 'asc' | 'desc';

// 48px = xl(24) * 2 — no hardcode
const ACTION_COL_WIDTH = tokens.spacing.scale.xl * 2;

export interface DataColumn<T> {
  key:       keyof T & string;   // symbol keys excluded — safe for String() and React keys
  label:     string;
  sortable?: boolean;
  width?:    number | string;
  render?:   (row: T) => ReactNode;
}

export interface DataTableProps<T extends object> {
  columns:       DataColumn<T>[];
  rows:          T[];
  rowKey:        keyof T & string;  // must point to a primitive field (string | number)
  loading?:      boolean;
  emptyMessage?: string;
  pageSize?:     number;
  rowActions?:   (row: T) => ReactNode;
  onSortChange?: (key: keyof T & string, direction: SortDirection) => void;
}

export function DataTable<T extends object>({
  columns,
  rows,
  rowKey,
  loading      = false,
  emptyMessage = 'No records found.',
  pageSize,
  rowActions,
  onSortChange,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<(keyof T & string) | null>(null);
  const [sortDir, setSortDir] = useState<SortDirection>('asc');
  const [page,    setPage]    = useState(1);

  // Sort — client-side only when onSortChange is not provided
  const sorted = onSortChange
    ? rows
    : sortKey
      ? [...rows].sort((a, b) => {
          const av = a[sortKey];
          const bv = b[sortKey];
          const cmp = av < bv ? -1 : av > bv ? 1 : 0;
          return sortDir === 'asc' ? cmp : -cmp;
        })
      : rows;

  // Pagination — clamp page when dataset shrinks
  const totalPages    = pageSize ? Math.ceil(sorted.length / pageSize) : 1;
  const effectivePage = Math.min(page, Math.max(1, totalPages));
  const paginated     = pageSize
    ? sorted.slice((effectivePage - 1) * pageSize, effectivePage * pageSize)
    : sorted;

  const handleSort = (key: keyof T & string) => {
    const nextDir: SortDirection =
      sortKey === key && sortDir === 'asc' ? 'desc' : 'asc';
    setSortKey(key);
    setSortDir(nextDir);
    setPage(1);
    onSortChange?.(key, nextDir);
  };

  const ariaSortValue = (key: keyof T & string): React.AriaAttributes['aria-sort'] => {
    if (sortKey !== key) return 'none';
    return sortDir === 'asc' ? 'ascending' : 'descending';
  };

  const sortIndicator = (key: keyof T & string) => {
    if (sortKey !== key) return ' ↕';
    return sortDir === 'asc' ? ' ↑' : ' ↓';
  };

  // Styles
  const wrapper: React.CSSProperties = {
    background:   'var(--fujin-bg-surface)',
    border:       `1px solid var(--fujin-border-subtle)`,
    borderRadius: tokens.radius.default,
    overflow:     'hidden',
  };

  const thBase: React.CSSProperties = {
    fontFamily:    tokens.typography.fontFamily.base,
    fontSize:      tokens.typography.fontSize.xs,
    fontWeight:    tokens.typography.fontWeight.semibold,
    color:         'var(--fujin-text-muted)',
    letterSpacing: tokens.typography.letterSpacing.wide,
    textTransform: 'uppercase',
    padding:       `${tokens.spacing.scale.sm}px ${tokens.spacing.scale.md}px`,
    borderBottom:  `1px solid var(--fujin-border-subtle)`,
    background:    'var(--fujin-bg-elevated)',
    userSelect:    'none',
    whiteSpace:    'nowrap',
  };

  const tdBase: React.CSSProperties = {
    fontFamily:    tokens.typography.fontFamily.base,
    fontSize:      tokens.typography.fontSize.sm,
    color:         'var(--fujin-text-secondary)',
    padding:       `${tokens.spacing.scale.sm}px ${tokens.spacing.scale.md}px`,
    borderBottom:  `1px solid var(--fujin-border-subtle)`,
    verticalAlign: 'middle',
  };

  const isEmpty     = rows.length === 0 && !loading;
  const isReloading = rows.length > 0 && loading;

  return (
    <Box style={wrapper}>
      <Table
        withRowBorders={false}
        style={{
          opacity:    isReloading ? tokens.opacity.disabled : 1,
          transition: `opacity ${tokens.transition.duration.base}`,
        }}
        highlightOnHover={!loading}
      >
        <Table.Thead>
          <Table.Tr>
            {columns.map((col) => (
              <Table.Th
                key={col.key}
                style={thBase}
                aria-sort={col.sortable ? ariaSortValue(col.key) : undefined}
                {...(col.width ? { w: col.width } : {})}
              >
                {col.sortable ? (
                  <UnstyledButton
                    onClick={() => handleSort(col.key)}
                    style={{
                      color:         'var(--fujin-text-secondary)',
                      fontFamily:    tokens.typography.fontFamily.base,
                      fontSize:      tokens.typography.fontSize.xs,
                      fontWeight:    tokens.typography.fontWeight.semibold,
                      letterSpacing: tokens.typography.letterSpacing.wide,
                      textTransform: 'uppercase',
                    }}
                  >
                    {col.label}{sortIndicator(col.key)}
                  </UnstyledButton>
                ) : (
                  col.label
                )}
              </Table.Th>
            ))}
            {rowActions && (
              <Table.Th style={{ ...thBase, width: ACTION_COL_WIDTH, textAlign: 'right' }} />
            )}
          </Table.Tr>
        </Table.Thead>

        <Table.Tbody>
          {/* Loading — no existing rows */}
          {loading && rows.length === 0 && (
            <Table.Tr>
              <Table.Td
                colSpan={columns.length + (rowActions ? 1 : 0)}
                style={{ ...tdBase, textAlign: 'center', padding: tokens.spacing.scale.lg, borderBottom: 'none' }}
              >
                <Loader size={tokens.typography.fontSize.xl} color="var(--fujin-text-muted)" />
              </Table.Td>
            </Table.Tr>
          )}

          {/* Empty state */}
          {isEmpty && (
            <Table.Tr>
              <Table.Td
                colSpan={columns.length + (rowActions ? 1 : 0)}
                style={{ ...tdBase, textAlign: 'center', color: 'var(--fujin-text-muted)', borderBottom: 'none' }}
              >
                {emptyMessage}
              </Table.Td>
            </Table.Tr>
          )}

          {/* Data rows */}
          {paginated.map((row) => (
            <Table.Tr key={row[rowKey] as string | number}>
              {columns.map((col) => (
                <Table.Td key={col.key} style={tdBase}>
                  {col.render
                    ? col.render(row)
                    : row[col.key] != null
                      ? String(row[col.key])
                      : '—'
                  }
                </Table.Td>
              ))}
              {rowActions && (
                <Table.Td style={{ ...tdBase, textAlign: 'right', width: ACTION_COL_WIDTH }}>
                  {rowActions(row)}
                </Table.Td>
              )}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      {/* Pagination — no borderTop, last row's borderBottom already divides */}
      {pageSize && totalPages > 1 && (
        <Box
          style={{
            display:        'flex',
            justifyContent: 'flex-end',
            alignItems:     'center',
            padding:        `${tokens.spacing.scale.sm}px ${tokens.spacing.scale.md}px`,
            gap:            tokens.spacing.scale.sm,
          }}
        >
          <Text
            style={{
              fontFamily: tokens.typography.fontFamily.base,
              fontSize:   tokens.typography.fontSize.xs,
              color:      'var(--fujin-text-muted)',
            }}
          >
            {(effectivePage - 1) * pageSize + 1}–{Math.min(effectivePage * pageSize, sorted.length)} of {sorted.length}
          </Text>
          <Pagination
            total={totalPages}
            value={effectivePage}
            onChange={setPage}
            disabled={loading}
            size="sm"
            radius={tokens.radius.default}
            styles={{
              control: {
                fontFamily:   tokens.typography.fontFamily.base,
                fontSize:     tokens.typography.fontSize.xs,
                borderRadius: tokens.radius.default,
                border:       `1px solid var(--fujin-border-subtle)`,
                background:   'var(--fujin-bg-elevated)',
                color:        'var(--fujin-text-secondary)',
              },
            }}
          />
        </Box>
      )}
    </Box>
  );
}
