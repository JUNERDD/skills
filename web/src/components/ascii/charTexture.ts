'use client';

import * as THREE from 'three';

/** 单字符贴图：用于 InstancedMesh 共享材质 */
export function createCharTexture(char: string, color: string) {
  const size = 96;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    throw new Error('2D context unavailable');
  }
  ctx.fillStyle = '#020403';
  ctx.fillRect(0, 0, size, size);
  ctx.fillStyle = color;
  ctx.font = '600 64px ui-monospace, monospace';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(char, size / 2, size / 2 + 2);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.magFilter = THREE.NearestFilter;
  tex.minFilter = THREE.NearestFilter;
  tex.needsUpdate = true;
  return tex;
}
