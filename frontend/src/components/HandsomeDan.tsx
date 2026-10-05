// Handsome Dan, Yale's bulldog mascot, as an ink-style line drawing (SVG, no image file):
// pen strokes of varying weight on warm paper, with cross-hatching for shadow.
export default function HandsomeDan({ size = 96 }: { size?: number }) {
  const ink = '#1f2124'
  const paper = '#ebe5da'

  return (
    <svg
      className="handsome-dan"
      width={size}
      height={size}
      viewBox="0 0 120 120"
      role="img"
      aria-label="Ink drawing of Handsome Dan, the Yale bulldog"
    >
      <circle cx="60" cy="60" r="58" fill={paper} />
      <circle cx="60" cy="60" r="55.5" fill="none" stroke={ink} strokeOpacity="0.5" strokeWidth="0.8" />

      <g fill="none" stroke={ink} strokeLinecap="round" strokeLinejoin="round">
        {/* rose ears, folded back at the sides of the skull */}
        <path d="M33 36c-6-1-12-5-12-10 1-4 7-4 12-1 3 2 5 5 6 8" strokeWidth="2.2" />
        <path d="M24 27c3 0 7 2 9 5" strokeWidth="0.9" />
        <path d="M87 36c6-1 12-5 12-10-1-4-7-4-12-1-3 2-5 5-6 8" strokeWidth="2.2" />
        <path d="M96 27c-3 0-7 2-9 5" strokeWidth="0.9" />

        {/* broad, flat skull and wide cheeks */}
        <path d="M34 34c7-5 16-7 26-7s19 2 26 7c7 5 11 13 11 22 0 6-2 11-5 15" strokeWidth="2.4" />
        <path d="M34 34c-7 5-11 13-11 22 0 6 2 11 5 15" strokeWidth="2.4" />

        {/* forehead wrinkles */}
        <path d="M45 34c5-2 10-2 15 0s10 2 15 0" strokeWidth="1.2" />
        <path d="M43 39c6-2 11-2 17 0s11 2 17 0" strokeWidth="1.1" />
        <path d="M60 30v12" strokeWidth="0.9" />

        {/* heavy brows over low, wide-set eyes */}
        <path d="M34 45c3-4 10-5 14-1" strokeWidth="2.2" />
        <path d="M86 45c-3-4-10-5-14-1" strokeWidth="2.2" />

        {/* the "rope" fold over the pushed-in nose */}
        <path d="M43 56c4-7 30-7 34 0" strokeWidth="1.8" />
        <path d="M46 59c-2 1-4 1-6 0M74 59c2 1 4 1 6 0" strokeWidth="1" />

        {/* flews: upper lips hanging from the nose into heavy jowls */}
        <path d="M60 66c-5 6-12 7-19 4" strokeWidth="1.8" />
        <path d="M60 66c5 6 12 7 19 4" strokeWidth="1.8" />
        <path d="M28 71c0 9 5 16 13 18 4 1 7 0 9-2" strokeWidth="2.4" />
        <path d="M92 71c0 9-5 16-13 18-4 1-7 0-9-2" strokeWidth="2.4" />

        {/* protruding lower jaw (underbite) */}
        <path d="M48 80c3 7 7 10 12 10s9-3 12-10" strokeWidth="2.2" />
        <path d="M50 80c6 2 14 2 20 0" strokeWidth="1.4" />

        {/* chest and collar */}
        <path d="M38 92c5 8 13 13 22 13s17-5 22-13" strokeWidth="1.5" />
        <path d="M55 104l5 4 5-4M60 108v5" strokeWidth="1.6" />

        {/* cross-hatching: cheek, jowl, and under-jaw shadow */}
        <g strokeWidth="0.6" strokeOpacity="0.75">
          <path d="M30 60l5-5M30 65l7-7M31 70l8-8M33 75l8-8M36 79l6-6" />
          <path d="M90 60l-5-5M90 65l-7-7M89 70l-8-8M87 75l-8-8M84 79l-6-6" />
          <path d="M52 92l3-3M57 93l3-3M62 93l3-3M67 92l3-3" />
          <path d="M66 28l3 3M72 29l3 3M78 31l2 2" />
        </g>
      </g>

      {/* ink-filled eyes, nose, and lower canines */}
      <g fill={ink}>
        <circle cx="41" cy="49" r="3.3" />
        <circle cx="79" cy="49" r="3.3" />
        <path d="M49 60c0-3 5-5 11-5s11 2 11 5-5 6-11 6-11-3-11-6Z" />
      </g>
      <g fill={paper}>
        <circle cx="42.3" cy="47.8" r="1" />
        <circle cx="80.3" cy="47.8" r="1" />
        <ellipse cx="55" cy="58.5" rx="2.4" ry="1.1" />
        <path d="M52 81l2.2-6 2.3 6.6Z" />
        <path d="M68 81l-2.2-6-2.3 6.6Z" />
      </g>
      <path d="M52 81l2.2-6 2.3 6.6M68 81l-2.2-6-2.3 6.6" fill="none" stroke={ink} strokeWidth="1.1" strokeLinejoin="round" />
      <path d="M60 66v-2" stroke={ink} strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}
