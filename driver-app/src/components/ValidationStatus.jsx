import React, { useState, useEffect } from 'react'

const ValidationStatus = ({ isVisible, validationType, onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0)
  const [completed, setCompleted] = useState(false)

  const validationSteps = {
    login: [
      { label: 'Validating email format', icon: '📧' },
      { label: 'Checking password requirements', icon: '🔐' },
      { label: 'Verifying driver credentials', icon: '🚗' },
      { label: 'Establishing secure session', icon: '🔒' }
    ],
    registration: [
      { label: 'Validating email format', icon: '📧' },
      { label: 'Checking password strength', icon: '🔐' },
      { label: 'Verifying name requirements', icon: '👤' },
      { label: 'Confirming driver role access', icon: '🚗' },
      { label: 'Creating secure account', icon: '✅' }
    ],
    profile: [
      { label: 'Validating profile data', icon: '👤' },
      { label: 'Checking vehicle information', icon: '🚙' },
      { label: 'Updating secure records', icon: '💾' }
    ]
  }

  const steps = validationSteps[validationType] || validationSteps.login

  useEffect(() => {
    if (!isVisible) {
      setCurrentStep(0)
      setCompleted(false)
      return
    }

    const interval = setInterval(() => {
      setCurrentStep(prev => {
        if (prev >= steps.length - 1) {
          setCompleted(true)
          setTimeout(() => {
            onComplete?.()
          }, 500)
          return prev
        }
        return prev + 1
      })
    }, 800) // Each step takes 800ms

    return () => clearInterval(interval)
  }, [isVisible, steps.length, onComplete])

  if (!isVisible) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-6 mx-4 max-w-sm w-full shadow-xl">
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-blue-600 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            {validationType === 'login' ? 'Signing In' : 
             validationType === 'registration' ? 'Creating Account' : 'Updating Profile'}
          </h3>
          <p className="text-sm text-gray-600">
            Verifying your information securely...
          </p>
        </div>

        <div className="space-y-3">
          {steps.map((step, index) => (
            <div
              key={index}
              className={`flex items-center p-3 rounded-lg transition-all ${
                index <= currentStep
                  ? index === currentStep
                    ? 'bg-blue-50 border border-blue-200'
                    : 'bg-green-50 border border-green-200'
                  : 'bg-gray-50 border border-gray-200'
              }`}
            >
              <div className="flex items-center justify-center w-8 h-8 rounded-full mr-3">
                {index < currentStep ? (
                  <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                ) : index === currentStep ? (
                  <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <span className="text-lg">{step.icon}</span>
                )}
              </div>
              <div className="flex-1">
                <p className={`text-sm font-medium ${
                  index <= currentStep
                    ? index === currentStep
                      ? 'text-blue-900'
                      : 'text-green-900'
                    : 'text-gray-600'
                }`}>
                  {step.label}
                </p>
              </div>
            </div>
          ))}
        </div>

        {completed && (
          <div className="mt-6 text-center">
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            </div>
            <p className="text-sm font-medium text-green-900">Validation Complete!</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default ValidationStatus