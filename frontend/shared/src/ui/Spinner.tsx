import type { CSSProperties } from 'react';
import { tokens } from './tokens';

export interface SpinnerProps {
  /** Diameter in px. */
  size?: number;
  label?: string;
  'data-testid'?: string;
}

/** Accessible loading indicator (role=status). */
export function Spinner({
  size = 24,
  label = '로딩 중',
  'data-testid': testId = 'ui-spinner',
}: SpinnerProps) {
  const style: CSSProperties = {
    display: 'inline-block',
    width: size,
    height: size,
    border: `3px solid ${tokens.color.border}`,
    borderTopColor: tokens.color.primary,
    borderRadius: '50%',
    animation: 'tos-spin 0.8s linear infinite',
  };
  return (
    <span role="status" aria-live="polite" data-testid={testId}>
      <span style={style} aria-hidden="true" />
      <span
        style={{
          position: 'absolute',
          width: 1,
          height: 1,
          overflow: 'hidden',
          clip: 'rect(0 0 0 0)',
        }}
      >
        {label}
      </span>
    </span>
  );
}
