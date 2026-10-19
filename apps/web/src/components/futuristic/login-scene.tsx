"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { Group } from "three";

function Orb({ reduced }: { reduced: boolean }) {
  const group = useRef<Group>(null);
  useFrame((_, delta) => {
    if (reduced || !group.current) return;
    group.current.rotation.y += delta * 0.18;
    group.current.rotation.x += delta * 0.05;
  });
  return (
    <group ref={group}>
      <mesh>
        <sphereGeometry args={[1.05, 64, 64]} />
        <meshPhysicalMaterial color="#d7e6f2" transparent opacity={0.72} roughness={0.25} transmission={0.4} thickness={0.6} clearcoat={1} />
      </mesh>
      <mesh rotation={[Math.PI / 2.4, 0.3, 0]}>
        <torusGeometry args={[1.55, 0.012, 16, 160]} />
        <meshBasicMaterial color="#45C4BB" transparent opacity={0.85} />
      </mesh>
      <mesh rotation={[Math.PI / 1.7, -0.5, 0.4]}>
        <torusGeometry args={[1.85, 0.008, 16, 160]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={0.35} />
      </mesh>
    </group>
  );
}

export default function LoginScene({ reduced }: { reduced: boolean }) {
  return (
    <Canvas dpr={[1, 1.25]} camera={{ position: [0, 0, 4.2], fov: 42 }} gl={{ alpha: true, antialias: true }} className="h-full w-full">
      <ambientLight intensity={0.8} />
      <directionalLight position={[3, 4, 5]} intensity={1.1} color="#ffffff" />
      <directionalLight position={[-4, -2, 3]} intensity={0.5} color="#58D3CA" />
      <Orb reduced={reduced} />
    </Canvas>
  );
}
