import React from 'react'
import {
  Car,
  GraduationCap,
  Home,
  Plane,
  ShieldAlert,
  Target
} from 'lucide-react'

export const getGoalIcon = (goal) => {
  const title = (goal?.goal_name || goal?.custom_name || goal?.goal_id || '').toLowerCase()
  if (title.includes('home') || title.includes('ev') || title.includes('mənzil')) return Home
  if (title.includes('car') || title.includes('avtomobil') || title.includes('maşın')) return Car
  if (title.includes('travel') || title.includes('səyahət') || title.includes('tətil')) return Plane
  if (title.includes('education') || title.includes('təhsil')) return GraduationCap
  if (title.includes('emergency') || title.includes('təcili')) return ShieldAlert
  if (title.includes('business') || title.includes('biznes')) return Target
  return Target
}

export function GoalCard({ goal }) {
  const amount = Number(goal?.current_amount) || 0
  const target = Number(goal?.target_amount || goal?.amount) || 0
  const monthlySaving = Number(goal?.recommended_monthly_saving) || 0

  const progress = goal?.progress_percentage !== undefined && goal?.progress_percentage !== null
    ? Math.round(Number(goal.progress_percentage))
    : (target > 0 ? Math.min(100, Math.round((amount / target) * 100)) : 0)

  const IconComponent = getGoalIcon(goal)
  const priority = goal?.priority || 'Orta'
  const goalTitle = goal?.goal_name || goal?.custom_name || goal?.goal_id || 'Yığım məqsədi'

  const formattedAmount = `${amount.toLocaleString('en-US')}/${target.toLocaleString('en-US')} AZN`
  const formattedMonthly = `${monthlySaving.toLocaleString('en-US')} AZN/ay`

  return (
    <div className="goal-card-container">
      {/* Top Row: Icon inside light-orange circular background on the left, Goal Name in bold font */}
      <div className="goal-card-top-row">
        <div className="goal-card-icon-wrapper">
          <IconComponent size={20} strokeWidth={2.2} />
        </div>
        <h4 className="goal-card-title">{goalTitle}</h4>
      </div>

      {/* Middle Row 1: Left: current vs target amount, Right: progress percentage in orange bold */}
      <div className="goal-card-middle-row">
        <span className="goal-card-amounts">{formattedAmount}</span>
        <span className="goal-card-percentage">{progress}%</span>
      </div>

      {/* Progress Bar: Light cream/orange background track, bright orange active track */}
      <div className="goal-card-progress-bar">
        <div
          className="goal-card-progress-fill"
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>

      {/* Bottom Row: Left: recommended monthly allocation, Right: priority status with bullet */}
      <div className="goal-card-bottom-row">
        <span className="goal-card-monthly">{formattedMonthly}</span>
        <div className="goal-card-priority">
          <span className="goal-card-bullet">•</span>
          <span className="goal-card-priority-label">Prioritet:</span>
          <span className="goal-card-priority-value">{priority}</span>
        </div>
      </div>
    </div>
  )
}

export default GoalCard
