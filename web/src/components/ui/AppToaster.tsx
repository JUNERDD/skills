'use client';

import { Toaster } from 'sonner';

export function AppToaster() {
  return (
    <Toaster
      position="bottom-right"
      toastOptions={{
        style: {
          background: 'var(--surface-1)',
          border: '1px solid rgba(255,255,255,0.14)',
          borderRadius: '8px',
          color: 'var(--ink)',
          fontFamily: 'var(--font-mono), ui-monospace, monospace',
        },
      }}
    />
  );
}
