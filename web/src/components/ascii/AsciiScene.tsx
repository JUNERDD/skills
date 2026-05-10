'use client';

import { Canvas } from '@react-three/fiber';
import { AsciiField } from './AsciiField';

export default function AsciiScene() {
  return (
    <Canvas
      className="block h-full w-full"
      dpr={[1, 1.5]}
      gl={{ alpha: true, antialias: false, stencil: false, depth: true }}
      onCreated={({ gl }) => {
        gl.setClearColor('#000000', 0);
        if (typeof window !== 'undefined') {
          gl.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
        }
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
