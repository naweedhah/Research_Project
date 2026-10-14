"use client";

import { Suspense, useLayoutEffect, useRef, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { ContactShadows, OrbitControls, OrthographicCamera } from "@react-three/drei";
import { Box3, NoToneMapping, OrthographicCamera as ThreeOrtho, SRGBColorSpace } from "three";
import { ChildModel, fitZoom } from "./ChildModel";

type SceneProps = {
  riskIntensity?: number;
  reducedMotion?: boolean;
  darkStage?: boolean;
  onContextLost?: () => void;
  neutral?: boolean;
  autoRotate?: boolean;
};

export function ChildModelScene({
  riskIntensity = 0.5,
  reducedMotion = false,
  darkStage = false,
  onContextLost,
  neutral = false,
  autoRotate = true,
}: SceneProps) {
  return (
    <Canvas
      orthographic
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      onCreated={({ gl }) => {
        gl.outputColorSpace = SRGBColorSpace;
        gl.toneMapping = NoToneMapping;
        gl.setClearColor(0x000000, 0);
        gl.domElement.addEventListener("webglcontextlost", (e) => {
          e.preventDefault();
          onContextLost?.();
        });
      }}
      style={{ width: "100%", height: "100%", touchAction: "none", cursor: "grab", background: "transparent" }}
      aria-hidden
    >
      <Suspense fallback={null}>
        <SceneContents
          riskIntensity={riskIntensity}
          reducedMotion={reducedMotion}
          darkStage={darkStage}
          neutral={neutral}
          autoRotate={autoRotate}
        />
      </Suspense>
    </Canvas>
  );
}

function SceneContents({
  riskIntensity,
  reducedMotion,
  darkStage,
  neutral,
  autoRotate,
}: {
  riskIntensity: number;
  reducedMotion: boolean;
  darkStage: boolean;
  neutral: boolean;
  autoRotate: boolean;
}) {
  const [bounds, setBounds] = useState<Box3 | null>(null);
  const camRef = useRef<ThreeOrtho>(null);

  return (
    <>
      <AutoFitCamera bounds={bounds} camRef={camRef} />
      <ambientLight intensity={darkStage ? 1.1 : 0.95} />
      <directionalLight position={[2, 4, 6]} intensity={darkStage ? 1.35 : 1.15} color={darkStage ? "#f8fafc" : "#fff8f0"} />
      <directionalLight position={[-3, 2, 4]} intensity={darkStage ? 0.55 : 0.45} color={darkStage ? "#93c5fd" : "#dbeafe"} />
      <hemisphereLight args={[darkStage ? "#e2e8f0" : "#ffffff", darkStage ? "#1e293b" : "#e2e8f0", darkStage ? 0.65 : 0.55]} />
      <ChildModel
        riskIntensity={riskIntensity}
        reducedMotion={reducedMotion}
        onBoundsChange={setBounds}
        neutral={neutral}
      />
      <ContactShadows position={[0, -0.88, 0]} opacity={darkStage ? 0.35 : 0.14} scale={2.2} blur={2.4} far={1.2} color={darkStage ? "#334155" : "#64748b"} />
      <OrbitControls
        enablePan={false}
        enableZoom={false}
        enableDamping
        dampingFactor={0.06}
        rotateSpeed={0.9}
        autoRotate={autoRotate && !reducedMotion}
        autoRotateSpeed={1.15}
        minPolarAngle={Math.PI / 2}
        maxPolarAngle={Math.PI / 2}
      />
    </>
  );
}

function AutoFitCamera({
  bounds,
  camRef,
}: {
  bounds: Box3 | null;
  camRef: React.RefObject<ThreeOrtho | null>;
}) {
  const { size } = useThree();

  useLayoutEffect(() => {
    const camera = camRef.current;
    if (!bounds || !camera) return;
    camera.position.set(0, 0, 8);
    camera.lookAt(0, 0, 0);
    camera.zoom = fitZoom(bounds, size.width, size.height);
    camera.updateProjectionMatrix();
  }, [bounds, size.width, size.height, camRef]);

  return <OrthographicCamera ref={camRef} makeDefault near={0.1} far={50} />;
}
