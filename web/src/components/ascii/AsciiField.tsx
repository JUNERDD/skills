'use client';

import { useFrame } from '@react-three/fiber';
import {
  Suspense,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import * as THREE from 'three';
import { createCharTexture } from './charTexture';

const CHARSET = '.:*#@+-|/\\01x^~`';

function computeGrid(w: number) {
  if (w < 440) return { cols: 18, rows: 13, spacing: 0.19 };
  if (w < 720) return { cols: 26, rows: 18, spacing: 0.175 };
  return { cols: 46, rows: 28, spacing: 0.16 };
}

function useWindowGrid() {
  const [grid, setGrid] = useState(() =>
    typeof window !== 'undefined'
      ? computeGrid(window.innerWidth)
      : { cols: 36, rows: 22, spacing: 0.16 },
  );

  useEffect(() => {
    const onResize = () => setGrid(computeGrid(window.innerWidth));
    onResize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  return grid;
}

function useMotionPreference() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const apply = () => setReduced(mq.matches);
    apply();
    mq.addEventListener('change', apply);
    return () => mq.removeEventListener('change', apply);
  }, []);
  return reduced;
}

function AsciiFieldInner() {
  const groupRef = useRef<THREE.Group>(null);
  const grid = useWindowGrid();
  const reduced = useMotionPreference();

  const geo = useMemo(() => new THREE.PlaneGeometry(1, 1.22), []);

  const textures = useMemo(() => {
    const color = '#8ef0a4';
    const unique = Array.from(new Set(CHARSET.split('')));
    const map: Record<string, THREE.CanvasTexture> = {};
    for (const ch of unique) {
      map[ch] = createCharTexture(ch, color);
    }
    return map;
  }, []);

  useLayoutEffect(() => {
    const group = groupRef.current;
    if (!group) return;

    const clearMeshes = () => {
      while (group.children.length) {
        const child = group.children[0] as THREE.InstancedMesh;
        group.remove(child);
        const mat = child.material as THREE.MeshBasicMaterial;
        mat.map = null;
        mat.dispose();
      }
    };

    clearMeshes();

    const { cols, rows, spacing } = grid;
    const chars = Array.from(new Set(CHARSET.split('')));
    const buckets = new Map<string, THREE.Matrix4[]>();

    let seed = 0xdeec;
    const rnd = () => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return (seed >>> 8) / 0xffffff;
    };

    for (let iy = 0; iy < rows; iy++) {
      for (let ix = 0; ix < cols; ix++) {
        const x = (ix - cols / 2) * spacing;
        const y = (iy - rows / 2) * spacing;
        const ch = chars[Math.floor(rnd() * chars.length)]!;
        const sx = spacing * (0.78 + rnd() * 0.18);
        const sy = spacing * (0.95 + rnd() * 0.2);
        const m = new THREE.Matrix4().compose(
          new THREE.Vector3(
            x + (rnd() - 0.5) * spacing * 0.45,
            y + (rnd() - 0.5) * spacing * 0.45,
            (rnd() - 0.5) * 0.9,
          ),
          new THREE.Quaternion(),
          new THREE.Vector3(sx, sy, 1),
        );
        if (!buckets.has(ch)) buckets.set(ch, []);
        buckets.get(ch)!.push(m);
      }
    }

    buckets.forEach((matrices, ch) => {
      const tex = textures[ch];
      if (!tex) return;
      const mat = new THREE.MeshBasicMaterial({
        map: tex,
        transparent: true,
        opacity: reduced ? 0.1 : 0.24,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      });
      const mesh = new THREE.InstancedMesh(geo, mat, matrices.length);
      mesh.frustumCulled = false;
      matrices.forEach((matrix, i) => mesh.setMatrixAt(i, matrix));
      mesh.instanceMatrix.needsUpdate = true;
      group.add(mesh);
    });

    return () => {
      clearMeshes();
    };
  }, [geo, grid, textures, reduced]);

  useFrame(() => {
    const g = groupRef.current;
    if (!g || reduced) return;
    const t = performance.now() / 1000;
    g.rotation.z = Math.sin(t * 0.18) * 0.032;
    g.position.x = Math.sin(t * 0.07) * 0.42;
    g.position.y = Math.cos(t * 0.05) * 0.28;
  });

  return (
    <>
      <fogExp2 attach="fog" args={[0x040604, reduced ? 0.09 : 0.062]} />
      <group ref={groupRef} />
    </>
  );
}

export function AsciiField() {
  return (
    <Suspense fallback={null}>
      <AsciiFieldInner />
    </Suspense>
  );
}
