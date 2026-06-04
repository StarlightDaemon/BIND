import type { ReactNode } from 'react';
import tokens from '../tokens.json';

export interface SectionHeaderProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function SectionHeader({ title, description, action }: SectionHeaderProps) {
  const containerStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingBottom: `${tokens.spacing.scale.sm}px`,
    borderBottom: `1px solid var(--fujin-border-subtle)`,
  };

  const textGroupStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: `${tokens.spacing.base}px`,
  };

  const titleStyle: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.base,
    fontSize: tokens.typography.fontSize.sm,
    fontWeight: tokens.typography.fontWeight.semibold,
    color: 'var(--fujin-text-primary)',
    letterSpacing: tokens.typography.letterSpacing.wide,
    textTransform: 'uppercase',
    margin: 0,
  };

  const descriptionStyle: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.base,
    fontSize: tokens.typography.fontSize.xs,
    color: 'var(--fujin-text-muted)',
    margin: 0,
  };

  return (
    <div style={containerStyle}>
      <div style={textGroupStyle}>
        <div style={titleStyle}>{title}</div>
        {description && <div style={descriptionStyle}>{description}</div>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
