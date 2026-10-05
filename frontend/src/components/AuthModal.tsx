import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { useAuth } from '../auth'
import HandsomeDan from './HandsomeDan'

function PasswordInput({
  name,
  value,
  onChange,
  autoComplete,
}: {
  name: string
  value: string
  onChange: (v: string) => void
  autoComplete: string
}) {
  const [show, setShow] = useState(false)
  return (
    <div className="password-field">
      <input
        type={show ? 'text' : 'password'}
        name={name}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete}
        maxLength={128}
        required
      />
      <button type="button" className="password-toggle" onClick={() => setShow((s) => !s)}>
        {show ? 'Hide' : 'Show'}
      </button>
    </div>
  )
}

function LoginForm() {
  const { login, openModal } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(email, password)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
      setPassword('')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="auth-form">
      <div className="auth-mascot">
        <HandsomeDan size={92} />
      </div>
      <h2 id="auth-title">Welcome back, Bulldog</h2>
      <p className="muted">Log in to your Campus Customs account.</p>

      <label>
        Email
        <input
          type="email"
          name="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          placeholder="you@yale.edu"
          required
          autoFocus
        />
      </label>
      <label>
        Password
        <PasswordInput name="password" value={password} onChange={setPassword} autoComplete="current-password" />
      </label>

      {error && <p className="notice notice-error" role="alert">{error}</p>}

      <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
        {busy ? 'Logging in…' : 'Log In'}
      </button>
      <p className="auth-switch muted">
        New here?{' '}
        <button type="button" className="text-link" onClick={() => openModal('register')}>
          Create an account
        </button>
      </p>
    </form>
  )
}

function passwordProblems(pw: string): string[] {
  const problems = []
  if (pw.length < 8) problems.push('at least 8 characters')
  if (!/[A-Za-z]/.test(pw)) problems.push('a letter')
  if (!/\d/.test(pw)) problems.push('a number')
  return problems
}

function RegisterForm() {
  const { register, openModal } = useAuth()
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', password: '', confirm_password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const set = (key: keyof typeof form) => (value: string) => setForm((f) => ({ ...f, [key]: value }))
  const problems = passwordProblems(form.password)
  const mismatch = form.confirm_password.length > 0 && form.password !== form.confirm_password

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (problems.length) return setError(`Password needs ${problems.join(', ')}.`)
    if (form.password !== form.confirm_password) return setError('Passwords do not match.')
    setBusy(true)
    try {
      await register(form)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="auth-form">
      <h2 id="auth-title">Create your account</h2>
      <p className="muted">Join Campus Customs for a faster, more personal shopping experience.</p>

      <div className="form-row">
        <label>
          First name
          <input
            name="first_name"
            value={form.first_name}
            onChange={(e) => set('first_name')(e.target.value)}
            autoComplete="given-name"
            maxLength={50}
            required
            autoFocus
          />
        </label>
        <label>
          Last name
          <input
            name="last_name"
            value={form.last_name}
            onChange={(e) => set('last_name')(e.target.value)}
            autoComplete="family-name"
            maxLength={50}
            required
          />
        </label>
      </div>
      <label>
        Email
        <input
          type="email"
          name="email"
          value={form.email}
          onChange={(e) => set('email')(e.target.value)}
          autoComplete="email"
          placeholder="you@yale.edu"
          required
        />
      </label>
      <label>
        Password
        <PasswordInput name="password" value={form.password} onChange={set('password')} autoComplete="new-password" />
        <span className={`field-hint ${form.password && problems.length === 0 ? 'ok' : ''}`}>
          {form.password && problems.length === 0
            ? '✓ Looks good'
            : 'At least 8 characters, with a letter and a number.'}
        </span>
      </label>
      <label>
        Confirm password
        <PasswordInput
          name="confirm_password"
          value={form.confirm_password}
          onChange={set('confirm_password')}
          autoComplete="new-password"
        />
        {mismatch && <span className="field-hint error">Passwords don’t match yet.</span>}
      </label>

      {error && <p className="notice notice-error" role="alert">{error}</p>}

      <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
        {busy ? 'Creating account…' : 'Create Account'}
      </button>
      <p className="auth-switch muted">
        Already have an account?{' '}
        <button type="button" className="text-link" onClick={() => openModal('login')}>
          Log in
        </button>
      </p>
    </form>
  )
}

function Overlay({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [onClose])

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <button className="modal-close" aria-label="Close" onClick={onClose}>
          ×
        </button>
        {children}
      </div>
    </div>
  )
}

export default function AuthModal() {
  const { modal, closeModal } = useAuth()
  if (!modal) return null
  return (
    <Overlay onClose={closeModal}>
      {modal === 'login' ? <LoginForm key="login" /> : <RegisterForm key="register" />}
    </Overlay>
  )
}
