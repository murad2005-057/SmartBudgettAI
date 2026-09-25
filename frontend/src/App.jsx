import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { LuShieldCheck } from 'react-icons/lu'
import { OnboardingLayout } from './components/onboarding/OnboardingLayout'
import { ACCOUNT_STORAGE_KEY, ONBOARDING_ACTIVE_KEY } from './hooks/useOnboardingForm'
import { registerUser } from './services/api'
import './App.css'

const API_BASE = 'http://127.0.0.1:8000/api'

export function App() {
  const navigate = useNavigate()

  const savedAccount = (() => {
    try {
      const value = window.localStorage.getItem(ACCOUNT_STORAGE_KEY)
      return value ? JSON.parse(value) : null
    } catch {
      return null
    }
  })()

  const [showOnboarding, setShowOnboarding] = useState(() =>
    window.localStorage.getItem(ONBOARDING_ACTIVE_KEY) === 'true'
  )
  
  const [formData, setFormData] = useState(savedAccount?.formData || {
    fullName: '',
    email: '',
    password: ''
  })

  const [touched, setTouched] = useState({
    fullName: false,
    email: false,
    password: false
  })

  const [isSubmitted, setIsSubmitted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [apiError, setApiError] = useState(null)

  // Check backend on mount if localStorage was cleared, to see if user has an active plan session
  useEffect(() => {
    const checkServerSession = async () => {
      const token = localStorage.getItem('access_token') || localStorage.getItem('token')
      if (!token) return

      try {
        const response = await axios.get(`${API_BASE}/financial-inquiry/status/`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (response.data) {
          window.localStorage.setItem(ONBOARDING_ACTIVE_KEY, 'true')
          setShowOnboarding(true)
        }
      } catch (err) {
        // No active backend session found, clear local flags if necessary
      }
    }

    if (!showOnboarding) {
      checkServerSession()
    }
  }, [showOnboarding])

  // Validation functions
  const isFullNameValid = formData.fullName.trim().length > 0

  const isEmailValid =
    formData.email.trim().includes('@') &&
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email.trim())

  const isPasswordValid =
    formData.password.length >= 8 &&
    /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?]/.test(formData.password)

  const isFormValid = isFullNameValid && isEmailValid && isPasswordValid

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => {
      const nextFormData = { ...prev, [name]: value }
      window.localStorage.setItem(ACCOUNT_STORAGE_KEY, JSON.stringify({ formData: nextFormData }))
      return nextFormData
    })
  }

  const handleBlur = (e) => {
    const { name } = e.target
    setTouched((prev) => ({ ...prev, [name]: true }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setApiError(null)
    setTouched({
      fullName: true,
      email: true,
      password: true
    })

    if (!isFormValid) return

    setIsLoading(true)

    try {
      // 1. Try to register a new account first
      await registerUser({
        fullName: formData.fullName.trim(),
        email: formData.email.trim(),
        password: formData.password
      })

      setIsSubmitted(true)
      window.localStorage.setItem(ONBOARDING_ACTIVE_KEY, 'true')
      window.localStorage.setItem(ACCOUNT_STORAGE_KEY, JSON.stringify({ formData }))

      setTimeout(() => {
        setShowOnboarding(true)
      }, 500)

    } catch (err) {
      // 2. If registration fails because the email is already registered, log in automatically
      const isEmailTaken = err.response?.status === 400 || (err.message && err.message.toLowerCase().includes('email'))

      if (isEmailTaken) {
        try {
          // Attempt to log in with the existing credentials
          const loginRes = await axios.post(`${API_BASE}/login/`, {
            email: formData.email.trim(),
            password: formData.password
          })

          const token = loginRes.data.access_token || loginRes.data.token || loginRes.data.access
          if (token) {
            localStorage.setItem('access_token', token)
          }

          window.localStorage.setItem(ACCOUNT_STORAGE_KEY, JSON.stringify({ formData }))

          // 3. Fetch their session status to redirect to their last saved summary table
          const headers = { Authorization: `Bearer ${token}` }
          const statusRes = await axios.get(`${API_BASE}/financial-inquiry/status/`, { headers })
          const sessionId = statusRes.data.session_id || statusRes.data.sessionId

          if (sessionId) {
            navigate(`/results/${sessionId}`)
          } else {
            // Fallback if session ID isn't returned directly
            setIsSubmitted(true)
            window.localStorage.setItem(ONBOARDING_ACTIVE_KEY, 'true')
            setTimeout(() => { setShowOnboarding(true) }, 500)
          }

        } catch (loginErr) {
          setApiError('Bu e-poçt artıq qeydiyyatdadır, lakin daxil etdiyiniz şifrə yanlışdır.')
        }
      } else {
        setApiError(err.message || 'Qeydiyyat zamanı xəta baş verdi.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const showFullNameError = (touched.fullName || isSubmitted) && !isFullNameValid
  const showEmailError = (touched.email || isSubmitted) && !isEmailValid
  const showPasswordError = (touched.password || isSubmitted) && !isPasswordValid

  if (showOnboarding) {
    const displayName = formData.fullName.trim().split(' ')[0] || 'User'
    return <OnboardingLayout userName={displayName} />
  }

  return (
    <main className="app-layout">
      {/* SOL PANEL */}
      <section className="left-panel">
        <header className="brand-container">
          <div className="brand-icon-box" aria-hidden="true">
            <svg
              className="brand-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <div className="brand-text">
            <h1 className="brand-title">SmartBudget AI</h1>
            <p className="brand-subtitle">Maliyyə gələcəyini ağıllı şəkildə planlaşdır</p>
          </div>
        </header>

        <div className="hero-main-content">
          <div className="pill-badge-outline">
            <svg className="spark-icon" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2z" />
            </svg>
            <span>Fərdiləşdirilmiş AI planı</span>
          </div>

          <h2 className="hero-heading">
            <span className="headline-dark">İllik büdcəni</span>
            <span className="headline-orange">ağıllı şəkildə planla</span>
          </h2>

          <p className="hero-body-text">
            Bir neçə sadə suala cavab verərək AI ilə gəlir və xərclərinə uyğun fərdiləşdirilmiş illik büdcə plan hazırla.
          </p>

          <div className="pill-badge-solid">
            <LuShieldCheck className="shield-icon" size={18} />
            <span>Real və balanslı plan</span>
          </div>
        </div>

        <div className="left-footer-spacer"></div>
      </section>

      {/* SAĞ PANEL */}
      <section className="right-panel">
        <div className="card-container">
          <h3 className="card-title">Başlamaq üçün məlumatlarınızı daxil edin</h3>
          <p className="card-desc">Planınız yalnız bu brauzerdə saxlanılır.</p>

          {apiError && (
            <div className="error-banner" role="alert" style={{ color: '#ef4444', marginBottom: '1rem' }}>
              <span>{apiError}</span>
            </div>
          )}

          {isSubmitted && isFormValid && !apiError && (
            <div className="success-banner" role="alert">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 10 1 1-5.93-9.14" strokeLinecap="round" strokeLinejoin="round"/>
                <polyline points="22 4 12 14.01 9 11.01" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>Uğurla qeydiyyatdan keçdiniz!</span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="form-field">
              <label htmlFor="fullName" className="field-label">Ad və soyad</label>
              <input
                id="fullName"
                name="fullName"
                type="text"
                className={`field-input ${showFullNameError ? 'has-error' : ''}`}
                value={formData.fullName}
                onChange={handleChange}
                onBlur={handleBlur}
                aria-invalid={showFullNameError}
                disabled={isLoading}
              />
              {showFullNameError && <p className="error-text">Ad və soyad hissəsini doldurun.</p>}
            </div>

            <div className="form-field">
              <label htmlFor="email" className="field-label">Email</label>
              <input
                id="email"
                name="email"
                type="email"
                className={`field-input ${showEmailError ? 'has-error' : ''}`}
                value={formData.email}
                onChange={handleChange}
                onBlur={handleBlur}
                aria-invalid={showEmailError}
                disabled={isLoading}
              />
              {showEmailError && <p className="error-text">Düzgün email ünvanı daxil edin ('@' işarəsi mütləqdir).</p>}
            </div>

            <div className="form-field">
              <label htmlFor="password" className="field-label">Şifrə</label>
              <input
                id="password"
                name="password"
                type="password"
                className={`field-input ${showPasswordError ? 'has-error' : ''}`}
                value={formData.password}
                onChange={handleChange}
                onBlur={handleBlur}
                aria-invalid={showPasswordError}
                disabled={isLoading}
              />
              {showPasswordError && <p className="error-text">Şifrə ən azı 8 simvol olmalı və xüsusi simvol ehtiva etməlidir.</p>}
            </div>

            <button
              type="submit"
              className="btn-submit"
              disabled={!isFormValid || isLoading}
            >
              <span>{isLoading ? 'Gözləyin...' : 'Planlamaya başla'}</span>
              <svg className="btn-arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          </form>
        </div>
      </section>
    </main>
  )
}

export default App