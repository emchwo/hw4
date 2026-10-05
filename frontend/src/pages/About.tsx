import { Link } from 'react-router-dom'
import Closeup from '../components/Closeup'

const VALUES = [
  { title: 'Community', text: 'Made for the whole Yale family — first-years to grandparents in the stands.' },
  { title: 'Tradition', text: 'Classic marks, college crests, and the colors behind every stitch.' },
  { title: 'Quality', text: 'Soft, durable fabrics that hold up season after season.' },
]

export default function About() {
  return (
    <>
      <section className="section about-hero">
        <div className="container about-split">
          <div>
            <span className="eyebrow">About Us</span>
            <h1>Made for the people who make Yale home.</h1>
            <p className="lead">
              Campus Customs curates apparel that celebrates Yale — comfortable, wearable, and easy to love. For
              students, alumni, faculty, and families, on campus or miles away.
            </p>
            <Link to="/products" className="btn btn-ghost">
              Shop now
            </Link>
          </div>
          <Closeup src="/images/super-heavyweight-crewneck-arched-yale-crest.jpg" zoom={1.5} focus="50% 38%" />
        </div>
      </section>

      <section className="section">
        <div className="container values-list">
          {VALUES.map((v) => (
            <div key={v.title}>
              <h3>{v.title}</h3>
              <p>{v.text}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
