'use client';

import dynamic from 'next/dynamic';

const LazyAscii = dynamic(() => import('./AsciiScene'), {
  ssr: false,
  loading: () => null,
});

export function AsciiBackdrop() {
  return (
    <div
      className="fixed inset-0 z-0 h-full w-full overflow-hidden pointer-events-none [&_canvas]:block"
      aria-hidden
    >
      <LazyAscii />
    </div>
  );
}
