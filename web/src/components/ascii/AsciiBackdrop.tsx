'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';

const LazyAscii = dynamic(() => import('./AsciiScene'), {
  ssr: false,
  loading: () => null,
});

const mobileTexture = `] 0 { 1 * } / > [ 0 ]   { 1 }  *  / 0
  { } 1 < 0  *  ]   [ 1 /   > 0   { }
0   / 1 ]  { * }    < 0 [ 1 ]   /
  [ 0 ]   *  { 1 }  /  >   0  < 1
{ 1 }   /   0 [ ]  *  < 1   { 0 }
  / 0   [ 1 ]   { }  *   > 0   /
1   { }  *   [ 0 ]   /  <   1  >
  < 0  /   { 1 }   [ ]  *  0   ]`;

function MobileAsciiTexture() {
  return (
    <pre className="absolute inset-0 overflow-hidden whitespace-pre-wrap px-4 pt-16 font-mono text-[11px] leading-[1.9] text-white/[0.13] opacity-90 [mask-image:linear-gradient(to_bottom,rgba(0,0,0,0.75),rgba(0,0,0,0.38)_48%,rgba(0,0,0,0.15))]">
      {mobileTexture}
    </pre>
  );
}

export function AsciiBackdrop() {
  const [shouldRenderScene, setShouldRenderScene] = useState(false);

  useEffect(() => {
    const media = window.matchMedia('(min-width: 640px)');
    const update = () => setShouldRenderScene(media.matches);

    update();
    media.addEventListener('change', update);

    return () => media.removeEventListener('change', update);
  }, []);

  return (
    <div
      className="absolute inset-0 z-0 h-full w-full overflow-hidden pointer-events-none [&_canvas]:!h-full [&_canvas]:!w-full [&_canvas]:block"
      aria-hidden
    >
      {shouldRenderScene ? <LazyAscii /> : <MobileAsciiTexture />}
    </div>
  );
}
