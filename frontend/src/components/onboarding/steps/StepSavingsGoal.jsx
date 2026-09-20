import React from 'react'
import { GoalOptionCard } from './GoalOptionCard'
import { GoalDetailForm } from './GoalDetailForm'

const GOALS = [
  { id: 'travel', icon: '✈️', label: 'Səyahət etmək' },
  { id: 'home', icon: '🏢', label: 'Ev almaq' },
  { id: 'car', icon: '🚗', label: 'Avtomobil almaq' },
  { id: 'education', icon: '🎓', label: 'Təhsil üçün yığım' },
  { id: 'wedding', icon: '👰', label: 'Toy üçün yığım' },
  { id: 'business', icon: '👨‍💻', label: 'Biznes qurmaq' },
  { id: 'emergency', icon: '💵', label: 'Fövqəladə hallar üçün ehtiyyat fondu' },
  { id: 'other', icon: '🎯', label: 'Digər' }
]

export function StepSavingsGoal({ goals, onToggleGoal, onPriorityChange, onAmountChange, onAmountClear, onCustomNameChange }) {
  return (
    <div className="step-content">
      <h4 className="question-title">Yığım məqsədiniz nədir?</h4>
      <div className="savings-goals-grid">
        {GOALS.map((goal) => (
          <GoalOptionCard
            key={goal.id}
            icon={goal.icon}
            label={goal.label}
            selected={goals.some((selectedGoal) => selectedGoal.id === goal.id)}
            onClick={() => onToggleGoal(goal)}
          />
        ))}
      </div>

      <div className="goal-details-list">
        {goals.map((goal) => (
          <GoalDetailForm
            key={goal.id}
            goal={goal}
            onPriorityChange={(priority) => onPriorityChange(goal.id, priority)}
            onAmountChange={(amount) => onAmountChange(goal.id, amount)}
            onAmountClear={() => onAmountClear(goal.id)}
            onCustomNameChange={(name) => onCustomNameChange(goal.id, name)}
          />
        ))}
      </div>
    </div>
  )
}
