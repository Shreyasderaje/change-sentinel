import { useId } from "react";

/** Decorative illustration only; it does not represent live spacecraft or sensor data. */
export function OrbitalIntelligence() {
  const key = useId().replaceAll(":", "");

  return (
    <section className="orbital-panel" aria-label="Illustrative orbital intelligence visualization">
      <div className="orbital-atmosphere" aria-hidden="true" />
      <div className="orbital-grid-layer" aria-hidden="true" />
      <div className="radar-field" aria-hidden="true"><span className="radar-sweep" /></div>
      <span className="orbital-scanline" aria-hidden="true" />
      <svg className="orbital-svg" viewBox="0 0 640 420" fill="none" aria-hidden="true" preserveAspectRatio="xMidYMid meet">
        <defs>
          <radialGradient id={`${key}-glow`} cx="0" cy="0" r="1" gradientTransform="matrix(0 207 -258 0 348 208)" gradientUnits="userSpaceOnUse">
            <stop stopColor="#148acb" stopOpacity=".28"/><stop offset=".68" stopColor="#0a3e70" stopOpacity=".2"/><stop offset="1" stopColor="#07172c" stopOpacity="0"/>
          </radialGradient>
          <linearGradient id={`${key}-orbit`} x1="79" y1="272" x2="568" y2="118" gradientUnits="userSpaceOnUse">
            <stop stopColor="#2382d5" stopOpacity=".08"/><stop offset=".52" stopColor="#6ce8ff" stopOpacity=".83"/><stop offset="1" stopColor="#318cdb" stopOpacity=".12"/>
          </linearGradient>
          <linearGradient id={`${key}-beam`} x1="0" y1="0" x2="0" y2="1">
            <stop stopColor="#5ce4ff" stopOpacity="0"/><stop offset=".5" stopColor="#5ce4ff" stopOpacity=".32"/><stop offset="1" stopColor="#5ce4ff" stopOpacity="0"/>
          </linearGradient>
          <clipPath id={`${key}-globe`}><ellipse cx="341" cy="210" rx="204" ry="139" /></clipPath>
        </defs>
        <ellipse cx="341" cy="210" rx="254" ry="180" fill={`url(#${key}-glow)`} />
        <g clipPath={`url(#${key}-globe)`}>
          <ellipse cx="341" cy="210" rx="204" ry="139" fill="#0a2945" fillOpacity=".23" />
          <path d="M138 210h406M145 174c112 25 280 25 392 0M145 246c112-25 280-25 392 0M174 137c101 42 238 42 334 0M174 283c101-42 238-42 334 0" stroke="#65bbeb" strokeOpacity=".2" strokeWidth=".8" />
          <path d="M341 71c-48 43-75 91-75 139s27 96 75 139M341 71c48 43 75 91 75 139s-27 96-75 139M341 71c-19 42-29 89-29 139s10 97 29 139M341 71c19 42 29 89 29 139s-10 97-29 139" stroke="#65bbeb" strokeOpacity=".17" strokeWidth=".8" />
          <path d="M173 194c26-18 37-15 53-6 15 8 24 3 39-5 16-8 27-6 36 6 10 12 20 15 33 8 15-8 20-19 37-17 17 2 26 16 39 14 14-2 22-11 37-8 17 3 24 17 40 15 15-2 23-12 41-7" stroke="#62b7d1" strokeOpacity=".35" />
          <path d="M177 224c26-14 48-12 61-2 12 10 24 8 41 0 16-8 28-5 41 8 13 13 23 12 36 5 14-8 22-16 37-11 15 5 23 19 41 16 18-3 24-16 42-11 17 5 28 20 48 16" stroke="#62b7d1" strokeOpacity=".24" />
          <path d="M190 159c21 2 28 9 42 6 15-3 21-14 36-14s21 13 38 15c18 2 24-7 41-7 18 0 25 12 43 13 17 1 23-7 41-6 19 1 29 12 47 10" stroke="#62b7d1" strokeOpacity=".19" />
          <path className="orbital-map-beam" d="M150 123h382v174H150z" fill={`url(#${key}-beam)`} />
        </g>
        <ellipse cx="341" cy="210" rx="204" ry="139" stroke="#6bb8e5" strokeOpacity=".42" />
        <path className="orbit-path" d="M83 275C167 44 461 46 562 161c71 81-11 167-144 174-147 8-274-75-255-160 16-74 144-127 262-104" stroke={`url(#${key}-orbit)`} strokeWidth="1.4" strokeDasharray="3 7" />
        <path d="M90 295c118-83 281-97 457-34" stroke="#488fc6" strokeOpacity=".16" />
        <g className="candidate-marker marker-one"><circle cx="249" cy="179" r="20" fill="#32d9ee" fillOpacity=".06"/><circle cx="249" cy="179" r="9" stroke="#69edff" strokeOpacity=".78"/><circle cx="249" cy="179" r="3" fill="#9cf6ff"/></g>
        <g className="candidate-marker marker-two"><circle cx="430" cy="246" r="24" fill="#4f9eff" fillOpacity=".06"/><circle cx="430" cy="246" r="10" stroke="#74baff" strokeOpacity=".74"/><circle cx="430" cy="246" r="3" fill="#b5d9ff"/></g>
        <g className="satellite-orbit-marker" transform="translate(0 0)">
          <circle cx="520" cy="109" r="19" fill="#39bfea" fillOpacity=".12" />
          <g className="satellite-hardware" stroke="#b8f4ff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="m515 109 5-5 5 5-5 5zM520 101v-3m0 22v-3m-8-8h-3m22 0h-3" />
            <path d="M510 104h-9v10h9m20-10h9v10h-9" stroke="#72d8f5" strokeWidth="2" />
            <path d="M504 107h5m-5 4h5m19-4h5m-5 4h5" stroke="#54a9d1" strokeWidth="1" />
          </g>
        </g>
      </svg>
      <div className="orbital-label orbital-label-top"><span className="orbital-label-dot" /> ORBITAL INTELLIGENCE <span>SIMULATION</span></div>
      <div className="telemetry telemetry-left"><small>SCENE PAIR</small><b>OPTICAL · RGB</b><small>CHANGE REVIEW</small></div>
      <div className="telemetry telemetry-right"><small>GRID REFERENCE</small><b>DEMO CELL 07</b><b>PIXEL SPACE</b></div>
      <div className="orbital-caption"><span>Illustrative visualization — not live satellite tracking.</span><small>CONCEPT VIEW / 01</small></div>
    </section>
  );
}
