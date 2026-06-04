import { Popover, UnstyledButton } from '@mantine/core';
import { useState } from 'react';
import tokens from '../tokens.json';
import { useFujinTheme } from './FujinThemeProvider';

function GearIcon() {
  return (
    <span aria-hidden="true" style={{ fontSize: 14, lineHeight: 1 }}>⚙</span>
  );
}

function ModeButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <UnstyledButton
      onClick={onClick}
      style={{
        flex:       1,
        padding:    `${tokens.spacing.scale.xs}px ${tokens.spacing.scale.sm}px`,
        fontFamily: tokens.typography.fontFamily.base,
        fontSize:   tokens.typography.fontSize.xs,
        fontWeight: active ? tokens.typography.fontWeight.semibold : tokens.typography.fontWeight.regular,
        color:      active ? 'var(--fujin-text-primary)' : 'var(--fujin-text-muted)',
        background: active ? 'var(--fujin-bg-elevated)' : 'transparent',
        border:     `1px solid ${active ? 'var(--fujin-border-strong)' : 'var(--fujin-border-subtle)'}`,
        cursor:     active ? 'default' : 'pointer',
        textAlign:  'center',
        transition: `color ${tokens.transition.duration.base} ${tokens.transition.easing.default},
                     background ${tokens.transition.duration.base} ${tokens.transition.easing.default}`,
      }}
    >
      {label}
    </UnstyledButton>
  );
}

export function ThemeMenu() {
  const [open, setOpen] = useState(false);
  const { mode, toggle } = useFujinTheme();

  return (
    <Popover
      opened={open}
      onChange={setOpen}
      position="top-end"
      offset={8}
      radius={0}
      shadow="md"
    >
      <Popover.Target>
        <UnstyledButton
          onClick={() => setOpen(o => !o)}
          aria-label="Theme settings"
          style={{
            display:        'flex',
            alignItems:     'center',
            justifyContent: 'center',
            width:          24,
            height:         24,
            color:          'var(--fujin-chrome-text)',
            opacity:        open ? 1 : 0.6,
            cursor:         'pointer',
            transition:     `opacity ${tokens.transition.duration.base} ${tokens.transition.easing.default}`,
          }}
        >
          <GearIcon />
        </UnstyledButton>
      </Popover.Target>

      <Popover.Dropdown
        style={{
          background:   'var(--fujin-bg-surface)',
          border:       '1px solid var(--fujin-border-subtle)',
          borderRadius: 0,
          padding:      tokens.spacing.scale.sm,
          minWidth:     160,
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: tokens.spacing.scale.sm }}>
          <span style={{
            fontFamily:    tokens.typography.fontFamily.base,
            fontSize:      tokens.typography.fontSize.xs,
            color:         'var(--fujin-text-muted)',
            letterSpacing: tokens.typography.letterSpacing.wide,
            textTransform: 'uppercase',
          }}>
            Appearance
          </span>

          <div style={{ display: 'flex', gap: tokens.spacing.scale.xs }}>
            <ModeButton label="Light" active={mode === 'light'} onClick={() => { if (mode !== 'light') toggle(); }} />
            <ModeButton label="Dark"  active={mode === 'dark'}  onClick={() => { if (mode !== 'dark')  toggle(); }} />
          </div>

          {/* Reserved for preset colour swatches */}
        </div>
      </Popover.Dropdown>
    </Popover>
  );
}
