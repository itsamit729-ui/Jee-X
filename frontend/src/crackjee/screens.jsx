import { useState, useEffect, useRef } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, LineChart, Line, CartesianGrid } from "recharts";
import { ArrowUpRight, Clock3, BookOpen, Target, Check, X as XIcon } from "lucide-react";
import { Logo, LogoMark } from "../components/Brand.jsx";
import Palette from "../components/Palette.jsx";
import FullscreenGuard from "../components/FullscreenGuard.jsx";
import { requestFullscreen, exitFullscreen, useFullscreenLock } from "../lib/fullscreen.js";
import { INK_2, LINE, PEN, GOOD, BAD, IDLE, CHEM, SUBJECT_COLOR, axisProps, gridProps, tooltipProps, fontBody } from "./ui.js";

/* ================================================================
   DATA
   ================================================================ */
const HERO_QUESTIONS = [
  { q: "The de Broglie wavelength of an electron accelerated through 100V is approximately:", ops: ["0.123 nm", "1.23 nm", "0.0123 nm", "12.3 nm"], ans: 0, year: "JEE Advanced 2019", funFact: "Louis de Broglie proposed matter waves in his 1924 PhD thesis and won the Nobel Prize for the idea five years later.", chapter: "Modern Physics", diff: "Medium" },
  { q: "The number of sp² hybridized carbon atoms in Aspirin (C₉H₈O₄) is:", ops: ["6", "7", "9", "3"], ans: 1, year: "JEE Advanced 2023", funFact: "Aspirin was originally derived from willow bark, used medicinally for over 3,500 years, and JEE still expects you to know its structure.", chapter: "Organic Chemistry", diff: "Hard" },
  { q: "If f(x) = x·[x], where [·] is the greatest integer function, then f(x) is:", ops: ["Continuous at x=2", "Discontinuous at x=2", "Differentiable at x=2", "None of these"], ans: 1, year: "IIT-JEE 1995", funFact: "Greatest-integer functions jump at every integer, so that is exactly where questions like this one probe continuity.", chapter: "Limits & Continuity", diff: "Medium" },
  { q: "A charged particle moves in a helical path. It must be under:", ops: ["Electric field only", "Magnetic field only", "Both E and B fields", "Magnetic field with velocity at angle"], ans: 3, year: "JEE Main 2024", funFact: "This is the principle behind the Large Hadron Collider at CERN, the machine that confirmed the Higgs boson.", chapter: "Magnetic Effects", diff: "Easy" },
  { q: "The compound that does NOT show optical isomerism:", ops: ["[Co(en)₃]³⁺", "[Co(en)₂Cl₂]⁺", "[Co(NH₃)₆]³⁺", "[Cr(ox)₃]³⁻"], ans: 2, year: "JEE Advanced 2018", funFact: "Coordination chemistry turns up in almost every JEE Advanced paper. Dependable marks once the isomer rules click.", chapter: "Coordination Compounds", diff: "Hard" },
  { q: "The value of lim(n→∞) (1 + 1/n)ⁿ equals:", ops: ["1", "∞", "e", "0"], ans: 2, year: "IIT-JEE 1998", funFact: "Euler's number e shows up in compound interest, population growth and radioactive decay alike.", chapter: "Limits", diff: "Easy" },
  { q: "The nuclear reaction ²H + ²H → ³He + n is an example of:", ops: ["Nuclear fission", "Nuclear fusion", "Radioactive decay", "Artificial transmutation"], ans: 1, year: "JEE Main 2022", funFact: "Fusion powers the Sun, which turns roughly 600 million tonnes of hydrogen into helium every second.", chapter: "Nuclear Physics", diff: "Easy" },
  { q: "Benzene reacts with CH₃Cl/AlCl₃. This reaction is called:", ops: ["Wurtz reaction", "Friedel-Crafts alkylation", "Kolbe reaction", "Sandmeyer reaction"], ans: 1, year: "IIT-JEE 2001", funFact: "Friedel and Crafts discovered this in 1877. It is one of the named reactions JEE asks about most.", chapter: "Organic Chemistry", diff: "Easy" },
  { q: "A matrix A satisfies A² = I. Then A is called:", ops: ["Nilpotent", "Idempotent", "Involutory", "Orthogonal"], ans: 2, year: "JEE Advanced 2020", funFact: "Matrices are among the most formulaic topics in the paper: learn the definitions and the marks follow.", chapter: "Matrices", diff: "Medium" },
  { q: "The Gibbs free energy change for a spontaneous process is:", ops: ["Positive", "Zero", "Negative", "Can be anything"], ans: 2, year: "JEE Main 2023", funFact: "Josiah Willard Gibbs' work was so far ahead of its time that few of his contemporaries fully understood it.", chapter: "Thermodynamics", diff: "Easy" },
];

const SUBJECTS = ["Physics", "Chemistry", "Mathematics"];
const DIFF_COLOR = { Easy: GOOD, Medium: CHEM, Hard: BAD };
const LETTER = (i) => String.fromCharCode(65 + i);

// Styles now live in index.css. Pages still call this hook, so it stays as a no-op.
export function useCrackJeeStyles() {}

function useInView(threshold = 0.35) {
  const ref = useRef(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || seen) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect(); } }, { threshold });
    io.observe(el);
    return () => io.disconnect();
  }, [seen, threshold]);
  return [ref, seen];
}

/* ================================================================
   HERO QUESTION CARD
   ================================================================ */
function QuestionSlider({ streak, setStreak, totalSolved, setTotalSolved }) {
  const n = HERO_QUESTIONS.length;
  const [idx, setIdx] = useState(0);
  const [selected, setSelected] = useState(null);
  const [revealed, setRevealed] = useState(false);
  const [results, setResults] = useState(() => Array(n).fill("idle"));
  const pos = idx % n;
  const current = HERO_QUESTIONS[pos];
  const right = selected === current.ans;

  const mark = (state) => setResults((r) => r.map((s, i) => (i === pos ? state : s)));

  const handleSelect = (oi) => {
    if (revealed) return;
    setSelected(oi);
    setRevealed(true);
    setTotalSolved((p) => p + 1);
    setStreak((p) => (oi === current.ans ? p + 1 : 0));
    mark(oi === current.ans ? "correct" : "wrong");
  };

  const advance = () => {
    if ((idx + 1) % n === 0) setResults(Array(n).fill("idle"));
    setIdx((p) => p + 1);
    setSelected(null);
    setRevealed(false);
  };

  const handleSkip = () => { setStreak(0); mark("skipped"); advance(); };

  const states = results.map((s, i) => (i === pos && !revealed ? "current" : s));

  return (
    <div>
      <div className="slider-head">
        <Palette states={states} label="Your answers" />
        <span className={`streak ${streak > 0 ? "is-on" : ""}`}>
          {streak > 1 ? `${streak} in a row` : `Question ${pos + 1} of ${n}`}
        </span>
      </div>

      <div key={idx} className="qcard q-enter">
        <div className="qmeta">
          <span className="tag">{current.year}</span>
          <span className="tag"><span className="dot" style={{ background: DIFF_COLOR[current.diff] }} />{current.diff}</span>
          <span className="tag">{current.chapter}</span>
        </div>
        <p className="qtext">{current.q}</p>

        <div className="options">
          {current.ops.map((op, oi) => {
            const state = !revealed ? "" : oi === current.ans ? "is-correct" : oi === selected ? "is-wrong" : "";
            return (
              <button key={oi} type="button" className={`option ${state}`} disabled={revealed} onClick={() => handleSelect(oi)}>
                <span className="option-key">{LETTER(oi)}</span>
                <span className="option-body">{op}</span>
                {revealed && oi === current.ans && <Check size={18} color={GOOD} className="option-icon" aria-label="Correct answer" />}
                {revealed && oi === selected && !right && <XIcon size={18} color={BAD} className="option-icon" aria-label="Your answer" />}
              </button>
            );
          })}
        </div>

        {revealed ? (
          <div className="explain" role="status">
            <strong>{right ? "Correct." : `Not quite. The answer is ${LETTER(current.ans)}.`}</strong>
            {current.funFact}
            <div><button type="button" className="btn btn-secondary btn-sm" onClick={advance}>Next question</button></div>
          </div>
        ) : (
          <div className="slider-foot">
            <button type="button" className="btn btn-quiet btn-sm" onClick={handleSkip}>Skip this one</button>
          </div>
        )}
      </div>
    </div>
  );
}

