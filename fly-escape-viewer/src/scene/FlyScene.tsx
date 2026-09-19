import { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import type { Group, Mesh } from "three";
import type { ScenarioData } from "../types";

/**
 * THE SISYPHUS SCENE - and a crash course in react-three-fiber, since none of this works
 * like the DOM you already know.
 *
 * WHAT THE PIECES ARE
 * -------------------
 * <Canvas>   the one real DOM element here. It creates a WebGL surface and a Three.js
 *            "scene graph" inside it. Everything nested under it is NOT HTML - those tags
 *            are 3D objects, and React is just describing a tree of them.
 * mesh       one visible object. A mesh is always exactly two things glued together:
 * geometry   its SHAPE - a bag of points and triangles. sphereGeometry, boxGeometry,
 *            icosahedronGeometry. The `args` array is passed to the Three.js constructor,
 *            so args={[0.45, 24, 16]} on a sphere means radius 0.45 with 24x16 segments.
 * material   its SURFACE - how light bounces off it. meshStandardMaterial reacts to lights
 *            (and therefore needs some in the scene, or everything renders black).
 * group      an invisible container. Move the group and everything inside moves with it,
 *            which is how the fly's body, head, wings and legs stay one creature.
 *
 * THE COORDINATE SYSTEM
 * ---------------------
 * Three.js is Y-UP: +Y is the sky, -Y is the floor, +X is right, -X is left, and +Z comes
 * toward you out of the screen. Our ground sits at y = 0 and the fly rests just above it.
 * The camera is parked far out on +Z looking back at the origin, which gives the flat
 * side-on view of a 2D platformer. We use an ORTHOGRAPHIC camera: no perspective, so a
 * shape keeps its size no matter how far away it is - which makes the boulder's fall read
 * as pure vertical motion instead of also appearing to grow.
 *
 * WHY useFrame INSTEAD OF requestAnimationFrame
 * ---------------------------------------------
 * You could run your own rAF loop, but you would then be fighting the renderer: r3f already
 * runs one loop that draws every frame, and useFrame simply hands you a slot inside it. That
 * matters because a) your code runs at the right moment, right before the draw, so the frame
 * you compute is the frame that gets painted, b) it stays in step with everything else in
 * the scene, and c) r3f can pause, throttle or reorder the whole thing without your loop
 * carrying on regardless.
 *
 * The other half: inside useFrame we move objects by writing straight to `mesh.position`
 * through a ref, NOT by putting coordinates in React state. State would re-render the
 * component 60 times a second to change one number. Mutating the object skips React
 * entirely - the scene graph is the state.
 *
 * WHERE THE MOTION COMES FROM
 * ---------------------------
 * Every position below is a pure function of `timeMs`, the same clock the debug view reads.
 * Nothing is on a timer of its own, so the fly cannot jump "about when" the Giant Fiber
 * fires - it jumps because timeMs passed giant_fiber_spike_ms, or it never jumps at all.
 */

// ---- scene constants, in world units (roughly "one unit = one fly body") ----
const FLY_REST = { x: 0, y: 0.55 };
const BOULDER_RADIUS = 1.0;
const BOULDER_TOP_Y = 7.5; // where the threat starts, off the top of the view
const BOULDER_REST_Y = BOULDER_RADIUS; // resting exactly on the ground
const JUMP_MS = 300; // how long the escape leap takes
const JUMP_DISTANCE = 2.8; // how far sideways the fly clears
const JUMP_HEIGHT = 1.9; // peak of the arc above its resting height

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const lerp = (from: number, to: number, t: number) => from + (to - from) * t;

interface Props {
  data: ScenarioData;
  timeMs: number;
}

/** The fly: one group holding a handful of primitives, all positioned relative to the group. */
function Fly({ groupRef }: { groupRef: React.RefObject<Group | null> }) {
  return (
    <group ref={groupRef}>
      {/* body */}
      <mesh castShadow>
        <sphereGeometry args={[0.42, 24, 18]} />
        <meshStandardMaterial color="#3f4a5a" roughness={0.45} />
      </mesh>
      {/* head, pushed forward along +X */}
      <mesh position={[0.46, 0.1, 0]}>
        <sphereGeometry args={[0.26, 20, 16]} />
        <meshStandardMaterial color="#333c49" roughness={0.45} />
      </mesh>
      {/* the two big red eyes */}
      <mesh position={[0.6, 0.18, 0.15]}>
        <sphereGeometry args={[0.13, 16, 12]} />
        <meshStandardMaterial color="#c0392b" roughness={0.3} />
      </mesh>
      <mesh position={[0.6, 0.18, -0.15]}>
        <sphereGeometry args={[0.13, 16, 12]} />
        <meshStandardMaterial color="#c0392b" roughness={0.3} />
      </mesh>
      {/* wings: very flat boxes, tilted up and back. transparent so they read as wings */}
      <mesh position={[-0.15, 0.32, 0.28]} rotation={[0.35, 0, 0.22]}>
        <boxGeometry args={[0.8, 0.02, 0.36]} />
        <meshStandardMaterial color="#9fb6d0" transparent opacity={0.45} />
      </mesh>
      <mesh position={[-0.15, 0.32, -0.28]} rotation={[-0.35, 0, 0.22]}>
        <boxGeometry args={[0.8, 0.02, 0.36]} />
        <meshStandardMaterial color="#9fb6d0" transparent opacity={0.45} />
      </mesh>
      {/* legs: thin cylinders. cylinderGeometry stands up the Y axis by default, so each
          one is rotated outwards a little to splay the feet. */}
      {[
        [0.22, 0.4],
        [-0.05, 0.25],
        [-0.3, 0.1],
      ].map(([x, tilt], i) => (
        <group key={i}>
          <mesh position={[x, -0.33, 0.2]} rotation={[tilt, 0, 0.25]}>
            <cylinderGeometry args={[0.03, 0.03, 0.42, 8]} />
            <meshStandardMaterial color="#232a33" />
          </mesh>
          <mesh position={[x, -0.33, -0.2]} rotation={[-tilt, 0, 0.25]}>
            <cylinderGeometry args={[0.03, 0.03, 0.42, 8]} />
            <meshStandardMaterial color="#232a33" />
          </mesh>
        </group>
      ))}
    </group>
  );
}

/** Everything that moves. Lives inside <Canvas> so it can use r3f hooks. */
function Animated({ data, timeMs }: Props) {
  const flyRef = useRef<Group>(null);
  const boulderRef = useRef<Mesh>(null);

  useFrame(() => {
    const fly = flyRef.current;
    const boulder = boulderRef.current;
    if (!fly || !boulder) return;

    // r3f re-registers this callback on every render, so `timeMs` here is always the latest
    // value from the shared clock - no stale closure, and no second clock.
    const t = timeMs;
    const ramp = data.ramp_duration_ms;
    const gf = data.giant_fiber_spike_ms;

    // ---- the boulder ----
    // Progress through the fall, 0 at the start of the ramp and 1 when it lands.
    const p = clamp01(t / ramp);
    // EASE-IN, NOT LINEAR, and for a physical reason: a falling body accelerates, so the
    // distance it has covered grows with the SQUARE of the time (the schoolbook d = ½gt²).
    // Squaring p reproduces that - barely moving at first, fastest at the moment of impact.
    // A linear fall would look like the boulder was being lowered on a rope.
    boulder.position.y = lerp(BOULDER_TOP_Y, BOULDER_REST_Y, p * p);
    // The boulder always lands on x = 0, the fly's ORIGINAL spot. Whether that spot is empty
    // by then is entirely up to whether the Giant Fiber fired.
    boulder.position.x = 0;
    boulder.rotation.z = -p * p * 2.4; // tumbling, on the same curve so it stops when it lands

    // ---- the fly ----
    if (gf == null || t < gf) {
      // No decision yet (or never, in a scenario where the circuit did not trigger): the fly
      // simply sits there. In the null case this is the whole story - it gets hit.
      fly.position.set(FLY_REST.x, FLY_REST.y, 0);
      fly.rotation.z = 0;
    } else {
      // THE JUMP. `u` runs 0 -> 1 over the 300 ms of the leap and then sticks at 1.
      const u = clamp01((t - gf) / JUMP_MS);
      // Sideways: straight-line travel, from the old spot to a safe distance.
      fly.position.x = lerp(FLY_REST.x, FLY_REST.x + JUMP_DISTANCE, u);
      // Upwards: the arc is 4 * h * u * (1 - u). Read it plainly - at u = 0 and u = 1 one of
      // the two factors is zero, so the height is zero (feet on the ground at both ends), and
      // at u = 0.5 it works out to exactly h, the top of the arc. That is a parabola, the
      // same shape anything thrown follows, written in one line and with no physics engine.
      fly.position.y = FLY_REST.y + 4 * JUMP_HEIGHT * u * (1 - u);
      fly.rotation.z = -u * 0.6; // a little tumble so the leap does not look stiff
    }

    // If the circuit never fired AND the boulder has arrived, flatten the fly a touch. It is
    // the one bit of theatre in here, and it still only happens when the data says it should.
    const squashed = gf == null && p >= 1;
    fly.scale.set(1, squashed ? 0.45 : 1, 1);
  });

  return (
    <>
      <Fly groupRef={flyRef} />
      {/* icosahedronGeometry with detail 0 is a 20-sided solid: chunky facets that read as
          rock. flatShading keeps each face flat instead of smoothing it into a ball. */}
      <mesh ref={boulderRef} position={[0, BOULDER_TOP_Y, 0]}>
        <icosahedronGeometry args={[BOULDER_RADIUS, 0]} />
        <meshStandardMaterial color="#6b6259" roughness={0.95} flatShading />
      </mesh>
    </>
  );
}

export function FlyScene({ data, timeMs }: Props) {
  return (
    <div className="scene-canvas">
      {/*
        The camera sits far out on +Z at height 0 and looks at the origin, so the view is
        dead horizontal. The scene itself is then shifted DOWN inside a group, which brings
        the interesting band (ground up to the falling boulder) into the middle of frame -
        easier than aiming the camera. `zoom` is how many pixels one world unit takes up.
      */}
      <Canvas orthographic camera={{ position: [0, 0, 20], zoom: 46, near: 0.1, far: 100 }}>
        {/* Lights. meshStandardMaterial is invisible without them: ambient fills everything
            evenly, the directional light comes from one side and creates the shading. */}
        <ambientLight intensity={0.55} />
        <directionalLight position={[4, 8, 6]} intensity={1.6} />
        <directionalLight position={[-6, 3, -4]} intensity={0.4} color="#88aaff" />

        {/* The camera looks at the origin, so we slide the whole scene DOWN until the band
            we care about - ground at y=0 up to the boulder's start at y=8.5 - straddles it.
            Nudged left as well, to leave room on the right for the fly to jump into. */}
        <group position={[-0.9, -4.05, 0]}>
          <Animated data={data} timeMs={timeMs} />
          {/* the ground: a very flat box, wide enough to fill the frame */}
          <mesh position={[0, -0.15, 0]}>
            <boxGeometry args={[30, 0.3, 6]} />
            <meshStandardMaterial color="#20262e" roughness={1} />
          </mesh>
        </group>
      </Canvas>
    </div>
  );
}
