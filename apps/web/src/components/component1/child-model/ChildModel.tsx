"use client";

import { useLayoutEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import { Box3, DoubleSide, Group, Mesh, MeshStandardMaterial, Object3D, Vector3 } from "three";
import { CHILD_MODEL_URL } from "./constants";

const TARGET_HEIGHT = 1.7;
const FLOAT_AMPLITUDE = 0.07;

/** When true, body uses a flat slate look; when false, GLB colours + risk glow. */
export const CHILD_MODEL_NEUTRAL = false;

export function ChildModel({
  riskIntensity = 0.5,
  reducedMotion = false,
  onBoundsChange,
  neutral = CHILD_MODEL_NEUTRAL,
}: {
  riskIntensity?: number;
  reducedMotion?: boolean;
  onBoundsChange?: (box: Box3) => void;
  neutral?: boolean;
}) {
  const gltf = useGLTF(CHILD_MODEL_URL);
  const floatRef = useRef<Group>(null);
  const root = useMemo(() => prepareScene(gltf.scene), [gltf.scene]);

  useLayoutEffect(() => {
    centerModel(root);
    if (neutral) applyNeutralLook(root);
    else applyRiskGlow(root, riskIntensity);
    onBoundsChange?.(new Box3().setFromObject(root));
  }, [root, riskIntensity, onBoundsChange, neutral]);

  useFrame((state) => {
    if (!floatRef.current || reducedMotion) return;
    floatRef.current.position.y = Math.sin(state.clock.elapsedTime * 1.05) * FLOAT_AMPLITUDE;
  });

  return (
    <group ref={floatRef}>
      <primitive object={root} />
    </group>
  );
}

function prepareScene(scene: Object3D) {
  const cloned = scene.clone(true);
  cloned.traverse((obj) => {
    if (!(obj as Mesh).isMesh) return;
    const mesh = obj as Mesh;
    mesh.castShadow = false;
    mesh.receiveShadow = false;
    mesh.frustumCulled = false;
    mesh.material = Array.isArray(mesh.material)
      ? mesh.material.map((m) => m.clone())
      : mesh.material.clone();
    if (mesh.material instanceof MeshStandardMaterial) configureMaterial(mesh.material);
    else if (Array.isArray(mesh.material)) {
      mesh.material.forEach((m) => m instanceof MeshStandardMaterial && configureMaterial(m));
    }
  });
  return cloned;
}

function configureMaterial(material: MeshStandardMaterial) {
  material.side = DoubleSide;
  material.metalness = 0;
  material.roughness = 1;
  if (material.emissiveMap && !material.map) {
    material.map = material.emissiveMap;
    material.color.set(1, 1, 1);
  }
  material.needsUpdate = true;
}

function centerModel(root: Object3D) {
  const box = new Box3().setFromObject(root);
  const size = new Vector3();
  box.getSize(size);
  root.scale.setScalar(TARGET_HEIGHT / Math.max(size.y, 0.0001));
  box.setFromObject(root);
  const center = new Vector3();
  box.getCenter(center);
  root.position.sub(center);
}

function applyNeutralLook(root: Object3D) {
  root.traverse((obj) => {
    if (!(obj as Mesh).isMesh) return;
    const mesh = obj as Mesh;
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) continue;
      material.map = null;
      material.emissiveMap = null;
      material.color.set("#c5ced8");
      material.emissive.set("#e8eef5");
      material.emissiveIntensity = 0.12;
      material.metalness = 0;
      material.roughness = 0.85;
      material.needsUpdate = true;
    }
  });
}

/** Visual metaphor only — scales emissive from the model’s own materials; no geometry change. */
function applyRiskGlow(root: Object3D, risk: number) {
  const k = Math.min(1, Math.max(0, risk));
  root.traverse((obj) => {
    if (!(obj as Mesh).isMesh) return;
    const mesh = obj as Mesh;
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) continue;
      if (material.userData.baseIntensity === undefined) {
        material.userData.baseIntensity = material.emissiveIntensity;
      }
      material.emissiveIntensity = (material.userData.baseIntensity as number) * (0.9 + k * 0.15);
      material.needsUpdate = true;
    }
  });
}

export function fitZoom(box: Box3, width: number, height: number, padding = 1.0) {
  const size = new Vector3();
  box.getSize(size);
  const paddedHeight = size.y * padding + FLOAT_AMPLITUDE * 2;
  const paddedWidth = size.x * padding;
  return Math.min(height / Math.max(paddedHeight, 0.0001), width / Math.max(paddedWidth, 0.0001));
}

useGLTF.preload(CHILD_MODEL_URL);
