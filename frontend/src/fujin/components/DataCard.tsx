import { Box, Collapse, Group, Menu, UnstyledButton } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import type { ReactNode } from 'react';
import tokens from '../tokens.json';

export interface CardAction {
  label:     string;
  icon?:     ReactNode;
  onClick:   () => void;
  danger?:   boolean;
  disabled?: boolean;
}

export interface DataCardProps {
  title:        string;
  badge?:       ReactNode;
  children:     ReactNode;
  detail?:      ReactNode;
  actions?:     CardAction[];
  defaultOpen?: boolean;
}

const PRIMARY_ACTION_LIMIT = 2;

export function DataCard({
  title,
  badge,
  children,
  detail,
  actions = [],
  defaultOpen = false,
}: DataCardProps) {
  const [open, { toggle }] = useDisclosure(defaultOpen);

  const primaryActions = actions.slice(0, PRIMARY_ACTION_LIMIT);
  const overflow       = actions.slice(PRIMARY_ACTION_LIMIT);
  const hasDetail      = Boolean(detail);

  const card: React.CSSProperties = {
    background:   'var(--fujin-bg-surface)',
    border:       `1px solid var(--fujin-border-subtle)`,
    borderRadius: tokens.radius.default,
  };

  const header: React.CSSProperties = {
    padding:        `${tokens.spacing.scale.sm}px ${tokens.spacing.scale.md}px`,
    borderBottom:   `1px solid var(--fujin-border-subtle)`,
    display:        'flex',
    alignItems:     'center',
    justifyContent: 'space-between',
    gap:            tokens.spacing.scale.sm,
  };

  const titleText: React.CSSProperties = {
    fontFamily:    tokens.typography.fontFamily.base,
    fontSize:      tokens.typography.fontSize.sm,
    fontWeight:    tokens.typography.fontWeight.semibold,
    color:         'var(--fujin-text-primary)',
    letterSpacing: tokens.typography.letterSpacing.wide,
    textTransform: 'uppercase',
  };

  const body: React.CSSProperties = {
    padding: tokens.spacing.scale.md,
  };

  const disclosureToggle: React.CSSProperties = {
    fontFamily:  tokens.typography.fontFamily.base,
    fontSize:    tokens.typography.fontSize.xs,
    color:       'var(--fujin-text-muted)',
    cursor:      'pointer',
    userSelect:  'none',
    padding:     `${tokens.spacing.scale.xs}px ${tokens.spacing.scale.md}px`,
    borderTop:   `1px solid var(--fujin-border-subtle)`,
    display:     'flex',
    alignItems:  'center',
    gap:         tokens.spacing.scale.xs,
  };

  const detailPanel: React.CSSProperties = {
    padding:    tokens.spacing.scale.md,
    background: 'var(--fujin-bg-base)',
  };

  const footer: React.CSSProperties = {
    padding:        `${tokens.spacing.scale.xs}px ${tokens.spacing.scale.md}px`,
    borderTop:      `1px solid var(--fujin-border-subtle)`,
    display:        'flex',
    alignItems:     'center',
    gap:            tokens.spacing.scale.sm,
    justifyContent: 'flex-end',
  };

  const actionBtn = (danger = false, disabled = false): React.CSSProperties => ({
    fontFamily:  tokens.typography.fontFamily.base,
    fontSize:    tokens.typography.fontSize.xs,
    fontWeight:  tokens.typography.fontWeight.medium,
    color:       disabled
                   ? 'var(--fujin-interactive-disabled)'
                   : danger
                     ? 'var(--fujin-status-danger)'
                     : 'var(--fujin-text-secondary)',
    padding:     `${tokens.spacing.base}px ${tokens.spacing.scale.sm}px`,
    cursor:      disabled ? 'not-allowed' : 'pointer',
    border:      `1px solid var(--fujin-border-subtle)`,
    borderRadius: tokens.radius.default,
    background:  'transparent',
    userSelect:  'none',
    opacity:     disabled ? tokens.opacity.disabled : 1,
  });

  return (
    <Box style={card}>

      {/* Header */}
      <div style={header}>
        <span style={titleText}>{title}</span>
        {badge && <span>{badge}</span>}
      </div>

      {/* Primary content */}
      <div style={body}>{children}</div>

      {/* Disclosure toggle */}
      {hasDetail && (
        <UnstyledButton style={disclosureToggle} onClick={toggle}>
          {open ? '▲ Less' : '▼ More detail'}
        </UnstyledButton>
      )}

      {/* Disclosed content — no extra border; toggle already provides the divider */}
      {hasDetail && (
        <Collapse in={open}>
          <div style={detailPanel}>{detail}</div>
        </Collapse>
      )}

      {/* Actions footer */}
      {actions.length > 0 && (
        <div style={footer}>
          {primaryActions.map((a) => (
            <UnstyledButton
              key={a.label}
              onClick={a.disabled ? undefined : a.onClick}
              disabled={a.disabled}
              style={actionBtn(a.danger, a.disabled)}
            >
              <Group gap={tokens.spacing.base}>
                {a.icon}
                {a.label}
              </Group>
            </UnstyledButton>
          ))}

          {overflow.length > 0 && (
            <Menu position="bottom-end" offset={tokens.spacing.base} radius={tokens.radius.default}>
              <Menu.Target>
                <UnstyledButton style={actionBtn()}>More ▾</UnstyledButton>
              </Menu.Target>
              <Menu.Dropdown
                style={{
                  background:   'var(--fujin-bg-elevated)',
                  border:       `1px solid var(--fujin-border-default)`,
                  borderRadius: tokens.radius.default,
                  padding:      `${tokens.spacing.base}px 0`,
                }}
              >
                {overflow.map((a) => (
                  <Menu.Item
                    key={a.label}
                    onClick={a.disabled ? undefined : a.onClick}
                    disabled={a.disabled}
                    leftSection={a.icon}
                    style={{
                      fontFamily:   tokens.typography.fontFamily.base,
                      fontSize:     tokens.typography.fontSize.xs,
                      color:        a.danger
                                      ? 'var(--fujin-status-danger)'
                                      : 'var(--fujin-text-secondary)',
                      borderRadius: tokens.radius.default,
                    }}
                  >
                    {a.label}
                  </Menu.Item>
                ))}
              </Menu.Dropdown>
            </Menu>
          )}
        </div>
      )}

    </Box>
  );
}
