'use client';

import { useFrame, useThree } from '@react-three/fiber';
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

const CHARSET = '{}[]<>/\\|=+-_*:;01';
const MAX_RIPPLES = 6;
const RESTORE_EPSILON = 0.001;
const PRESS_ATTACK_SPEED = 18;
const PRESS_RELEASE_SPEED = 3.4;
const HOLD_GROW_ATTACK_SPEED = 5.5;
const HOLD_GROW_RELEASE_SPEED = 2.2;

type InstancePoint = {
  phase: number;
  sx: number;
  sy: number;
  x: number;
  y: number;
  z: number;
};

type MeshBucket = {
  mesh: THREE.InstancedMesh;
  points: InstancePoint[];
};

type Ripple = {
  age: number;
  duration: number;
  radius: number;
  strength: number;
  x: number;
  y: number;
};

function computeGrid(viewportWidth: number, viewportHeight: number, screenWidth: number) {
  const spacing = screenWidth < 440 ? 0.15 : screenWidth < 720 ? 0.145 : 0.135;
  const widthWithDrift = viewportWidth + 3.4;
  const heightWithDrift = viewportHeight + 3;

  return {
    cols: Math.max(34, Math.ceil(widthWithDrift / spacing)),
    rows: Math.max(44, Math.ceil(heightWithDrift / spacing)),
    spacing,
  };
}

function damp(current: number, target: number, speed: number, delta: number) {
  return current + (target - current) * (1 - Math.exp(-speed * delta));
}

