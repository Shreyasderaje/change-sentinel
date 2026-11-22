import Link from "next/link";
import Image from "next/image";
import { OrbitalIntelligence } from "@/components/motion/OrbitalIntelligence";

const capabilities = [
  {
    number: "01",
    title: "Geospatial change detection",
    text: "Compare image pairs and surface measured visual differences as review candidates.",
    anchor: "#platform",
  },
  {
    number: "02",
    title: "Satellite image comparison",
    text: "Inspect before and after scenes, difference maps, and candidate regions together.",
    anchor: "#platform",
  },
  {
    number: "03",
    title: "Investigation intelligence",
    text: "Keep imagery, measurements, review notes, and report preparation in one workflow.",
    anchor: "#how-it-works",
  },
  {
    number: "04",
    title: "Field verification",
    text: "Give officers a focused place to examine candidate regions and record observations.",
    anchor: "#field-verification",
  },
  {
    number: "05",
    title: "Voice-first field reporting",
    text: "Transcribe short field notes with Saaras v4, then edit and confirm the local draft.",
    anchor: "#ai-intelligence",
  },
  {
    number: "06",
    title: "Human verification and auditability",
    text: "Keep candidate detections distinct from confirmed findings and preserve review provenance.",
    anchor: "#field-verification",
  },
];

const steps = [
  "Upload an image pair",
  "Identify candidate changes",
  "Review measurements and geospatial context",
  "Verify findings in the field",
  "Prepare an investigation report",
];

