import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from 'react';
import { tokens } from './tokens';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  /** Stable automation hook. */
  'data-testid'?: string;
  children: ReactNode;
}

const base: CSSProperties = {
  minHeight: tokens.touchTarget,
  padding: `${tokens.space(2)} ${tokens.space(4)}`,
  borderRadius: tokens.radius,
  border: `1px solid ${tokens.color.border}`,
  fontSize: '16px',
  cursor: 'pointer',
};

const variantStyle: Record<NonNullable<ButtonProps['variant']>, CSSProperties> = {
  primary: {
    background: tokens.color.primary,
    color: tokens.color.primaryText,
    borderColor: tokens.color.primary,
  },
  secondary: { background: tokens.color.surface, color: tokens.color.text },
  danger: {
    background: tokens.color.danger,
    color: '#fff',
    borderColor: tokens.color.danger,
  },
};

/** Stateless, controlled touch-friendly button (NFR-design MP-03). */
export function Button({
  variant = 'primary',
  style,
  disabled,
  children,
  'data-testid': testId = 'ui-button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type="button"
      data-testid={testId}
      disabled={disabled}
      style={{
        ...base,
        ...variantStyle[variant],
        ...(disabled ? { opacity: 0.5, cursor: 'not-allowed' } : {}),
        ...style,
      }}
      {...rest}
    >
      {children}
    </button>
  );
}
