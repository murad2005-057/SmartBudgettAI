import React from 'react'
import { LuChevronLeft, LuChevronRight } from 'react-icons/lu'

export function FormNavigation({
  onNext,
  onComplete,
  onPrev,
  showBack = true,
  disableNext = false,
  nextLabel = 'Növbəti'
}) {
  return (
    <div className="form-navigation-container">
      <div className="nav-left">
        {showBack && (
          <button type="button" className="btn-back" onClick={onPrev}>
            <LuChevronLeft size={18} />
            <span>Gəri</span>
          </button>
        )}
      </div>
      <div className="nav-right">
        <button
          type="button"
          className="btn-next"
          onClick={onComplete || onNext}
          disabled={disableNext}
        >
          <span>{nextLabel}</span>
          <LuChevronRight size={18} />
        </button>
      </div>
    </div>
  )
}
