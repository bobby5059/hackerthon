import type { CSSProperties, ReactNode } from 'react';
import { tokens } from './tokens';
import { Button } from './Button';

export interface ErrorBannerProps {
  message: ReactNode;
  /** Optional retry action; renders a button when provided. */
  onRetry?: () => void;
  'data-testid'?: string;
}

const style: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: tokens.space(3),
  padding: tokens.space(3),
  background: tokens.color.dangerBg,
  color: tokens.color.danger,
  border: `1px solid ${tokens.color.danger}`,
  borderRadius: tokens.radius,
};

/** Inline error banner (role=alert). Stateless/controlled. */
export function ErrorBanner({
  message,
  onRetry,
  'data-testid': testId = 'ui-error-banner',
}: ErrorBannerProps) {
  return (
    <div role="alert" data-testid={testId} style={style}>
      <span>{message}</span>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry} data-testid={`${testId}-retry`}>
          다시 시도
        </Button>
      )}
    </div>
  );
}
