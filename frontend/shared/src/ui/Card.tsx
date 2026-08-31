import type { CSSProperties, HTMLAttributes, ReactNode } from 'react';
import { tokens } from './tokens';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  'data-testid'?: string;
}

const base: CSSProperties = {
  background: tokens.color.surface,
  border: `1px solid ${tokens.color.border}`,
  borderRadius: tokens.radius,
  padding: tokens.space(4),
  color: tokens.color.text,
};

/** Simple content container. */
export function Card({
  children,
  style,
  'data-testid': testId = 'ui-card',
  ...rest
}: CardProps) {
  return (
    <div data-testid={testId} style={{ ...base, ...style }} {...rest}>
      {children}
    </div>
  );
}
