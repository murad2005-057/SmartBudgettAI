import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App.jsx";
import { BudgetPlanResults } from "./components/onboarding/BudgetPlanResults.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        {/* Onboarding / Main App */}
        <Route path="/" element={<App />} />
        
        {/* Final Results Page */}
        <Route path="/summary/:sessionId" element={<BudgetPlanResults />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)