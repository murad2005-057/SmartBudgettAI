import React from 'react'

export function GoalOptionCard({ icon, label, selected, onClick }) {
  return (
    <button
      type="button"
      className={`savings-goal-card${selected ? ' is-selected' : ''}`}
      onClick={onClick}
      aria-pressed={selected}
    >
      <span className="savings-goal-icon" aria-hidden="true">{icon}</span>
      <span>{label}</span>
    </button>
  )
}
