// The Campus Customs seal logo, drawn in SVG (no image file).
export default function Seal({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 200 200" role="img" aria-label="Campus Customs seal">
      <defs>
        {/* starts at the left so "CAMPUS CUSTOMS" arcs across the top */}
        <path id="seal-ring" d="M21,100 a79,79 0 1,1 158,0 a79,79 0 1,1 -158,0" />
      </defs>
      <circle cx="100" cy="100" r="94" fill="none" stroke="#ebe5db" strokeWidth="1.5" />
      <circle cx="100" cy="100" r="66" fill="none" stroke="#ebe5db" strokeWidth="0.8" />
      <text fontFamily="var(--font-mono)" fontSize="11" fill="#ebe5db" letterSpacing="3">
        <textPath href="#seal-ring" textLength="490" lengthAdjust="spacing">
          CAMPUS CUSTOMS · NEW HAVEN, CT ·
        </textPath>
      </text>
      <text
        x="100"
        y="118"
        textAnchor="middle"
        fontFamily="var(--font-serif)"
        fontStyle="italic"
        fontSize="58"
        fill="#ebe5db"
      >
        CC
      </text>
      <line x1="78" y1="132" x2="122" y2="132" stroke="#b8946f" strokeWidth="1.5" />
      <circle cx="100" cy="146" r="3" fill="#3a5f92" />
    </svg>
  )
}
