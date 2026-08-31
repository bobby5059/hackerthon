// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';
import { Button } from './Button';
import { ErrorBanner } from './ErrorBanner';
import { Spinner } from './Spinner';
import { Modal } from './Modal';
import { safeImageUrl } from './tokens';

afterEach(cleanup);

describe('Button', () => {
  it('renders with a stable data-testid and fires onClick', () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>주문</Button>);
    const btn = screen.getByTestId('ui-button');
    fireEvent.click(btn);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('does not fire onClick when disabled', () => {
    const onClick = vi.fn();
    render(
      <Button onClick={onClick} disabled>
        주문
      </Button>,
    );
    fireEvent.click(screen.getByTestId('ui-button'));
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe('ErrorBanner', () => {
  it('has role=alert and renders a retry button when onRetry is given', () => {
    const onRetry = vi.fn();
    render(<ErrorBanner message="오류" onRetry={onRetry} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('ui-error-banner-retry'));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('omits the retry button without onRetry', () => {
    render(<ErrorBanner message="오류" />);
    expect(screen.queryByTestId('ui-error-banner-retry')).toBeNull();
  });
});

describe('Spinner', () => {
  it('exposes role=status with an accessible label', () => {
    render(<Spinner label="주문 불러오는 중" />);
    expect(screen.getByRole('status')).toHaveTextContent('주문 불러오는 중');
  });
});

describe('Modal', () => {
  it('renders nothing when closed', () => {
    render(
      <Modal open={false} onClose={() => {}}>
        내용
      </Modal>,
    );
    expect(screen.queryByTestId('ui-modal')).toBeNull();
  });

  it('renders a labelled dialog when open', () => {
    render(
      <Modal open onClose={() => {}} title="확인">
        <button>확인</button>
      </Modal>,
    );
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby');
  });

  it('closes on ESC', () => {
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose}>
        <button>x</button>
      </Modal>,
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('closes on overlay click but not on dialog click', () => {
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose}>
        <button>x</button>
      </Modal>,
    );
    fireEvent.click(
      screen.getByTestId ? screen.getByTestId('ui-modal') : screen.getByRole('dialog'),
    );
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId('ui-modal-overlay'));
    expect(onClose).toHaveBeenCalledOnce();
  });
});

describe('safeImageUrl (SP-03 XSS-safe)', () => {
  it('allows http(s) URLs', () => {
    expect(safeImageUrl('https://cdn/x.png')).toBe('https://cdn/x.png');
    expect(safeImageUrl('http://cdn/x.png')).toBe('http://cdn/x.png');
  });
  it('blocks javascript: and returns undefined for empty', () => {
    expect(safeImageUrl('javascript:alert(1)')).toBeUndefined();
    expect(safeImageUrl(null)).toBeUndefined();
  });
});
