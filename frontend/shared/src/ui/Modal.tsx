import { useEffect, useRef } from 'react';
import type { CSSProperties, ReactNode } from 'react';
import { tokens } from './tokens';

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  /** Close when the overlay (outside the dialog) is clicked. Default true. */
  closeOnOverlay?: boolean;
  'data-testid'?: string;
}

const overlayStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: tokens.color.overlay,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: tokens.space(4),
  zIndex: 1000,
};

const dialogStyle: CSSProperties = {
  background: tokens.color.surface,
  color: tokens.color.text,
  borderRadius: tokens.radius,
  padding: tokens.space(5),
  maxWidth: '90vw',
  maxHeight: '90vh',
  overflow: 'auto',
  minWidth: '280px',
};

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

/**
 * Accessible modal dialog (NFR-design MP-03): role=dialog + aria-modal,
 * focus trap, ESC to close, overlay-click to close, body scroll lock.
 * Stateless/controlled — visibility is owned by the parent via `open`.
 */
export function Modal({
  open,
  onClose,
  title,
  children,
  closeOnOverlay = true,
  'data-testid': testId = 'ui-modal',
}: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    // Move focus into the dialog.
    const focusFirst = () => {
      const node = dialogRef.current;
      if (!node) return;
      const focusable = node.querySelectorAll<HTMLElement>(FOCUSABLE);
      (focusable[0] ?? node).focus();
    };
    focusFirst();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== 'Tab') return;
      const node = dialogRef.current;
      if (!node) return;
      const focusable = Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (focusable.length === 0) {
        e.preventDefault();
        return;
      }
      const first = focusable[0]!;
      const last = focusable[focusable.length - 1]!;
      const active = document.activeElement;
      if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', onKeyDown, true);
    return () => {
      document.removeEventListener('keydown', onKeyDown, true);
      document.body.style.overflow = originalOverflow;
      previouslyFocused?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;

  const titleId = `${testId}-title`;

  return (
    <div
      style={overlayStyle}
      data-testid={`${testId}-overlay`}
      onClick={closeOnOverlay ? onClose : undefined}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        tabIndex={-1}
        data-testid={testId}
        style={dialogStyle}
        onClick={(e) => e.stopPropagation()}
      >
        {title && (
          <h2 id={titleId} style={{ marginTop: 0 }} data-testid={`${testId}-title`}>
            {title}
          </h2>
        )}
        {children}
      </div>
    </div>
  );
}
