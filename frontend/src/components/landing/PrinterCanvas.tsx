import { Suspense, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { useGLTF, Environment, Center } from '@react-three/drei'
import { motion } from 'framer-motion'
import type { Group } from 'three'

function PrinterModel() {
  const { scene } = useGLTF('/hp_metal_printer_s100.glb')
  const groupRef = useRef<Group>(null)

  useFrame(({ clock }) => {
    if (!groupRef.current) return
    // Oscillate ±30° (Math.PI/6 radians) — never a full rotation
    groupRef.current.rotation.y =
      Math.sin(clock.elapsedTime * 0.18) * (Math.PI / 6)
  })

  return (
    <group ref={groupRef}>
      <Center>
        <primitive object={scene} />
      </Center>
    </group>
  )
}

function LoadingFallback() {
  return null
}

interface PrinterCanvasProps {
  className?: string
  wrapperOpacity?: number
}

export function PrinterCanvas({
  className,
  wrapperOpacity = 1,
}: PrinterCanvasProps) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0 }}
      animate={{ opacity: wrapperOpacity }}
      transition={{ duration: 0.4, delay: 0, ease: 'easeOut' }}
    >
      <Canvas
        camera={{ position: [0, 0.5, 3.5], fov: 45 }}
        style={{ width: '100%', height: '100%' }}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={1.2} />
        <directionalLight position={[4, 6, 4]} intensity={2} castShadow />
        <directionalLight position={[-4, 2, -4]} intensity={0.6} />
        <Suspense fallback={<LoadingFallback />}>
          <Environment preset='studio' />
          <PrinterModel />
        </Suspense>
      </Canvas>
    </motion.div>
  )
}
