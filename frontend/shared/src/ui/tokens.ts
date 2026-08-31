/**
 * Minimal design tokens for the touch-friendly UI kit (FD frontend-components.md).
 * Inline style objects are used instead of CSS Modules to keep the ESM build
 * zero-config and fully typed; tokens centralize the few shared values.
 */
export const tokens = {
  color: {
    primary: '#2563eb',
    primaryText: '#ffffff',
    surface: '#ffffff',
    border: '#e2e8f0',
    text: '#1e293b',
    danger: '#dc2626',
    dangerBg: '#fef2f2',
    overlay: 'rgba(15, 23, 42, 0.5)',
    muted: '#64748b',
  },
  radius: '10px',
  // Touch target minimum (usability NFR): 44px.
  touchTarget: '44px',
  space: (n: number): string => `${n * 4}px`,
} as const;

/** Allow only http(s) image URLs (SP-03, XSS-safe): blocks javascript:/data: schemes. */
export function safeImageUrl(url: string | null | undefined): string | undefined {
  if (!url) return undefined;
  try {
    const parsed = new URL(url, 'https://placeholder.local');
    return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? url : undefined;
  } catch {
    return undefined;
  }
}