export function LandingPage() {
  return (
    <main className="marketing-shell">
      <header className="marketing-header">
        <a className="brand-lockup" href="#top" aria-label="Change Sentinel home">
          <span className="brand-symbol" aria-hidden="true"><span /></span>
          <span><strong>CHANGE SENTINEL</strong><small>GEOSPATIAL INTELLIGENCE</small></span>
        </a>
        <nav className="marketing-nav" aria-label="Main navigation">
          <a href="#platform">Platform</a>
          <a href="#how-it-works">How it works</a>
          <a href="#ai-intelligence">AI intelligence</a>
          <a href="#field-verification">Field verification</a>
        </nav>
        <div className="header-actions">
          <Link className="text-link" href="/login">Sign in</Link>
          <Link className="button button-small" href="/workspace">Launch workspace <span aria-hidden="true">↗</span></Link>
        </div>
      </header>

      <section className="hero-section" id="top">
        <div className="hero-copy">
          <p className="eyebrow"><span className="eyebrow-dot" /> GEOSPATIAL INTELLIGENCE, WITH HUMAN REVIEW</p>
          <h1>See what changed.<br /><span>Know what needs</span><br />verification.</h1>
          <p className="hero-description">Transform satellite imagery into actionable geospatial intelligence. Detect candidate changes, understand their context, and coordinate human verification.</p>
          <div className="hero-actions">
            <Link className="button" href="/workspace">Launch workspace <span aria-hidden="true">↗</span></Link>
            <a className="button button-quiet" href="#platform">Explore the platform <span aria-hidden="true">↓</span></a>
          </div>
          <div className="hero-proof" aria-label="Product principles">
            <span><b>01</b> Measured candidates</span><i />
            <span><b>02</b> Human verification</span><i />
            <span><b>03</b> Traceable review</span>
          </div>
        </div>
        <div className="hero-art-wrap">
          <OrbitalIntelligence />
          <div className="hero-art-caption"><span className="live-dot" /> Change intelligence workflow <span>01 / 05</span></div>
        </div>
      </section>

      <section className="principle-strip" aria-label="Review principle">
        <p>From imagery to informed action</p>
        <span>Signals are surfaced as candidates. People establish what they mean.</span>
      </section>

      <section className="section-block" id="platform">
        <div className="section-heading">
          <p className="eyebrow">THE PLATFORM</p>
          <h2>One workflow for seeing change<br className="desktop-break" /> and deciding what comes next.</h2>
          <p>Bring image comparison, investigation context, and field review into a clear sequence.</p>
        </div>
        <div className="capability-grid">
          {capabilities.map((item) => (
            <a className="capability-card" href={item.anchor} key={item.number}>
              <span className="capability-number">{item.number}</span>
              <span className="capability-arrow" aria-hidden="true">↗</span>
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </a>
          ))}
        </div>
      </section>

      <section className="comparison-section">
        <div className="comparison-copy">
          <p className="eyebrow">SEE THE DIFFERENCE</p>
          <h2>Put both moments<br />in the same frame.</h2>
          <p>Compare two scenes, inspect the difference intensity map, and review regions identified by image analysis. Each output stays clearly labeled as a candidate until a person verifies it.</p>
          <Link className="inline-link" href="/workspace">Explore the image workspace <span aria-hidden="true">→</span></Link>
        </div>
        <div className="comparison-visual">
          <figure><Image src="/images/demo-before.png" alt="Synthetic example image before a visual change" fill sizes="(max-width: 800px) 92vw, 43vw" /><figcaption>BEFORE · SYNTHETIC EXAMPLE</figcaption></figure>
          <div className="comparison-divider"><span>COMPARE</span></div>
          <figure><Image src="/images/demo-after.png" alt="Synthetic example image after a visual change" fill sizes="(max-width: 800px) 92vw, 43vw" /><figcaption>AFTER · SYNTHETIC EXAMPLE</figcaption></figure>
          <p className="visual-note">Bundled illustration only. Not a real satellite capture or analysis result.</p>
        </div>
      </section>

      <section className="workflow-section" id="how-it-works">
        <div className="section-heading section-heading-inline">
          <div><p className="eyebrow">HOW IT WORKS</p><h2>A clear path from image pair<br className="desktop-break" /> to field-ready report.</h2></div>
          <p>Every stage keeps the source imagery and the review status in view.</p>
        </div>
        <ol className="workflow-list">
          {steps.map((step, index) => <li key={step}><span>0{index + 1}</span><p>{step}</p><i aria-hidden="true">{index < steps.length - 1 ? "↘" : "✓"}</i></li>)}
        </ol>
      </section>

      <section className="ai-section" id="ai-intelligence">
        <div className="ai-orbit"><OrbitalIntelligence /></div>
        <div className="ai-copy">
          <p className="eyebrow">AI INTELLIGENCE</p>
          <h2>Useful intelligence.<br /><span>Clear boundaries.</span></h2>
          <p>Voice can make field reporting easier. Investigation assistance needs verified context before it can be useful.</p>
          <div className="ai-feature">
            <span className="feature-status status-ready">AVAILABLE</span>
            <div><h3>Sarvam Voice Intelligence</h3><p>Officers can record or upload a short note, receive a Saaras v4 transcript, and edit it before confirming a page-local draft. Saving the transcript is not yet available.</p></div>
          </div>
          <div className="ai-feature">
            <span className="feature-status status-planned">BACKEND DEPENDENCY</span>
            <div><h3>Investigation Copilot</h3><p>The interface is prepared. Sending will remain disabled until the authenticated backend explicitly provides authorized, verified investigation context.</p></div>
          </div>
        </div>
      </section>

      <section className="field-section" id="field-verification">
        <div className="field-copy">
          <p className="eyebrow">FIELD VERIFICATION</p>
          <h2>Keep the human decision<br />in the workflow.</h2>
          <p>Candidate differences are a starting point for investigation. Officers can review regions and capture notes while the product keeps unsaved choices visibly marked as local drafts.</p>
          <Link className="inline-link" href="/workspace">See the review workspace <span aria-hidden="true">→</span></Link>
        </div>
        <div className="audit-card">
          <div className="audit-top"><span>REVIEW RECORD</span><span className="draft-pill">LOCAL DRAFT</span></div>
          <div className="audit-row"><span className="audit-icon">01</span><div><b>Candidate region identified</b><small>Computed measurement · requires review</small></div><span className="audit-state">CANDIDATE</span></div>
          <div className="audit-row"><span className="audit-icon">02</span><div><b>Field note transcribed</b><small>Editable transcript · not persisted</small></div><span className="audit-state state-muted">DRAFT</span></div>
          <div className="audit-row"><span className="audit-icon">03</span><div><b>Human verification</b><small>Decision remains with the investigator</small></div><span className="audit-state state-muted">PENDING</span></div>
          <p className="audit-footnote">Status labels describe this interface only. They do not update a backend investigation.</p>
        </div>
      </section>

      <section className="closing-cta">
        <p className="eyebrow">CHANGE SENTINEL 2.0</p>
        <h2>Start with the evidence.<br /><span>Move forward with clarity.</span></h2>
        <Link className="button" href="/workspace">Launch workspace <span aria-hidden="true">↗</span></Link>
      </section>

      <footer className="marketing-footer">
        <a className="brand-lockup" href="#top" aria-label="Change Sentinel home"><span className="brand-symbol" aria-hidden="true"><span /></span><span><strong>CHANGE SENTINEL</strong><small>GEOSPATIAL INTELLIGENCE</small></span></a>
        <p>Satellite imagery comparison and human-led investigation review.</p>
        <nav aria-label="Footer navigation"><a href="#platform">Platform</a><a href="#how-it-works">How it works</a><a href="#ai-intelligence">AI intelligence</a><Link href="/login">Sign in</Link></nav>
        <small>Change Sentinel 2.0 · Candidate findings require human verification.</small>
      </footer>
    </main>
  );
}