/* ================================================================
   HOME PAGE
   ================================================================ */
const STEPS = [
  { title: "Sit a test", body: "A full 75-question mock, a single-subject test, or the free 10-question warm-up.", states: ["answered", "answered", "answered", "current", "idle", "idle", "idle", "idle"] },
  { title: "See where the marks went", body: "Accuracy and time for every chapter, not just a total at the end.", states: ["correct", "correct", "wrong", "correct", "wrong", "correct", "correct", "wrong"] },
  { title: "Practise what cost you", body: "Pick the chapters you dropped and drill them with a subject test.", states: ["correct", "correct", "correct", "correct", "wrong", "correct", "correct", "correct"] },
];

const SHOWCASE = [
  "answered", "answered", "unanswered", "answered", "answered",
  "marked", "answered", "answered", "answeredMarked", "unanswered",
  "answered", "answered", "answered", "marked", "answered",
  "unanswered", "answered", "idle", "idle", "idle",
  "idle", "idle", "idle", "idle", "idle",
];

const LEGEND = [
  ["idle", "Not visited"],
  ["unanswered", "Not answered"],
  ["answered", "Answered"],
  ["marked", "Marked for review"],
  ["answeredMarked", "Answered and marked for review"],
];

export function HomePage({ onStart, onDashboard, onFreeTest, onLogin, onLogout, isAuthenticated, streak, setStreak, totalSolved, setTotalSolved }) {
  const [showcaseRef, showcaseSeen] = useInView();
  const freeTest = onFreeTest || onStart;

  return (
    <div>
      <header className="topbar">
        <div className="wrap topbar-row">
          <Logo />
          <nav className="topbar-links" aria-label="Main">
            {onFreeTest && <button type="button" className="btn btn-quiet btn-sm hide-sm" onClick={onFreeTest}>Free test</button>}
            {isAuthenticated ? (
              <>
                <button type="button" className="btn btn-quiet btn-sm" onClick={onDashboard}>Dashboard</button>
                {onLogout && <button type="button" className="btn btn-quiet btn-sm hide-sm" onClick={onLogout}>Log out</button>}
              </>
            ) : (
              onLogin && <button type="button" className="btn btn-quiet btn-sm" onClick={onLogin}>Log in</button>
            )}
            <button type="button" className="btn btn-primary btn-sm" onClick={onStart}>Start a mock <ArrowUpRight size={16}/></button>
          </nav>
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="wrap hero-grid">
            <div>
              <h1>Find the marks you're losing.</h1>
              <p className="lead">
                Sit full JEE Main mocks on a screen that works like the real one, then see chapter by chapter where your score went.
              </p>
              <div className="hero-actions">
                <button type="button" className="btn btn-primary btn-lg" onClick={freeTest}>Take the free 10-question test</button>
                <button type="button" className="btn btn-secondary btn-lg" onClick={onStart}>Start a full mock</button>
              </div>
              <p className="hero-note">The free test needs no account. Or try the question here first.</p>
            </div>
            <QuestionSlider streak={streak} setStreak={setStreak} totalSolved={totalSolved} setTotalSolved={setTotalSolved} />
          </div>
        </section>

        <section className="section">
          <div className="wrap">
            <h2 className="section-title">Three steps, after every test.</h2>
            <ol className="steps" style={{ listStyle: "none", padding: 0 }}>
              {STEPS.map((s, i) => (
                <li key={s.title} className="step">
                  <span className="step-n">Step {i + 1}</span>
                  <Palette states={s.states} decorative />
                  <h3>{s.title}</h3>
                  <p>{s.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="section">
          <div className="wrap">
            <div className="exam-showcase" ref={showcaseRef}>
              <div
                className={`showcase-palette ${showcaseSeen ? "palette-reveal" : ""}`}
                role="img"
                aria-label="A question palette halfway through a subject: most questions answered, some not answered or marked for review, the rest not visited"
              >
                {SHOWCASE.map((s, i) => (
                  <span key={i} className="sq" data-s={showcaseSeen ? s : "idle"} style={{ "--i": i }}>{i + 1}</span>
                ))}
              </div>
              <div>
                <h2 className="section-title">The exam screen, before exam day.</h2>
                <p className="section-lead">
                  Mocks use the same timer, sections and question palette as the NTA's JEE Main screen, so every colour already means something to you on the day.
                </p>
                <div className="legend">
                  {LEGEND.map(([s, text]) => (
                    <div key={s} className="legend-item"><span className="sq" data-s={s} />{text}</div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="section">
          <div className="wrap">
            <div className="cta-band">
              <div>
                <h2>Ten questions, five minutes.</h2>
                <p>No sign-up until you want to keep your result.</p>
              </div>
              <button type="button" className="btn btn-invert btn-lg" onClick={freeTest}>Take the free test</button>
            </div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="wrap footer-row">
          <Logo />
          <span>Built for JEE Main and Advanced aspirants.</span>
        </div>
      </footer>
    </div>
  );
}

/* ================================================================
   NTA TEST INTERFACE  (deliberately mimics the real exam portal)
   ================================================================ */
const QUESTIONS = {
  Physics: { A: [
    { id:1, text:"A particle of mass 2 kg moves with velocity 3 m/s. A force of 6N acts for 3s. Final velocity is:", options:["12 m/s","6 m/s","9 m/s","15 m/s"], correct:0, chapter:"Laws of Motion", difficulty:"Easy" },
    { id:2, text:"Two blocks (3 kg, 5 kg) connected by string over frictionless pulley. Acceleration is (g=10):", options:["2.5 m/s²","3.75 m/s²","1.25 m/s²","5.0 m/s²"], correct:0, chapter:"Laws of Motion", difficulty:"Medium" },
    { id:3, text:"Work done moving 5 μC charge across 20V potential difference:", options:["100 μJ","50 μJ","200 μJ","10 μJ"], correct:0, chapter:"Electrostatics", difficulty:"Easy" },
    { id:4, text:"Convex lens (f=20cm) gives real image 3× object size. Object distance:", options:["26.67 cm","30 cm","40 cm","13.33 cm"], correct:0, chapter:"Ray Optics", difficulty:"Medium" },
    { id:5, text:"de Broglie wavelength of electron through 100V:", options:["0.123 nm","1.23 nm","0.0123 nm","12.3 nm"], correct:0, chapter:"Dual Nature", difficulty:"Medium" },
    { id:6, text:"Body projected vertically at 40 m/s. Max height (g=10):", options:["80 m","40 m","160 m","60 m"], correct:0, chapter:"Kinematics", difficulty:"Easy" },
    { id:7, text:"Ideal gas undergoes isothermal expansion. Internal energy:", options:["Remains constant","Increases","Decreases","First increases then decreases"], correct:0, chapter:"Thermodynamics", difficulty:"Easy" },
    { id:8, text:"YDSE fringe width 0.5mm. Screen distance doubled. New fringe width:", options:["1.0 mm","0.25 mm","0.5 mm","2.0 mm"], correct:0, chapter:"Wave Optics", difficulty:"Medium" },
    { id:9, text:"MI of solid sphere about diameter is (2/5)MR². About tangent:", options:["(7/5)MR²","(2/5)MR²","(3/5)MR²","(9/5)MR²"], correct:0, chapter:"Rotational Motion", difficulty:"Medium" },
    { id:10, text:"12Ω wire bent into circle. Resistance between diametrically opposite points:", options:["3 Ω","6 Ω","12 Ω","24 Ω"], correct:0, chapter:"Current Electricity", difficulty:"Easy" },
    { id:11, text:"Binding energy per nucleon is maximum for:", options:["Fe-56","U-238","He-4","H-1"], correct:0, chapter:"Nuclei", difficulty:"Easy" },
    { id:12, text:"Charge Q at centre of cube. Flux through one face:", options:["Q/6ε₀","Q/ε₀","Q/2ε₀","Q/4ε₀"], correct:0, chapter:"Electrostatics", difficulty:"Medium" },
    { id:13, text:"Simple pendulum time period on moon (g/6) compared to earth:", options:["√6 times","6 times","1/6 times","1/√6 times"], correct:0, chapter:"Oscillations", difficulty:"Easy" },
    { id:14, text:"Transformer: 500 primary, 5000 secondary turns. Input 220V, output:", options:["2200 V","22 V","220 V","1100 V"], correct:0, chapter:"EMI & AC", difficulty:"Easy" },
    { id:15, text:"Sound speed at 0°C is 332 m/s. At 546°C approximately:", options:["574 m/s","664 m/s","498 m/s","332 m/s"], correct:0, chapter:"Waves", difficulty:"Medium" },
    { id:16, text:"Two capacitors C in series. Dielectric K in one. Net capacitance:", options:["KC/(K+1)","2KC","C(K+1)/2","C/2K"], correct:0, chapter:"Electrostatics", difficulty:"Hard" },
    { id:17, text:"Ball dropped from h, hits ground at v. At what height is speed v/2?", options:["3h/4","h/2","h/4","3h/2"], correct:0, chapter:"Kinematics", difficulty:"Medium" },
    { id:18, text:"Escape velocity v from planet M,R. If R→4R, M→16M:", options:["2v","v","4v","v/2"], correct:0, chapter:"Gravitation", difficulty:"Medium" },
    { id:19, text:"Photoelectric effect: max KE depends on:", options:["Frequency","Intensity","Both","Neither"], correct:0, chapter:"Dual Nature", difficulty:"Easy" },
    { id:20, text:"Magnetic field at center of circular loop (radius R, current I):", options:["μ₀I/2R","μ₀I/R","μ₀I/4R","2μ₀I/R"], correct:0, chapter:"Magnetic Effects", difficulty:"Easy" },
  ], B: [
    { id:21, text:"F=(3î+4ĵ)N moves body from origin to (3,4)m. Work done = ___ J.", correct:"25", chapter:"WEP", difficulty:"Easy" },
    { id:22, text:"Car accelerates from rest at 2 m/s². Distance in 5th second = ___ m.", correct:"9", chapter:"Kinematics", difficulty:"Medium" },
    { id:23, text:"Equivalent resistance of 3Ω and 6Ω in parallel = ___ Ω.", correct:"2", chapter:"Current Electricity", difficulty:"Easy" },
    { id:24, text:"Spring k=200 N/m compressed 0.1m. PE stored = ___ J.", correct:"1", chapter:"WEP", difficulty:"Easy" },
    { id:25, text:"Frequencies 256 Hz and 260 Hz together. Beats/sec = ___.", correct:"4", chapter:"Waves", difficulty:"Easy" },
  ]},
  Chemistry: { A: [
    { id:26, text:"Hybridization of carbon in methane:", options:["sp³","sp²","sp","dsp²"], correct:0, chapter:"Chemical Bonding", difficulty:"Easy" },
    { id:27, text:"Strongest acid:", options:["HClO₄","HClO₃","HClO₂","HClO"], correct:0, chapter:"Chemical Bonding", difficulty:"Easy" },
    { id:28, text:"IUPAC name of CH₃CH(OH)CH₃:", options:["Propan-2-ol","Propan-1-ol","2-Methylethanol","Isopropanol"], correct:0, chapter:"GOC & Isomerism", difficulty:"Easy" },
    { id:29, text:"Sigma and pi bonds in CH₂=CH-CH=CH₂:", options:["9σ, 2π","7σ, 2π","8σ, 2π","10σ, 2π"], correct:0, chapter:"Chemical Bonding", difficulty:"Medium" },
    { id:30, text:"Highest lattice energy:", options:["NaF","NaCl","NaBr","NaI"], correct:0, chapter:"Chemical Bonding", difficulty:"Medium" },
    { id:31, text:"Oxidation state of Cr in K₂Cr₂O₇:", options:["+6","+3","+7","+2"], correct:0, chapter:"Redox", difficulty:"Easy" },
    { id:32, text:"Most stable carbocation:", options:["(CH₃)₃C⁺","CH₃CH₂⁺","CH₃⁺","C₆H₅CH₂⁺"], correct:0, chapter:"GOC", difficulty:"Easy" },
    { id:33, text:"Quantum number determining orbital shape:", options:["Azimuthal (l)","Principal (n)","Magnetic (mₗ)","Spin (mₛ)"], correct:0, chapter:"Atomic Structure", difficulty:"Easy" },
    { id:34, text:"pH of 0.01 M HCl:", options:["2","1","3","0.01"], correct:0, chapter:"Equilibrium", difficulty:"Easy" },
    { id:35, text:"Highest electronegativity:", options:["Fluorine","Chlorine","Oxygen","Nitrogen"], correct:0, chapter:"Periodic Table", difficulty:"Easy" },
    { id:36, text:"Shows geometrical isomerism:", options:["2-Butene","2-Butyne","Propene","Ethene"], correct:0, chapter:"GOC", difficulty:"Medium" },
    { id:37, text:"First order reaction rate depends on:", options:["First power","Square","Independent","Cube"], correct:0, chapter:"Kinetics", difficulty:"Easy" },
    { id:38, text:"Frenkel defect shown by:", options:["AgBr","NaCl","KCl","CsCl"], correct:0, chapter:"Solid State", difficulty:"Medium" },
    { id:39, text:"Reagent in Wurtz reaction:", options:["Na/dry ether","Zn/HCl","LiAlH₄","NaBH₄"], correct:0, chapter:"Hydrocarbons", difficulty:"Easy" },
    { id:40, text:"Coordination number of Na⁺ in NaCl:", options:["6","4","8","12"], correct:0, chapter:"Solid State", difficulty:"Easy" },
    { id:41, text:"Ore of aluminium:", options:["Bauxite","Galena","Calamine","Haematite"], correct:0, chapter:"p-Block", difficulty:"Easy" },
    { id:42, text:"Bond order of O₂:", options:["2","1","3","2.5"], correct:0, chapter:"Chemical Bonding", difficulty:"Medium" },
    { id:43, text:"Lucas test distinguishes:", options:["1°,2°,3° alcohols","Aldehydes/ketones","Acids/bases","Alkanes/alkenes"], correct:0, chapter:"Alcohols", difficulty:"Medium" },
    { id:44, text:"Shape of XeF₄:", options:["Square planar","Tetrahedral","See-saw","T-shaped"], correct:0, chapter:"p-Block", difficulty:"Medium" },
    { id:45, text:"Nessler's reagent is:", options:["K₂HgI₄","K₂Cr₂O₇","KMnO₄","K₄[Fe(CN)₆]"], correct:0, chapter:"Coordination", difficulty:"Medium" },
  ], B: [
    { id:46, text:"d-orbital electrons in Fe²⁺ (Z=26) = ___.", correct:"6", chapter:"d-Block", difficulty:"Easy" },
    { id:47, text:"Molarity: 4g NaOH in 500mL = ___ M.", correct:"0.2", chapter:"Solutions", difficulty:"Easy" },
    { id:48, text:"Lone pairs in H₂O = ___.", correct:"2", chapter:"Chemical Bonding", difficulty:"Easy" },
    { id:49, text:"Degree of unsaturation in benzene = ___.", correct:"4", chapter:"Hydrocarbons", difficulty:"Easy" },
    { id:50, text:"If Kc(A⇌B)=4, then Kc(B⇌A) = ___.", correct:"0.25", chapter:"Equilibrium", difficulty:"Easy" },
  ]},
  Mathematics: { A: [
    { id:51, text:"f(x)=x²+2x+1, f'(1) =", options:["4","2","3","1"], correct:0, chapter:"Differentiation", difficulty:"Easy" },
    { id:52, text:"∫₀¹ x² dx =", options:["1/3","1/2","1","2/3"], correct:0, chapter:"Integration", difficulty:"Easy" },
    { id:53, text:"Eccentricity of x²/25 + y²/16 = 1:", options:["3/5","4/5","5/3","4/3"], correct:0, chapter:"Conics", difficulty:"Medium" },
    { id:54, text:"|A|=5 for 3×3 matrix. |2A| =", options:["40","10","20","80"], correct:0, chapter:"Matrices", difficulty:"Medium" },
    { id:55, text:"Arrangements of MISSISSIPPI:", options:["34650","11!","5040","39916800"], correct:0, chapter:"P&C", difficulty:"Medium" },
    { id:56, text:"General solution of sin x = 1/2:", options:["nπ+(-1)ⁿπ/6","2nπ±π/6","nπ+π/6","nπ±π/3"], correct:0, chapter:"Trigonometry", difficulty:"Medium" },
    { id:57, text:"Distance between 3x+4y=9 and 6x+8y=15:", options:["3/10","3/5","6/5","1/2"], correct:0, chapter:"Straight Lines", difficulty:"Medium" },
    { id:58, text:"lim(x→0) sin(x)/x =", options:["1","0","∞","-1"], correct:0, chapter:"Limits", difficulty:"Easy" },
    { id:59, text:"Sum of first 20 AP terms (a=1, d=3):", options:["590","580","600","610"], correct:0, chapter:"Sequences", difficulty:"Easy" },
    { id:60, text:"P(A)=0.4, P(B)=0.3, independent. P(A∩B):", options:["0.12","0.7","0.1","0.42"], correct:0, chapter:"Probability", difficulty:"Easy" },
    { id:61, text:"Derivative of eˣ·sin x:", options:["eˣ(sinx+cosx)","eˣcosx","eˣsinx","eˣ(sinx-cosx)"], correct:0, chapter:"Differentiation", difficulty:"Easy" },
    { id:62, text:"Circle with center (1,2), radius 3:", options:["(x-1)²+(y-2)²=9","x²+y²=9","(x+1)²+(y+2)²=9","(x-1)²+(y-2)²=3"], correct:0, chapter:"Circles", difficulty:"Easy" },
    { id:63, text:"Vector ⊥ to î+ĵ and î+k̂:", options:["î-ĵ-k̂","î+ĵ+k̂","-î+ĵ-k̂","ĵ-k̂"], correct:0, chapter:"Vectors", difficulty:"Medium" },
    { id:64, text:"Area bounded by y=x², x-axis, x=2:", options:["8/3","4","2","4/3"], correct:0, chapter:"Area Under Curves", difficulty:"Easy" },
    { id:65, text:"Degree of d²y/dx²+(dy/dx)³+y=0:", options:["1","2","3","Not defined"], correct:0, chapter:"Diff. Equations", difficulty:"Easy" },
    { id:66, text:"Coefficient of x³ in (1+x)¹⁰:", options:["120","45","210","10"], correct:0, chapter:"Binomial", difficulty:"Easy" },
    { id:67, text:"Angle between direction ratios (1,1,0) and (0,1,1):", options:["60°","90°","45°","30°"], correct:0, chapter:"3D Geometry", difficulty:"Medium" },
    { id:68, text:"If z=3+4i, |z|=", options:["5","7","4","3"], correct:0, chapter:"Complex Numbers", difficulty:"Easy" },
    { id:69, text:"sin⁻¹(sin(π/6)):", options:["π/6","1/2","√3/2","π/3"], correct:0, chapter:"Inverse Trig", difficulty:"Easy" },
    { id:70, text:"Variance of 2,4,6,8,10:", options:["8","4","10","6"], correct:0, chapter:"Statistics", difficulty:"Medium" },
  ], B: [
    { id:71, text:"∫₀^(π/2) sin²x dx = π/___.", correct:"4", chapter:"Integration", difficulty:"Medium" },
    { id:72, text:"³C₂+⁴C₂+⁵C₂=ⁿC₃, n=___.", correct:"6", chapter:"P&C", difficulty:"Medium" },
    { id:73, text:"Real roots of x³-3x+2=0: ___.", correct:"2", chapter:"Quadratics", difficulty:"Medium" },
    { id:74, text:"A=[[1,2],[3,4]], tr(A)=___.", correct:"5", chapter:"Matrices", difficulty:"Easy" },
    { id:75, text:"Sum 1+1/2+1/4+... (infinite GP)=___.", correct:"2", chapter:"Sequences", difficulty:"Easy" },
  ]}
};

const EXAM_STATE_WORDS = { notVisited: "not visited", notAnswered: "not answered", answered: "answered", markedReview: "marked for review", answeredMarked: "answered and marked for review" };

export function TestInterface({ onFinish, onBack }) {
  const allQ = {}; SUBJECTS.forEach(s => { allQ[s] = [...QUESTIONS[s].A, ...QUESTIONS[s].B]; });
  const totalQ = SUBJECTS.reduce((a, s) => a + allQ[s].length, 0);
  const [curSub, setCurSub] = useState("Physics");
  const [curIdx, setCurIdx] = useState(0);
  const [answers, setAnswers] = useState({});
  const [statuses, setStatuses] = useState({});
  const [timeLeft, setTimeLeft] = useState(180*60);
  const [started, setStarted] = useState(false);
  const [showInst, setShowInst] = useState(true);
  const [showConfirm, setShowConfirm] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [sel, setSel] = useState(null);
  const [timePerQ, setTimePerQ] = useState({});
  const qTimer = useRef(Date.now());
  const { exited: fsExited, resume: fsResume } = useFullscreenLock(started);

  useEffect(() => { if (!started) return; const t = setInterval(() => setTimeLeft(p => { if (p<=0){clearInterval(t);doSubmit();return 0;} return p-1; }),1000); return ()=>clearInterval(t); }, [started]);

  const curQs = allQ[curSub]; const curQ = curQs[curIdx]; const qk = `${curSub}-${curQ.id}`; const isNum = curIdx >= 20;
  useEffect(() => { setSel(answers[qk]?.selected ?? null); if(!statuses[qk]) setStatuses(p=>({...p,[qk]:"notAnswered"})); }, [qk]);
  useEffect(() => { qTimer.current = Date.now(); }, [qk]);

  const recTime = () => { const e=(Date.now()-qTimer.current)/1000; setTimePerQ(p=>({...p,[qk]:(p[qk]||0)+e})); qTimer.current=Date.now(); };
  const saveNext = () => { recTime(); if(sel!==null){setAnswers(p=>({...p,[qk]:{selected:sel,isNumerical:isNum}}));setStatuses(p=>({...p,[qk]:p[qk]==="markedReview"?"answeredMarked":"answered"}));} if(curIdx<curQs.length-1)setCurIdx(i=>i+1); };
  const markReview = () => { recTime(); if(sel!==null){setAnswers(p=>({...p,[qk]:{selected:sel,isNumerical:isNum}}));setStatuses(p=>({...p,[qk]:"answeredMarked"}));}else{setStatuses(p=>({...p,[qk]:"markedReview"}));} if(curIdx<curQs.length-1)setCurIdx(i=>i+1); };
  const clearResp = () => { setSel(null); setAnswers(p=>{const n={...p};delete n[qk];return n;}); setStatuses(p=>({...p,[qk]:"notAnswered"})); };

  const doSubmit = () => {
    exitFullscreen(); // explicit, since onFinish below navigates away and unmounts this component
    recTime(); let score=0,correct=0,incorrect=0,unattempted=0; const subScores={}; const chapScores={}; const qDets=[];
    SUBJECTS.forEach(sub => { subScores[sub]={correct:0,incorrect:0,unattempted:0,score:0,total:allQ[sub].length,time:0};
      allQ[sub].forEach((q,idx)=>{ const k=`${sub}-${q.id}`; const a=answers[k]; const iN=idx>=20; const tt=timePerQ[k]||0; subScores[sub].time+=tt; let st="unattempted",ic=false;
        if(a){if(iN){ic=String(a.selected).trim()===String(q.correct).trim();}else{ic=parseInt(a.selected)===q.correct;} if(ic){score+=4;correct++;subScores[sub].correct++;subScores[sub].score+=4;st="correct";}else{score-=1;incorrect++;subScores[sub].incorrect++;subScores[sub].score-=1;st="incorrect";}}else{unattempted++;subScores[sub].unattempted++;st="unattempted";}
        if(!chapScores[q.chapter])chapScores[q.chapter]={correct:0,total:0,subject:sub}; chapScores[q.chapter].total++; if(st==="correct")chapScores[q.chapter].correct++;
        qDets.push({...q,subject:sub,userAnswer:a?.selected,status:st,timeTaken:tt,isNum:iN}); }); });
    onFinish({score,correct,incorrect,unattempted,total:totalQ,maxScore:totalQ*4,subjectScores:subScores,chapterScores:chapScores,qDetails:qDets,totalTime:180*60-timeLeft,timePerQ});
  };

  const fmt = s => `${String(Math.floor(s/3600)).padStart(2,"0")}:${String(Math.floor((s%3600)/60)).padStart(2,"0")}:${String(s%60).padStart(2,"0")}`;
  const statusOf = k => statuses[k] || "notVisited";
  const cnt = st => Object.values(statuses).filter(s=>s===st).length;
  const answeredCount = cnt("answered") + cnt("answeredMarked");
  const goTo = (sub, idx) => { recTime(); setCurSub(sub); setCurIdx(idx); };

  if (showInst) return (
    <main className="intro">
      <Logo />
      <h1>JEE Main mock test</h1>
      <p className="page-sub">The same pattern, timer and question palette as the real exam.</p>
      <div className="facts">
        <div className="fact-row"><span>Duration</span><b>180 minutes</b></div>
        <div className="fact-row"><span>Questions</span><b>75, 25 per subject</b></div>
        <div className="fact-row"><span>Each subject</span><b>20 MCQs, then 5 numerical</b></div>
        <div className="fact-row"><span>Marking</span><b>+4 correct, −1 wrong</b></div>
      </div>
      <h2>Question palette</h2>
      <div className="legend" style={{ marginTop: 0 }}>
        {LEGEND.map(([s, text]) => <div key={s} className="legend-item"><span className="sq" data-s={s} />{text}</div>)}
      </div>
      <p className="hint" style={{ marginTop: 18 }}>Save and next records your answer. Answers marked for review still count when you submit.</p>
      <div className="hero-actions">
        <button type="button" className="btn btn-primary btn-lg" onClick={()=>{requestFullscreen();setShowInst(false);setStarted(true);}}>Start the test</button>
        <button type="button" className="btn btn-secondary btn-lg" onClick={onBack}>Go back</button>
      </div>
    </main>
  );

  return (
    <div className="exam">
      <FullscreenGuard exited={fsExited} onResume={fsResume} />
      <header className="exam-top">
        <div className="exam-title"><LogoMark /><span>JEE Main mock <small>{curSub}</small></span></div>
        <div className={`timer ${timeLeft < 600 ? "is-low" : ""}`} role="timer" aria-label="Time left">{fmt(timeLeft)}</div>
      </header>
      <nav className="exam-tabs" aria-label="Subjects">
        {SUBJECTS.map(s => (
          <button key={s} type="button" className={`exam-tab ${curSub===s ? "active" : ""}`} aria-current={curSub===s || undefined} onClick={()=>goTo(s, 0)}>
            <span className="dot" style={{ background: SUBJECT_COLOR[s] }} />{s}
          </button>
        ))}
      </nav>
      <div className="exam-body">
        <main className="exam-main">
          <div className="seg exam-sections" role="group" aria-label="Section">
            <button type="button" aria-pressed={!isNum} onClick={()=>{recTime();setCurIdx(0);}}>Section A: MCQ</button>
            <button type="button" aria-pressed={isNum} onClick={()=>{recTime();setCurIdx(20);}}>Section B: numerical</button>
          </div>
          <div className="exam-q-head">
            <strong>Question {curIdx+1} of {curQs.length}</strong>
            <span className="tag"><span className="dot" style={{ background: DIFF_COLOR[curQ.difficulty] }} />{curQ.difficulty}</span>
          </div>
          <p className="exam-question">{curQ.text}</p>
          {isNum ? (
            <div className="field" style={{ maxWidth: 300 }}>
              <label className="field-label" htmlFor="num-answer">Your answer</label>
              <input id="num-answer" className="input num" inputMode="decimal" value={sel||""} onChange={e=>setSel(e.target.value)} placeholder="Type a number" />
            </div>
          ) : (
            <div className="options" role="radiogroup" aria-label="Options">
              {curQ.options.map((op,oi)=>(
                <button key={oi} type="button" role="radio" aria-checked={sel===oi} className={`option ${sel===oi ? "is-selected" : ""}`} onClick={()=>setSel(oi)}>
                  <span className="option-key">{LETTER(oi)}</span>
                  <span className="option-body">{op}</span>
                </button>
              ))}
            </div>
          )}
          <div className="exam-actions">
            <button type="button" className="btn btn-save" onClick={saveNext}>Save and next</button>
            <button type="button" className="btn btn-mark" onClick={markReview}>Mark for review</button>
            <button type="button" className="btn btn-secondary" onClick={clearResp}>Clear</button>
            <button type="button" className="btn btn-secondary" onClick={()=>{recTime();if(curIdx>0)setCurIdx(i=>i-1);}} disabled={curIdx===0}>Previous</button>
            <button type="button" className="btn btn-primary push" onClick={()=>setShowConfirm(true)}>Submit test</button>
          </div>
        </main>
        <button type="button" className="palette-toggle" aria-expanded={paletteOpen} aria-controls="question-palette" onClick={() => setPaletteOpen(!paletteOpen)}>{paletteOpen ? 'Hide' : 'Show'} question palette <span>{answeredCount} / {totalQ} answered</span></button>
        <aside id="question-palette" className="exam-side" data-open={paletteOpen} aria-label="Question palette">
          <div className="exam-count">
            <span><i className="sq" data-s="answered" />Answered <b>{cnt("answered")}</b></span>
            <span><i className="sq" data-s="unanswered" />Not answered <b>{cnt("notAnswered")}</b></span>
            <span><i className="sq" data-s="marked" />Marked <b>{cnt("markedReview") + cnt("answeredMarked")}</b></span>
            <span><i className="sq" data-s="idle" />Not visited <b>{totalQ - Object.keys(statuses).length}</b></span>
          </div>
          {SUBJECTS.map(sub=>(
            <div key={sub} className="pal-group">
              <h3>{sub}</h3>
              <div className="pal-grid">
                {allQ[sub].map((q,idx)=>{
                  const k=`${sub}-${q.id}`; const ic=curSub===sub&&curIdx===idx; const st=statusOf(k);
                  return (
                    <button key={q.id} type="button" className={`pal-btn ${ic ? "is-current" : ""}`} data-s={st}
                      aria-label={`${sub} question ${idx+1}, ${EXAM_STATE_WORDS[st]}`} aria-current={ic || undefined}
                      onClick={()=>goTo(sub, idx)}>{idx+1}</button>
                  );
                })}
              </div>
            </div>
          ))}
        </aside>
      </div>
      {showConfirm && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="submit-title">
          <div className="modal">
            <h2 id="submit-title">Submit the test?</h2>
            <p>You've answered {answeredCount} of {totalQ} questions. Answers can't be changed after you submit.</p>
            <div className="modal-actions">
              <button type="button" className="btn btn-primary" onClick={doSubmit}>Submit test</button>
              <button type="button" className="btn btn-secondary" onClick={()=>setShowConfirm(false)}>Keep going</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ================================================================
   ANALYSIS
   ================================================================ */
const OUTCOME = { correct: "correct", incorrect: "wrong", unattempted: "idle" };
const OUTCOME_WORD = { correct: "Correct", incorrect: "Wrong", unattempted: "Skipped" };
const TABS = [["overview", "Overview"], ["subjects", "Subjects"], ["chapters", "Chapters"], ["questions", "Questions"]];

export function AnalysisDashboard({ result, onHome, onBuddy }) {
  const [tab, setTab] = useState("overview");
  if (!result) return (
    <main className="wrap page">
      <div className="empty">
        <h3>No result to show</h3>
        <p>Results appear here right after you submit a mock test.</p>
        <button type="button" className="btn btn-primary" onClick={onHome}>Back to dashboard</button>
      </div>
    </main>
  );
  const {score,correct,incorrect,unattempted,total,maxScore,subjectScores,chapterScores,qDetails,totalTime}=result;
  const acc=correct>0?((correct/(correct+incorrect))*100).toFixed(1):0;
  const subData=SUBJECTS.map(s=>({name:s,correct:subjectScores[s].correct,incorrect:subjectScores[s].incorrect,unattempted:subjectScores[s].unattempted}));
  const pieD=[{name:"Correct",value:correct,color:GOOD},{name:"Wrong",value:incorrect,color:BAD},{name:"Skipped",value:unattempted,color:IDLE}];
  const radarD=Object.entries(chapterScores).slice(0,8).map(([c,d])=>({ch:c.length>14?c.slice(0,13)+"…":c,v:d.total>0?Math.round(d.correct/d.total*100):0}));
  const weakC=Object.entries(chapterScores).filter(([,d])=>d.total>0&&d.correct/d.total<0.5).sort((a,b)=>a[1].correct/a[1].total-b[1].correct/b[1].total);
  const strongC=Object.entries(chapterScores).filter(([,d])=>d.total>0&&d.correct/d.total>=0.5).sort((a,b)=>b[1].correct/b[1].total-a[1].correct/a[1].total);
  const squares = sub => qDetails.filter(q => q.subject === sub).map(q => OUTCOME[q.status]);

  return (
    <main className="wrap page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Mock test result</h1>
          <p className="page-sub">JEE Main pattern, {total} questions</p>
        </div>
        <div className="page-actions">
          <button type="button" className="btn btn-secondary" onClick={onBuddy}>Ask the assistant</button>
          <button type="button" className="btn btn-quiet" onClick={onHome}>Dashboard</button>
        </div>
      </div>

      <section className="panel result-panel" aria-label="Score">
        <div>
          <div className="score-big">{score}<small>/ {maxScore}</small></div>
          <p className="result-line" style={{ marginTop: 12 }}>{correct} correct, {incorrect} wrong, {unattempted} skipped</p>
        </div>
        <div className="result-squares">
          {SUBJECTS.map(s => (
            <div key={s} className="result-sub">
              <span className="result-sub-name"><span className="dot" style={{ background: SUBJECT_COLOR[s] }} />{s}</span>
              <Palette size="sm" states={squares(s)} label={s} />
            </div>
          ))}
        </div>
      </section>

      <div className="stats" style={{ marginTop: 16 }}>
        <div className="stat"><div className="stat-value">{acc}%</div><div className="stat-label">Accuracy on attempted</div></div>
        <div className="stat"><div className="stat-value">{Math.round(totalTime/60)} min</div><div className="stat-label">Time used of 180</div></div>
      </div>
      {/* Real rank/percentile estimate (scaled to JEE Main, historical JoSAA colleges) renders
          below via RankPredictor in pages/Analysis.jsx, once the attempt is saved server-side. */}

      <div className="seg tabs" role="group" aria-label="Result view">
        {TABS.map(([t, text]) => <button key={t} type="button" aria-pressed={tab===t} onClick={()=>setTab(t)}>{text}</button>)}
      </div>

      {tab==="overview" && (
        <div className="stack">
          <div className="grid-2">
            <div className="panel">
              <h2 className="panel-title">Answers</h2>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={pieD} cx="50%" cy="50%" innerRadius={58} outerRadius={84} paddingAngle={2} dataKey="value" stroke="none">
                    {pieD.map((e,i)=><Cell key={i} fill={e.color}/>)}
                  </Pie>
                  <Tooltip {...tooltipProps} />
                </PieChart>
              </ResponsiveContainer>
              <div className="chart-legend">
                {pieD.map(d => <span key={d.name}><i className="dot" style={{ background: d.color }} />{d.name} <b>{d.value}</b></span>)}
              </div>
            </div>
            <div className="panel">
              <h2 className="panel-title">By subject</h2>
              <ResponsiveContainer width="100%" height={236}>
                <BarChart data={subData} barSize={36}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="name" {...axisProps} />
                  <YAxis {...axisProps} width={28} />
                  <Tooltip {...tooltipProps} />
                  <Bar dataKey="correct" name="Correct" fill={GOOD} stackId="a" />
                  <Bar dataKey="incorrect" name="Wrong" fill={BAD} stackId="a" />
                  <Bar dataKey="unattempted" name="Skipped" fill={IDLE} stackId="a" radius={[6,6,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="panel">
            <h2 className="panel-title">Accuracy by chapter</h2>
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={radarD} outerRadius="66%">
                <PolarGrid stroke={LINE} />
                <PolarAngleAxis dataKey="ch" tick={{ fill: INK_2, fontSize: 12, fontFamily: fontBody }} />
                <PolarRadiusAxis angle={30} domain={[0,100]} tick={false} axisLine={false} />
                <Radar dataKey="v" name="Accuracy %" stroke={PEN} fill={PEN} fillOpacity={0.18} strokeWidth={2} />
                <Tooltip {...tooltipProps} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {tab==="subjects" && (
        <div className="stack">
          {SUBJECTS.map(sub=>{ const d=subjectScores[sub]; return (
            <div key={sub} className="panel">
              <div className="panel-head">
                <h2 className="panel-title" style={{ display: "flex", alignItems: "center", gap: 10 }}><span className="dot" style={{ background: SUBJECT_COLOR[sub] }} />{sub}</h2>
                <span className="row-value" style={{ fontSize: 22 }}>{d.score}<span className="faint" style={{ fontSize: 15 }}> / {d.total*4}</span></span>
              </div>
              <div className="bar" aria-hidden="true">
                <span style={{ width: `${d.correct/d.total*100}%`, background: GOOD }} />
                <span style={{ width: `${d.incorrect/d.total*100}%`, background: BAD }} />
              </div>
              <p className="muted" style={{ marginTop: 12, fontSize: 14.5 }}>
                {d.correct} correct, {d.incorrect} wrong, {d.unattempted} skipped, {Math.round(d.time/60)} min spent
              </p>
            </div>
          ); })}
        </div>
      )}

      {tab==="chapters" && (
        <div className="grid-2">
          <div className="panel">
            <h2 className="panel-title">Needs work</h2>
            {weakC.length===0 ? <p className="muted">No chapter is below 50%.</p> : (
              <div className="rows">
                {weakC.map(([c,d])=>(
                  <div key={c} className="row"><span className="row-main">{c}</span><span className="row-value" style={{ color: BAD }}>{d.correct}/{d.total}</span></div>
                ))}
              </div>
            )}
          </div>
          <div className="panel">
            <h2 className="panel-title">Strong</h2>
            {strongC.length===0 ? <p className="muted">No chapter is at 50% or above yet.</p> : (
              <div className="rows">
                {strongC.map(([c,d])=>(
                  <div key={c} className="row"><span className="row-main">{c}</span><span className="row-value" style={{ color: GOOD }}>{d.correct}/{d.total}</span></div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {tab==="questions" && (
        <div className="panel table-wrap" style={{ padding: "8px 12px" }}>
          <table className="table">
            <thead><tr><th>#</th><th>Subject</th><th>Chapter</th><th>Result</th><th>Yours</th><th>Answer</th><th>Time</th></tr></thead>
            <tbody>
              {qDetails.map((q,i)=>(
                <tr key={i}>
                  <td className="num">{i+1}</td>
                  <td>{q.subject}</td>
                  <td>{q.chapter}</td>
                  <td><span className="status"><span className="sq" data-s={OUTCOME[q.status]} />{OUTCOME_WORD[q.status]}</span></td>
                  <td className="num">{q.userAnswer!==undefined?(q.isNum?q.userAnswer:LETTER(parseInt(q.userAnswer))):"–"}</td>
                  <td className="num" style={{ fontWeight: 600 }}>{q.isNum?q.correct:LETTER(q.correct)}</td>
                  <td className="num">{q.timeTaken?Math.round(q.timeTaken)+"s":"–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}

/* ================================================================
   DASHBOARD OVERVIEW
   ================================================================ */
const START_SQUARES = ["answered", "answered", "unanswered", "answered", "marked", "answered", "idle", "idle", "idle", "idle"];

export function DashboardOverview({ featured, onStart, onFreeTest, onSubjectTest, profile, statCards, history, subjectTrends }) {
  const first = profile?.name?.split(" ")[0];
  const classText = profile?.class_level ? (profile.class_level === "dropper" ? "dropper" : `Class ${profile.class_level}`) : null;
  const hasData = statCards && statCards.length > 0;

  return (
    <main className="wrap page">
      <div className="page-head">
        <div>
          <span className="eyebrow dashboard-eyebrow">OVERVIEW</span>
          <h1 className="page-title">{first ? `Welcome back, ${first}.` : "Your dashboard"}</h1>
          <p className="dashboard-context">Your tests, results and next practice session.</p>
          {profile?.username && <p className="page-sub">@{profile.username}{classText ? `, ${classText}` : ""}</p>}
        </div>
      </div>

      {featured}
      <span className="section-label">OTHER WAYS TO PRACTISE</span>
      <section className="start" aria-label="Start a test">
        <div className="start-tile start-main">
          <Palette states={START_SQUARES} size="sm" decorative />
          <span className="start-label"><Clock3 size={14}/> 180 MIN · 75 QUESTIONS</span>
          <h2>Full mock test</h2>
          <p>75 questions in 3 hours, on the same screen and pattern as JEE Main.</p>
          <button type="button" className="btn btn-invert" onClick={onStart}>Start a mock <ArrowUpRight size={16}/></button>
        </div>
        {onSubjectTest && (
          <div className="start-tile">
            <span className="start-label"><Target size={14}/> CHAPTER & SUBJECT TESTS</span>
            <h2>Subject practice</h2>
            <p>Practise one subject, or a single chapter, from the question bank.</p>
            <button type="button" className="btn btn-secondary" onClick={onSubjectTest}>Choose a subject</button>
          </div>
        )}
        {onFreeTest && (
          <div className="start-tile">
            <span className="start-label"><BookOpen size={14}/> 5 MIN · 10 QUESTIONS</span>
            <h2>Quick diagnostic</h2>
            <p>Ten timed questions across Physics, Chemistry and Maths.</p>
            <button type="button" className="btn btn-secondary" onClick={onFreeTest}>Take the free test</button>
          </div>
        )}
      </section>

      {hasData ? (
        <div className="stack">
          <div className="stats">
            {statCards.map(c => (
              <div key={c.k} className="stat"><div className="stat-value">{c.v}</div><div className="stat-label">{c.l}</div></div>
            ))}
          </div>
          <div className="grid-2">
            <div className="panel">
              <h2 className="panel-title">Score by test</h2>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={history}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="t" {...axisProps} />
                  <YAxis {...axisProps} width={32} />
                  <Tooltip {...tooltipProps} cursor={{ stroke: LINE }} />
                  <Line isAnimationActive={false} type="monotone" dataKey="s" name="Score" stroke={PEN} strokeWidth={2.5} dot={{ r: 3.5, fill: PEN, strokeWidth: 0 }} activeDot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="panel">
              <h2 className="panel-title">Accuracy by subject</h2>
              <ResponsiveContainer width="100%" height={188}>
                <LineChart data={subjectTrends}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="t" {...axisProps} />
                  <YAxis {...axisProps} width={45} domain={[0,100]} unit="%" />
                  <Tooltip {...tooltipProps} cursor={{ stroke: LINE }} />
                  <Line isAnimationActive={false} type="monotone" dataKey="P" name="Physics" stroke={SUBJECT_COLOR.Physics} strokeWidth={2.5} dot={false} />
                  <Line isAnimationActive={false} type="monotone" dataKey="C" name="Chemistry" stroke={SUBJECT_COLOR.Chemistry} strokeWidth={2.5} dot={false} />
                  <Line isAnimationActive={false} type="monotone" dataKey="M" name="Maths" stroke={SUBJECT_COLOR.Mathematics} strokeWidth={2.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
              <div className="chart-legend">
                {SUBJECTS.map(s => <span key={s}><i className="dot" style={{ background: SUBJECT_COLOR[s] }} />{s}</span>)}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="empty">
          <Palette states={["idle", "idle", "idle", "idle", "idle"]} decorative />
          <h3>Your first result goes here.</h3>
          <p>Take a warm-up to set your starting point. Your results and subject accuracy will have a home right here.</p>
          <button type="button" className="btn btn-primary" onClick={onFreeTest || onStart}>Take your first test</button>
        </div>
      )}
    </main>
  );
}

/* ================================================================
   STUDY ASSISTANT
   ================================================================ */
export function AIBuddy({ result }) {
  const [msgs,setMsgs]=useState([{r:"b",t:"Hi. Ask me about strategy, time management or a subject. If you came here from a mock result, I can also talk through your score and weak chapters."}]);
  const [inp,setInp]=useState("");const[typing,setTyping]=useState(false);const ref=useRef(null);
  useEffect(()=>{if(ref.current)ref.current.scrollTop=ref.current.scrollHeight;},[msgs,typing]);

  const respond=(m)=>{const l=m.toLowerCase();
    if(l.includes("weak")||l.includes("improve")){if(result){const w=Object.entries(result.chapterScores).filter(([,d])=>d.total>0&&d.correct/d.total<0.5).map(([c])=>c);return`Your weakest chapters right now: ${w.join(", ")||"none, you're above 50% everywhere"}. I'd put about two focused hours a day into these. Want a study plan?`;}return"Take a mock test first. I need some data before I can pinpoint your weak areas.";}
    if(l.includes("score")||l.includes("rank")||l.includes("how did")){if(result)return`You scored ${result.score}/${result.maxScore} with ${((result.correct/(result.correct+result.incorrect))*100).toFixed(1)}% accuracy. You left ${result.unattempted} unattempted, and those are recoverable marks.`;return"No test data yet. Take a mock and I'll break down your score and predicted rank.";}
    if(l.includes("time")||l.includes("speed"))return"A workable rule: about 55 minutes per subject, 1.5 to 2 minutes per MCQ and about 3 minutes per numerical. If a question runs past 3 minutes, mark it for review and move on. Save the last 15 minutes for the marked ones.";
    if(l.includes("physic"))return"Priority order: Current Electricity and Electrostatics first, then Mechanics (laws of motion, work and energy, rotation), Modern Physics for quick marks, and Optics. HC Verma first, then DC Pandey for practice.";
    if(l.includes("chem"))return"Inorganic: read NCERT thoroughly, more than once. Physical: drill numericals. Organic: master the named reactions and mechanisms. NCERT alone covers a large share of the Chemistry paper.";
    if(l.includes("math"))return"Highest return: Coordinate Geometry and Calculus, then Algebra (matrices, permutations and combinations, probability). Work through chapter-wise PYQs from the last five years.";
    if(l.includes("stress")||l.includes("motivat")||l.includes("anxious"))return"Take a breath. Work in 50-minute blocks with 10-minute breaks, keep some daily exercise, and protect 7+ hours of sleep. Consistency beats burnout.";
    if(l.includes("plan")||l.includes("schedule"))return"A sample day:\n6–8am  Weakest subject\n8–10am  Chapter revision\n10–11am  Break\n11am–1pm  Timed problems\n2–4pm  Mock sections\n4–5pm  PYQs\n5–6pm  Error analysis\n7–8pm  Formula review\nWeekends: one full mock and its analysis.";
    return"Focus on why a formula works, not just what it says. If you can explain a concept plainly, you own it. Which topic should we dig into?";
  };

  const ask=(m)=>{setMsgs(p=>[...p,{r:"u",t:m}]);setTyping(true);setTimeout(()=>{setMsgs(p=>[...p,{r:"b",t:respond(m)}]);setTyping(false);},550+Math.random()*550);};
  const send=()=>{if(!inp.trim())return;const m=inp.trim();setInp("");ask(m);};
  const quicks=["How did I do?","Weak chapters","Physics tips","Chemistry tips","Maths strategy","Time management","Feeling stressed","Daily plan"];

  return (
    <main className="chat">
      <div className="chat-head">
        <h1>Study assistant</h1>
        <p>{result ? "It can see the mock you just finished." : "Open it from a mock result to talk through your score."}</p>
      </div>
      <div ref={ref} className="chat-log" aria-live="polite">
        {msgs.map((m,i)=><div key={i} className={`msg ${m.r==="u" ? "msg-me" : "msg-bot"}`}>{m.t}</div>)}
        {typing && <div className="msg msg-bot typing" aria-label="The assistant is typing"><i /><i /><i /></div>}
      </div>
      <div className="chips">
        {quicks.map(a=><button key={a} type="button" className="chip" onClick={()=>ask(a)}>{a}</button>)}
      </div>
      <form className="composer" onSubmit={e=>{e.preventDefault();send();}}>
        <label className="visually-hidden" htmlFor="chat-input">Message</label>
        <input id="chat-input" className="input" value={inp} onChange={e=>setInp(e.target.value)} placeholder="Ask about JEE prep" autoComplete="off" />
        <button type="submit" className="btn btn-primary" disabled={!inp.trim()}>Send</button>
      </form>
    </main>
  );
}
