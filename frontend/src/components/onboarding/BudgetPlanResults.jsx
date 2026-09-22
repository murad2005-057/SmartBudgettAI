import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { RefreshCw } from 'lucide-react'
import axios from 'axios'
import { ONBOARDING_ACTIVE_KEY, ACCOUNT_STORAGE_KEY } from '../../hooks/useOnboardingForm'
import { StepSummary } from "./steps/StepSummary";

export function BudgetPlanResults() {
  const navigate = useNavigate()
  
  const [loading, setLoading] = useState(true)
  const [summaryData, setSummaryData] = useState(null)
  const [goalsData, setGoalsData] = useState([]) // <--- Added missing state hook
  const [monthlyTableData, setMonthlyTableData] = useState([]) // <--- Added missing state hook
  const [comparisonData, setComparisonData] = useState([]) // <--- Added missing state hook
  const [error, setError] = useState(null)

  const userName = (() => {
    try {
      const stored = window.localStorage.getItem(ACCOUNT_STORAGE_KEY)
      const parsed = stored ? JSON.parse(stored) : null
      return parsed?.formData?.fullName?.trim().split(' ')[0] || 'İstifadəçi'
    } catch {
      return 'İstifadəçi'
    }
  })()

  useEffect(() => {
    const fetchAllData = async () => {
      try {
        setLoading(true)
        const token = localStorage.getItem('access_token') || localStorage.getItem('token')
        const headers = { 'Authorization': `Bearer ${token}` }

        // Fetch using paths matching your Django urls.py
        const [summaryRes, goalsRes, tableRes, comparisonRes] = await Promise.all([
          axios.get(`http://127.0.0.1:8000/api/summary/`, { headers }),
          axios.get(`http://127.0.0.1:8000/api/summary/goals/`, { headers }).catch(() => ({ data: [] })),
          axios.get(`http://127.0.0.1:8000/api/summary/table/`, { headers }).catch(() => ({ data: [] })),
          axios.get(`http://127.0.0.1:8000/api/summary/comparison/`, { headers }).catch(() => ({ data: [] }))
        ])

        setSummaryData(summaryRes.data)
        setGoalsData(goalsRes.data)
        setMonthlyTableData(tableRes.data)
        setComparisonData(comparisonRes.data)
      } catch (err) {
        console.error("Məlumatı yükləmək mümkün olmadı:", err)
        setError(`Xəta: ${err.response?.status || 'Bilinməyən'} - Məlumatları yükləmək mümkün olmadı.`)
      } finally {
        setLoading(false)
      }
    }

    fetchAllData()
  }, [])

  const handleDownloadExcel = () => {
    window.open(`http://127.0.0.1:8000/api/summary/export/excel/`, '_blank')
  }

  const handleDownloadPDF = () => {
    window.open(`http://127.0.0.1:8000/api/summary/export/pdf/`, '_blank')
  }

  const handleReset = () => {
    window.localStorage.removeItem(ONBOARDING_ACTIVE_KEY)
    navigate('/')
  }

  if (loading) {
    return (
      <div className="step-content summary-content text-center py-5" style={{ textAlign: 'center', padding: '4rem' }}>
        <RefreshCw className="animate-spin mx-auto mb-3" size={36} />
        <p>AI maliyyə planınızı hazırlayır və təhlil edir...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="step-content summary-content text-center py-5 text-danger" style={{ textAlign: 'center', padding: '4rem' }}>
        <p>{error}</p>
        <button type="button" className="btn-restart mt-3" onClick={handleReset}>Yenidən cəhd et</button>
      </div>
    )
  }

  return (
    <StepSummary 
      summaryData={summaryData}
      goalsData={goalsData}
      monthlyTableData={monthlyTableData}
      comparisonData={comparisonData}
      userName={userName}
      onReset={handleReset}
      onDownloadExcel={handleDownloadExcel}
      onDownloadPDF={handleDownloadPDF}
    />
  )
}

export default BudgetPlanResults