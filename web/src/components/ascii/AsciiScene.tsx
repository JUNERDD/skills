'use client';

import { Canvas } from '@react-three/fiber';
import { AsciiField } from './AsciiField';

type AsciiSceneProps = {
  onReady?: () => void;
};

export default function AsciiScene({ onReady }: AsciiSceneProps) {
  return (
    <Canvas
      className="block h-full w-full bg-[color:var(--surface-0)]"
      dpr={[1, 1.5]}
      gl={{
        alpha: false,
        antialias: false,
        depth: true,
        premultipliedAlpha: false,
        stencil: false,
      }}
      onCreated={({ gl }) => {
        gl.setClearColor('#050505', 1);
        gl.clear(true, true, true);
        if (typeof window !== 'undefined') {
          gl.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
        }
        onReady?.();
      }}
      camera={{
        position: [0, 0, 9.2],
        fov: 38,
        near: 0.1,
        far: 42,
      }}
    >
      <AsciiField />
    </Canvas>
  );
}
