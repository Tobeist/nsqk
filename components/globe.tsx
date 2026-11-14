"use client";
import Image from "next/image";
import {
  Component,
  Suspense,
  useEffect,
  useRef,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Line, useTexture } from "@react-three/drei";
import {
  BufferGeometry,
  Float32BufferAttribute,
  DoubleSide,
  AdditiveBlending,
  BackSide,
  Color,
  SRGBColorSpace,
  Vector3,
  Vector2,
  ShapeUtils,
} from "three";
import { Crosshair, Minus, Plus, RotateCcw } from "lucide-react";
import { intersectedStates, type StateFeature } from "@/lib/geography";
import { regions, type Region } from "@/lib/catalog";
import type { MapRegionValue } from "@/lib/map-layer";
import type { OrbitControls as OrbitControlsType } from "three-stdlib";
const position = (
  lat: number,
  lon: number,
  r = 2,
): [number, number, number] => {
  const p = (lat * Math.PI) / 180,
    t = (lon * Math.PI) / 180;
  return [
    r * Math.cos(p) * Math.cos(t),
    r * Math.sin(p),
    -r * Math.cos(p) * Math.sin(t),
  ];
};
function RegionMark({
  region,
  selected,
  onSelect,
  value,
}: {
  region: Region;
  selected: boolean;
  onSelect: (id: string) => void;
  value?: MapRegionValue;
}) {
  const [w, s, e, n] = region.bbox;
  const boundary: [number, number, number][] = [];
  for (let i = 0; i <= 12; i++)
    boundary.push(position(s, w + ((e - w) * i) / 12, 2.012));
  for (let i = 0; i <= 12; i++)
    boundary.push(position(s + ((n - s) * i) / 12, e, 2.012));
  for (let i = 0; i <= 12; i++)
    boundary.push(position(n, e - ((e - w) * i) / 12, 2.012));
  for (let i = 0; i <= 12; i++)
    boundary.push(position(n - ((n - s) * i) / 12, w, 2.012));
  const positions: number[] = [];
  for (let row = 0; row < 4; row++)
    for (let col = 0; col < 4; col++) {
      const a = position(
          s + ((n - s) * row) / 4,
          w + ((e - w) * col) / 4,
          2.014,
        ),
        b = position(
          s + ((n - s) * row) / 4,
          w + ((e - w) * (col + 1)) / 4,
          2.014,
        ),
        c = position(
          s + ((n - s) * (row + 1)) / 4,
          w + ((e - w) * col) / 4,
          2.014,
        ),
        d = position(
          s + ((n - s) * (row + 1)) / 4,
          w + ((e - w) * (col + 1)) / 4,
          2.014,
        );
      positions.push(...a, ...b, ...c, ...b, ...d, ...c);
    }
  const fill = new BufferGeometry();
  fill.setAttribute("position", new Float32BufferAttribute(positions, 3));
  const crosses =
    value?.statistics &&
    value.statistics.confidenceInterval[0] <= 0 &&
    value.statistics.confidenceInterval[1] >= 0;
  return (
    <group>
      {value?.state === "analyzed" && (
        <mesh
          geometry={fill}
          onClick={(e) => {
            e.stopPropagation();
            onSelect(region.id);
          }}
        >
          <meshBasicMaterial
            color={value.color}
            side={DoubleSide}
            transparent
            opacity={0.9}
          />
        </mesh>
      )}
      <Line
        dashed={!!crosses}
        dashSize={0.016}
        gapSize={0.01}
        points={boundary}
        color={selected ? "#b1ffdf" : (value?.color ?? "#9ac0cc")}
        lineWidth={selected ? 2.6 : 1}
      />
    </group>
  );
}
function StateSurface({ feature }: { feature: StateFeature }) {
  const geometry = useMemo(() => {
    const points: number[] = [];
    function subdivide(a: Vector3, b: Vector3, c: Vector3, depth: number) {
      if (depth === 0) {
        points.push(...a.toArray(), ...b.toArray(), ...c.toArray());
        return;
      }
      const ab = a.clone().add(b).normalize().multiplyScalar(2.006),
        bc = b.clone().add(c).normalize().multiplyScalar(2.006),
        ca = c.clone().add(a).normalize().multiplyScalar(2.006);
      subdivide(a, ab, ca, depth - 1);
      subdivide(ab, b, bc, depth - 1);
      subdivide(ca, bc, c, depth - 1);
      subdivide(ab, bc, ca, depth - 1);
    }
    const polygons =
      feature.geometry.type === "Polygon"
        ? [feature.geometry.coordinates]
        : feature.geometry.type === "MultiPolygon"
          ? feature.geometry.coordinates
          : [];
    for (const polygon of polygons) {
      const rings = polygon.map((ring) =>
        ring.slice(0, -1).map((p) => new Vector2(p[0], p[1])),
      );
      const flat = rings.flat();
      for (const face of ShapeUtils.triangulateShape(
        rings[0],
        rings.slice(1),
      )) {
        const vertices = face.map(
          (i) => new Vector3(...position(flat[i].y, flat[i].x, 2.006)),
        );
        subdivide(vertices[0], vertices[1], vertices[2], 2);
      }
    }
    const g = new BufferGeometry();
    g.setAttribute("position", new Float32BufferAttribute(points, 3));
    return g;
  }, [feature]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  const polygons =
    feature.geometry.type === "Polygon"
      ? [feature.geometry.coordinates]
      : feature.geometry.type === "MultiPolygon"
        ? feature.geometry.coordinates
        : [];
  return (
    <group>
      <mesh geometry={geometry}>
        <meshBasicMaterial
          color="#39878a"
          transparent
          opacity={0.65}
          side={DoubleSide}
        />
      </mesh>
      {polygons.map((polygon, i) => (
        <Line
          key={i}
          points={polygon[0].map((p) => position(p[1], p[0], 2.009))}
          color="#a5e0d7"
          lineWidth={1}
        />
      ))}
    </group>
  );
}
function Earth() {
  const texture = useTexture("/assets/earth-map.png", (texture) => {
    texture.colorSpace = SRGBColorSpace;
  });
  // Equirectangular u=.5 (longitude 0) aligns with the sphere +X axis.
  return (
    <group>
      <mesh>
        <sphereGeometry args={[2, 96, 64]} />
        <meshPhongMaterial
          map={texture}
          color="#c4d8df"
          shininess={14}
          specular={new Color("#31556b")}
        />
      </mesh>
      <mesh>
        <sphereGeometry args={[2.025, 64, 48]} />
        <shaderMaterial
          transparent
          depthWrite={false}
          side={BackSide}
          blending={AdditiveBlending}
          vertexShader={`varying vec3 vN; varying vec3 vP; void main(){vN=normalize(normalMatrix*normal); vec4 p=modelViewMatrix*vec4(position,1.);vP=p.xyz;gl_Position=projectionMatrix*p;}`}
          fragmentShader={`varying vec3 vN;varying vec3 vP;void main(){float f=pow(1.-abs(dot(normalize(vN),normalize(-vP))),3.);gl_FragColor=vec4(.17,.48,.65,f*.5);}`}
        />
      </mesh>
    </group>
  );
}
function Controls({ action }: { action: { type: string; tick: number } }) {
  const ref = useRef<OrbitControlsType>(null);
  const { camera, invalidate } = useThree();
  useEffect(() => {
    if (action.type === "reset")
      camera.position.copy(new Vector3(...position(26, -103, 5.8)));
    if (action.type === "in") camera.position.multiplyScalar(0.85);
    if (action.type === "out") camera.position.multiplyScalar(1.18);
    ref.current?.update();
    invalidate();
  }, [action, camera, invalidate]);
  return (
    <OrbitControls
      ref={ref}
      makeDefault
      enablePan={false}
      enableDamping={false}
      minDistance={4.4}
      maxDistance={9}
      rotateSpeed={0.45}
      zoomSpeed={0.6}
      minPolarAngle={0.25}
      maxPolarAngle={Math.PI - 0.25}
    />
  );
}
function Fallback() {
  return (
    <div className="globe-fallback">
      <Image
        src="/assets/earth-fallback.svg"
        width={520}
        height={520}
        unoptimized
        alt="Mapa de la Tierra centrado en Norteamérica"
      />
      <p>Vista estática · usa el selector de región</p>
    </div>
  );
}
class GlobeBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? <Fallback /> : this.props.children;
  }
}
export default function Globe({
  regionId,
  onSelect,
  forceFallback = false,
  layer = [],
}: {
  regionId: string;
  onSelect: (id: string) => void;
  forceFallback?: boolean;
  layer?: MapRegionValue[];
}) {
  const [supported] = useState(() => {
    if (typeof document === "undefined") return true;
    try {
      return !!document.createElement("canvas").getContext("webgl2");
    } catch {
      return false;
    }
  });
  const [action, setAction] = useState({ type: "reset", tick: 0 });
  return (
    <div className="globe-container">
      <div className="globe-halo" />
      {!supported || forceFallback ? (
        <Fallback />
      ) : (
        <GlobeBoundary>
          <Canvas
            style={{ position: "absolute", inset: 0 }}
            dpr={[1, 1.6]}
            frameloop="demand"
            camera={{ position: position(26, -103, 5.8), fov: 42 }}
            gl={{ antialias: true, alpha: true }}
            fallback={<Fallback />}
            aria-label="Globo terrestre interactivo. Arrastra para rotar y usa la rueda para acercar. La caja noreste de México tiene datos disponibles."
          >
            <ambientLight intensity={1.7} />
            <directionalLight
              position={[-3, 5, 6]}
              intensity={2.4}
              color="#d6e9ed"
            />
            <directionalLight
              position={[2, 0, -5]}
              intensity={0.45}
              color="#497fbb"
            />
            <Suspense fallback={null}>
              <Earth />
              {intersectedStates.map((f) => (
                <StateSurface key={f.properties.id} feature={f} />
              ))}
              {regions.map((region) => (
                <RegionMark
                  key={region.id}
                  region={region}
                  selected={regionId === region.id}
                  onSelect={onSelect}
                  value={layer.find((v) => v.regionId === region.id)}
                />
              ))}
            </Suspense>
            <Controls action={action} />
          </Canvas>
        </GlobeBoundary>
      )}
      <div className="globe-toolbar" aria-label="Controles del globo">
        <button
          title="Acercar"
          aria-label="Acercar globo"
          onClick={() => setAction((a) => ({ type: "in", tick: a.tick + 1 }))}
          disabled={!supported || forceFallback}
        >
          <Plus size={17} />
        </button>
        <button
          title="Alejar"
          aria-label="Alejar globo"
          onClick={() => setAction((a) => ({ type: "out", tick: a.tick + 1 }))}
          disabled={!supported || forceFallback}
        >
          <Minus size={17} />
        </button>
        <span />
        <button
          title="Volver a Norteamérica"
          aria-label="Volver a Norteamérica"
          onClick={() =>
            setAction((a) => ({ type: "reset", tick: a.tick + 1 }))
          }
          disabled={!supported || forceFallback}
        >
          <RotateCcw size={16} />
        </button>
      </div>
      <div className="globe-coordinate">
        <Crosshair size={13} /> 26° N &nbsp; 103° O <span>VISTA INICIAL</span>
      </div>
    </div>
  );
}