function smoothstep01(value: number) {
  const t = THREE.MathUtils.clamp(value, 0, 1);
  return t * t * (3 - 2 * t);
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
  const bucketsRef = useRef<MeshBucket[]>([]);
  const matrixRef = useRef(new THREE.Matrix4());
  const positionRef = useRef(new THREE.Vector3());
  const quaternionRef = useRef(new THREE.Quaternion());
  const scaleRef = useRef(new THREE.Vector3());
  const interactionRef = useRef({
    active: false,
    holdGrow: 0,
    holdTime: 0,
    lastRippleAt: 0,
    lastRippleX: 0,
    lastRippleY: 0,
    lastWorldX: 0,
    lastWorldY: 0,
    needsRestore: false,
    press: 0,
    pointerDown: false,
    ripples: [] as Ripple[],
    targetWorldX: 0,
    targetWorldY: 0,
    targetX: 0,
    targetY: 0,
    worldX: 0,
    worldY: 0,
    x: 0,
    y: 0,
  });
  const { size, viewport } = useThree();
  const grid = useMemo(
    () => computeGrid(viewport.width, viewport.height, size.width),
    [size.width, viewport.height, viewport.width],
  );
  const reduced = useMotionPreference();

  const geo = useMemo(() => new THREE.PlaneGeometry(1, 1.22), []);

  const textures = useMemo(() => {
    const color = '#f2f2ee';
    const unique = Array.from(new Set(CHARSET.split('')));
    const map: Record<string, THREE.CanvasTexture> = {};
    for (const ch of unique) {
      map[ch] = createCharTexture(ch, color);
    }
    return map;
  }, []);

  useEffect(() => {
    const interaction = interactionRef.current;

    const updateTarget = (clientX: number, clientY: number) => {
      interaction.active = true;
      interaction.targetX = (clientX / window.innerWidth - 0.5) * 2;
      interaction.targetY = (clientY / window.innerHeight - 0.5) * 2;

      const point = {
        x: interaction.targetX * viewport.width * 0.5,
        y: -interaction.targetY * viewport.height * 0.5,
      };

      interaction.targetWorldX = point.x;
      interaction.targetWorldY = point.y;

      return point;
    };

    const addRipple = (
      x: number,
      y: number,
      strength: number,
      timestamp: number,
    ) => {
      interaction.ripples.push({
        age: 0,
        duration: 0.58,
        radius: Math.max(0.86, Math.min(viewport.width, viewport.height) * 0.2),
        strength,
        x,
        y,
      });
      if (interaction.ripples.length > MAX_RIPPLES) {
        interaction.ripples.splice(0, interaction.ripples.length - MAX_RIPPLES);
      }
      interaction.lastRippleAt = timestamp;
      interaction.lastRippleX = x;
      interaction.lastRippleY = y;
      interaction.needsRestore = true;
    };

    const onPointerMove = (event: PointerEvent) => {
      const events =
        typeof event.getCoalescedEvents === 'function'
          ? event.getCoalescedEvents()
          : [];
      const pointerEvent = events.at(-1) ?? event;
      const point = updateTarget(pointerEvent.clientX, pointerEvent.clientY);
      if (!interaction.pointerDown) return;

      const moveX = point.x - interaction.lastWorldX;
      const moveY = point.y - interaction.lastWorldY;
      const moved = Math.hypot(moveX, moveY);
      const rippleDx = point.x - interaction.lastRippleX;
      const rippleDy = point.y - interaction.lastRippleY;
      const rippleDistance = Math.hypot(rippleDx, rippleDy);
      const elapsed = pointerEvent.timeStamp - interaction.lastRippleAt;

      interaction.lastWorldX = point.x;
      interaction.lastWorldY = point.y;

      if (rippleDistance > 0.28 || (moved > 0.04 && elapsed > 70)) {
        addRipple(point.x, point.y, 0.42 + Math.min(0.32, moved * 1.2), pointerEvent.timeStamp);
      }
    };

    const onPointerDown = (event: PointerEvent) => {
      if (event.pointerType === 'mouse' && event.button !== 0) return;
      const point = updateTarget(event.clientX, event.clientY);
      interaction.pointerDown = true;
      interaction.holdGrow = 0;
      interaction.holdTime = 0;
      interaction.press = Math.max(interaction.press, 0.35);
      interaction.worldX = point.x;
      interaction.worldY = point.y;
      interaction.lastWorldX = point.x;
      interaction.lastWorldY = point.y;
      addRipple(point.x, point.y, 0.92, event.timeStamp);
    };

    const onPointerUp = (event: PointerEvent) => {
      if (!interaction.pointerDown) return;
      interaction.pointerDown = false;
      addRipple(interaction.targetWorldX, interaction.targetWorldY, 0.28, event.timeStamp);
    };

    const onPointerLeave = () => {
      interaction.active = false;
      interaction.pointerDown = false;
      interaction.targetX = 0;
      interaction.targetY = 0;
    };

    window.addEventListener('pointermove', onPointerMove, { passive: true });
    window.addEventListener('pointerdown', onPointerDown, { passive: true });
    window.addEventListener('pointerup', onPointerUp, { passive: true });
    window.addEventListener('pointercancel', onPointerUp, { passive: true });
    document.documentElement.addEventListener('pointerleave', onPointerLeave);

    return () => {
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('pointerup', onPointerUp);
      window.removeEventListener('pointercancel', onPointerUp);
      document.documentElement.removeEventListener('pointerleave', onPointerLeave);
    };
  }, [viewport.height, viewport.width]);

  useLayoutEffect(() => {
    const group = groupRef.current;
    if (!group) return;

    const clearMeshes = () => {
      bucketsRef.current = [];
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
    const buckets = new Map<string, InstancePoint[]>();

    let seed = 0xdeec;
    const rnd = () => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return (seed >>> 8) / 0xffffff;
    };

    for (let iy = 0; iy < rows; iy++) {
      for (let ix = 0; ix < cols; ix++) {
        const x = (ix - (cols - 1) / 2) * spacing;
        const y = (iy - (rows - 1) / 2) * spacing;
        const ch = chars[Math.floor(rnd() * chars.length)]!;
        const sx = spacing * (0.78 + rnd() * 0.18);
        const sy = spacing * (0.95 + rnd() * 0.2);
        const point = {
          phase: rnd() * Math.PI * 2,
          sx,
          sy,
          x: x + (rnd() - 0.5) * spacing * 0.45,
          y: y + (rnd() - 0.5) * spacing * 0.45,
          z: (rnd() - 0.5) * 1.6,
        };
        if (!buckets.has(ch)) buckets.set(ch, []);
        buckets.get(ch)!.push(point);
      }
    }

    buckets.forEach((points, ch) => {
      const tex = textures[ch];
      if (!tex) return;
      const mat = new THREE.MeshBasicMaterial({
        map: tex,
        transparent: true,
        opacity: reduced ? 0.12 : 0.31,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      });
      const mesh = new THREE.InstancedMesh(geo, mat, points.length);
      mesh.frustumCulled = false;
      points.forEach((point, i) => {
        matrixRef.current.compose(
          positionRef.current.set(point.x, point.y, point.z),
          quaternionRef.current.identity(),
          scaleRef.current.set(point.sx, point.sy, 1),
        );
        mesh.setMatrixAt(i, matrixRef.current);
      });
      mesh.instanceMatrix.needsUpdate = true;
      group.add(mesh);
      bucketsRef.current.push({ mesh, points });
    });

    return () => {
      clearMeshes();
    };
  }, [geo, grid, textures, reduced]);

  useFrame((_, delta) => {
    const g = groupRef.current;
    if (!g || reduced) return;
    const t = performance.now() / 1000;
    const interaction = interactionRef.current;
    const pointerSpeed = interaction.pointerDown ? 32 : 16;
    const pressTarget = interaction.pointerDown ? 1 : 0;

    interaction.x = damp(interaction.x, interaction.targetX, pointerSpeed, delta);
    interaction.y = damp(interaction.y, interaction.targetY, pointerSpeed, delta);
    interaction.worldX = damp(interaction.worldX, interaction.targetWorldX, pointerSpeed * 1.15, delta);
    interaction.worldY = damp(interaction.worldY, interaction.targetWorldY, pointerSpeed * 1.15, delta);
    interaction.press = damp(
      interaction.press,
      pressTarget,
      interaction.pointerDown ? PRESS_ATTACK_SPEED : PRESS_RELEASE_SPEED,
      delta,
    );
    if (interaction.pointerDown) {
      interaction.holdTime = Math.min(interaction.holdTime + delta, 1.15);
    } else {
      interaction.holdTime = 0;
    }
    const holdGrowTarget = interaction.pointerDown
      ? smoothstep01(interaction.holdTime / 1.05)
      : 0;
    interaction.holdGrow = damp(
      interaction.holdGrow,
      holdGrowTarget,
      interaction.pointerDown ? HOLD_GROW_ATTACK_SPEED : HOLD_GROW_RELEASE_SPEED,
      delta,
    );

    for (let i = interaction.ripples.length - 1; i >= 0; i--) {
      const ripple = interaction.ripples[i]!;
      ripple.age += delta;
      if (ripple.age >= ripple.duration) {
        interaction.ripples.splice(i, 1);
      }
    }

    const idleX = Math.sin(t * 0.06) * 0.22;
    const idleY = Math.cos(t * 0.045) * 0.16;

    g.rotation.x = damp(g.rotation.x, -interaction.y * 0.027, 9, delta);
    g.rotation.y = damp(g.rotation.y, interaction.x * 0.044, 9, delta);
    g.rotation.z = Math.sin(t * 0.14) * 0.01 + interaction.x * 0.006;
    g.position.x = damp(g.position.x, idleX + interaction.x * 0.24, 11, delta);
    g.position.y = damp(g.position.y, idleY - interaction.y * 0.13, 11, delta);
    g.scale.setScalar(1 + interaction.holdGrow * 0.024);

    const opacity =
      0.31 +
      (interaction.active ? 0.018 : 0) +
      interaction.press * 0.026 +
      interaction.holdGrow * 0.014;
    for (let i = 0; i < g.children.length; i++) {
      const mesh = g.children[i] as THREE.InstancedMesh;
      const mat = mesh.material as THREE.MeshBasicMaterial;
      mat.opacity = opacity;
    }

    const hasRipples = interaction.ripples.length > 0;
    const hasHold =
      interaction.press > RESTORE_EPSILON ||
      interaction.holdGrow > RESTORE_EPSILON;
    const hasActiveDeformation = hasRipples || hasHold;
    if (!hasActiveDeformation && !interaction.needsRestore) return;

    const holdRadius = Math.max(0.92, Math.min(viewport.width, viewport.height) * 0.22);
    const holdRadiusSq = holdRadius * holdRadius;
    const holdStrength = interaction.press * (0.76 + interaction.holdGrow * 0.34);
    const pulse = 0.76 + Math.sin(t * 5.2) * 0.1;

    for (let bucketIndex = 0; bucketIndex < bucketsRef.current.length; bucketIndex++) {
      const { mesh, points } = bucketsRef.current[bucketIndex]!;
      for (let index = 0; index < points.length; index++) {
        const point = points[index]!;
        let x = point.x;
        let y = point.y;
        let z = point.z;
        let scale = 1;

        if (holdStrength > RESTORE_EPSILON) {
          const dx = point.x - interaction.worldX;
          const dy = point.y - interaction.worldY;
          const distSq = dx * dx + dy * dy;

          if (distSq < holdRadiusSq) {
            const dist = Math.sqrt(distSq) || 1;
            const falloff = smoothstep01(1 - dist / holdRadius);
            const influence =
              holdStrength *
              falloff *
              (pulse + Math.sin(point.phase + t * 3.4) * 0.08);
            const push = influence * (0.34 + interaction.holdGrow * 0.2);
            const spin = Math.sin(point.phase + t * 2.8) * influence * 0.1;

            x += (dx / dist) * push - (dy / dist) * spin;
            y += (dy / dist) * push + (dx / dist) * spin;
            z += influence * (0.58 + Math.cos(point.phase + t * 2.2) * 0.16);
            scale += influence * (0.28 + interaction.holdGrow * 0.26);
          }
        }

        if (hasRipples) {
          for (let rippleIndex = 0; rippleIndex < interaction.ripples.length; rippleIndex++) {
            const ripple = interaction.ripples[rippleIndex]!;
            const progress = ripple.age / ripple.duration;
            const envelope = Math.sin(progress * Math.PI);
            const dx = point.x - ripple.x;
            const dy = point.y - ripple.y;
            const wave = ripple.radius * (0.18 + progress * 0.82);
            const waveWidth = ripple.radius * 0.34;
            const maxReach = wave + waveWidth * 2.4;
            const distSq = dx * dx + dy * dy;
            const coreRadius = ripple.radius * 0.45;

            if (distSq > maxReach * maxReach && distSq > coreRadius * coreRadius) {
              continue;
            }

            const dist = Math.sqrt(distSq) || 1;
            const shellOffset = (dist - wave) / waveWidth;
            const shell =
              Math.abs(shellOffset) < 2.4 ? Math.exp(-(shellOffset * shellOffset)) : 0;
            const core =
              distSq < coreRadius * coreRadius
                ? Math.exp(-(distSq / (coreRadius * coreRadius))) * (1 - progress)
                : 0;
            const influence = ripple.strength * envelope * (shell + core * 0.32);

            if (influence > 0.003) {
              const spin = Math.sin(point.phase + progress * Math.PI * 4) * influence * 0.16;
              const push = influence * 0.5;

              x += (dx / dist) * push - (dy / dist) * spin;
              y += (dy / dist) * push + (dx / dist) * spin;
              z += influence * Math.cos(point.phase + progress * Math.PI * 3) * 0.78;
              scale += influence * 0.48;
            }
          }
        }

        matrixRef.current.compose(
          positionRef.current.set(x, y, z),
          quaternionRef.current.identity(),
          scaleRef.current.set(point.sx * scale, point.sy * scale, 1),
        );
        mesh.setMatrixAt(index, matrixRef.current);
      }
      mesh.instanceMatrix.needsUpdate = true;
    }

    interaction.needsRestore = hasActiveDeformation;
  });

  return (
    <>
      <fogExp2 attach="fog" args={[0x05070b, reduced ? 0.08 : 0.045]} />
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
