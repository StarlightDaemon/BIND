import { AppShell, Stack, Tooltip, UnstyledButton } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useState, type ReactNode } from 'react';
import tokens from '../tokens.json';

const RAIL_EXPANDED    = 220;
const RAIL_COLLAPSED   = 60;
const NAV_ITEM_HEIGHT  = 40;

export interface NavItem {
  icon:     ReactNode;
  label:    string;
  active?:  boolean;
  onClick?: () => void;
}

export interface ToolShellProps {
  navItems:  NavItem[];
  logo?:     ReactNode;
  footer?:   ReactNode;
  children:  ReactNode;
  header?:   (controls: { toggleMobile: () => void; mobileOpen: boolean }) => ReactNode;
}

export function ToolShell({ navItems, logo, footer, children, header }: ToolShellProps) {
  const [collapsed,   { toggle: toggleRail }]   = useDisclosure(false);
  const [mobileOpen,  { toggle: toggleMobile }] = useDisclosure(false);
  const [hoveredLabel, setHoveredLabel] = useState<string | null>(null);

  const railWidth = collapsed ? RAIL_COLLAPSED : RAIL_EXPANDED;

  const rail: React.CSSProperties = {
    background:   'var(--fujin-bg-surface)',
    borderRight:  `1px solid var(--fujin-border-subtle)`,
    display:      'flex',
    flexDirection:'column',
    transition:   `width ${tokens.transition.duration.base} ${tokens.transition.easing.default}`,
    overflowX:    'hidden',
  };

  const logoBar: React.CSSProperties = {
    padding:       tokens.spacing.scale.md,
    borderBottom:  `1px solid var(--fujin-border-subtle)`,
    display:       'flex',
    alignItems:    'center',
    gap:           tokens.spacing.scale.sm,
    color:         'var(--fujin-text-primary)',
    cursor:        'pointer',
    userSelect:    'none',
    flexShrink:    0,
  };

  const logoLabel: React.CSSProperties = {
    fontFamily:  tokens.typography.fontFamily.base,
    fontSize:    tokens.typography.fontSize.sm,
    fontWeight:  tokens.typography.fontWeight.semibold,
    whiteSpace:  'nowrap',
    overflow:    'hidden',
  };

  const footerSlot: React.CSSProperties = {
    borderTop: `1px solid var(--fujin-border-subtle)`,
    padding:   tokens.spacing.scale.sm,
    flexShrink: 0,
  };

  const main: React.CSSProperties = {
    background: 'var(--fujin-bg-base)',
    minHeight:  '100vh',
  };

  const headerBar: React.CSSProperties = {
    background:    'var(--fujin-bg-surface)',
    borderBottom:  `1px solid var(--fujin-border-subtle)`,
    display:       'flex',
    alignItems:    'center',
    padding:       `0 ${tokens.spacing.scale.md}px`,
    height:        '100%',
  };

  return (
    <AppShell
      header={header ? { height: tokens.spacing.scale.xl * 2 } : undefined}
      navbar={{
        width:     railWidth,
        breakpoint:'sm',
        collapsed: { mobile: !mobileOpen },
      }}
      padding={0}
    >
      {header && (
        <AppShell.Header style={headerBar}>
          {header({ toggleMobile, mobileOpen })}
        </AppShell.Header>
      )}
      <AppShell.Navbar style={rail}>

        {/* Logo / collapse toggle */}
        <UnstyledButton onClick={toggleRail} style={logoBar}>
          {logo}
          {!collapsed && <span style={logoLabel}>Menu</span>}
        </UnstyledButton>

        {/* Nav items */}
        <Stack gap={0} style={{ flex: 1, overflowY: 'auto', padding: `${tokens.spacing.scale.xs}px 0` }}>
          {navItems.map((item) =>
            collapsed ? (
              <Tooltip key={item.label} label={item.label} position="right" withArrow={false} radius={tokens.radius.default}>
                <UnstyledButton
                  onClick={item.onClick}
                  style={{
                    display:         'flex',
                    alignItems:      'center',
                    justifyContent:  'center',
                    height:          NAV_ITEM_HEIGHT,
                    width:           '100%',
                    color:           item.active
                                       ? 'var(--fujin-text-primary)'
                                       : 'var(--fujin-text-muted)',
                    background:      item.active
                                       ? 'var(--fujin-bg-elevated)'
                                       : 'transparent',
                  }}
                >
                  {item.icon}
                </UnstyledButton>
              </Tooltip>
            ) : (
              <UnstyledButton
                key={item.label}
                onClick={item.onClick}
                onMouseEnter={() => setHoveredLabel(item.label)}
                onMouseLeave={() => setHoveredLabel(null)}
                style={{
                  display:      'flex',
                  alignItems:   'center',
                  gap:          tokens.spacing.scale.sm,
                  height:       NAV_ITEM_HEIGHT,
                  width:        '100%',
                  padding:      `0 ${tokens.spacing.scale.sm}px`,
                  borderRadius: tokens.radius.default,
                  background:   item.active || hoveredLabel === item.label
                                  ? 'var(--fujin-bg-elevated)'
                                  : 'transparent',
                  color:        item.active
                                  ? 'var(--fujin-text-primary)'
                                  : 'var(--fujin-text-secondary)',
                  fontFamily:   tokens.typography.fontFamily.base,
                  fontSize:     tokens.typography.fontSize.sm,
                  cursor:       'pointer',
                  whiteSpace:   'nowrap',
                  overflow:     'hidden',
                  transition:   `background ${tokens.transition.duration.base} ${tokens.transition.easing.default}`,
                }}
              >
                {item.icon}
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.label}</span>
              </UnstyledButton>
            )
          )}
        </Stack>

        {/* Footer slot — user profile, settings, etc. */}
        {footer && <div style={footerSlot}>{footer}</div>}

      </AppShell.Navbar>

      <AppShell.Main style={main}>
        {children}
      </AppShell.Main>
    </AppShell>
  );
}
