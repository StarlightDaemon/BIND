import { Menu, UnstyledButton } from '@mantine/core';
import type { ReactNode } from 'react';
import tokens from '../tokens.json';

export interface ActionMenuItem {
  label: string;
  icon?: ReactNode;
  onClick: () => void;
  danger?: boolean;
  disabled?: boolean;
}

export interface ActionMenuProps {
  items: ActionMenuItem[];
}

export function ActionMenu({ items }: ActionMenuProps) {
  const triggerStyle: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.base,
    fontSize: tokens.typography.fontSize.sm,
    fontWeight: tokens.typography.fontWeight.medium,
    color: 'var(--fujin-text-secondary)',
    padding: `${tokens.spacing.base}px ${tokens.spacing.scale.sm}px`,
    cursor: 'pointer',
    border: `1px solid var(--fujin-border-subtle)`,
    borderRadius: tokens.radius.default,
    background: 'transparent',
  };

  const dropdownStyle: React.CSSProperties = {
    background: 'var(--fujin-bg-elevated)',
    border: `1px solid var(--fujin-border-default)`,
    borderRadius: tokens.radius.default,
    padding: `${tokens.spacing.base}px 0`,
  };

  return (
    <Menu position="bottom-end" offset={tokens.spacing.base} radius={tokens.radius.default}>
      <Menu.Target>
        <UnstyledButton style={triggerStyle}>⋯</UnstyledButton>
      </Menu.Target>
      <Menu.Dropdown style={dropdownStyle}>
        {items.map((item) => (
          <Menu.Item
            key={item.label}
            onClick={item.disabled ? undefined : item.onClick}
            disabled={item.disabled}
            leftSection={item.icon}
            style={{
              fontFamily: tokens.typography.fontFamily.base,
              fontSize: tokens.typography.fontSize.xs,
              color: item.danger
                ? 'var(--fujin-status-danger)'
                : 'var(--fujin-text-secondary)',
              borderRadius: tokens.radius.default,
              opacity: item.disabled ? tokens.opacity.disabled : 1,
            }}
          >
            {item.label}
          </Menu.Item>
        ))}
      </Menu.Dropdown>
    </Menu>
  );
}
