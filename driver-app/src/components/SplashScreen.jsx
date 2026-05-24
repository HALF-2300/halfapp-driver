import React, { useEffect } from 'react'

export default function SplashScreen({ onComplete }) {
  useEffect(() => {
    // Auto-transition after 2 seconds
    const timer = setTimeout(() => {
      if (onComplete) {
        onComplete()
      }
    }, 2000)

    return () => clearTimeout(timer)
  }, [onComplete])

  return (
    <div 
      className="min-h-screen flex flex-col justify-center items-center relative overflow-hidden"
      style={{
        background: "linear-gradient(to bottom right, #3b82f6 0%, #2563eb 100%)"
      }}
    >
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-20 left-10 w-32 h-32 bg-white/20 rounded-full blur-3xl"></div>
        <div className="absolute bottom-40 right-10 w-48 h-48 bg-white/10 rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-white/5 rounded-full blur-3xl"></div>
      </div>

      {/* Main Content */}
      <div className="text-center z-10">
        {/* Car Icon */}
        <div className="mb-8">
          <div className="w-24 h-24 mx-auto mb-6 bg-white/20 rounded-3xl flex items-center justify-center backdrop-blur-sm border border-white/30">
            <svg
              width="48"
              height="48"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="text-white"
            >
              <path
                d="M6.3375 5.50313L5.11406 9H18.8859L17.6625 5.50313C17.4516 4.90313 16.8844 4.5 16.2469 4.5H7.75312C7.11562 4.5 6.54844 4.90313 6.3375 5.50313ZM1.85625 9.225L3.50625 4.51406C4.13906 2.70938 5.84062 1.5 7.75312 1.5H16.2469C18.1594 1.5 19.8609 2.70938 20.4938 4.51406L22.1437 9.225C23.2312 9.675 24 10.7484 24 12V18.75V21C24 21.8297 23.3297 22.5 22.5 22.5H21C20.1703 22.5 19.5 21.8297 19.5 21V18.75H4.5V21C4.5 21.8297 3.82969 22.5 3 22.5H1.5C0.670312 22.5 0 21.8297 0 21V18.75V12C0 10.7484 0.76875 9.675 1.85625 9.225ZM6 13.5C6 13.1022 5.84196 12.7206 5.56066 12.4393C5.27936 12.158 4.89782 12 4.5 12C4.10218 12 3.72064 12.158 3.43934 12.4393C3.15804 12.7206 3 13.1022 3 13.5C3 13.8978 3.15804 14.2794 3.43934 14.5607C3.72064 14.842 4.10218 15 4.5 15C4.89782 15 5.27936 14.842 5.56066 14.5607C5.84196 14.2794 6 13.8978 6 13.5ZM19.5 15C19.8978 15 20.2794 14.842 20.5607 14.5607C20.842 14.2794 21 13.8978 21 13.5C21 13.1022 20.842 12.7206 20.5607 12.4393C20.2794 12.158 19.8978 12 19.5 12C19.1022 12 18.7206 12.158 18.4393 12.4393C18.158 12.7206 18 13.1022 18 13.5C18 13.8978 18.158 14.2794 18.4393 14.5607C18.7206 14.842 19.1022 15 19.5 15Z"
                fill="currentColor"
              />
            </svg>
          </div>
        </div>

        {/* App Name */}
        <h1 className="text-4xl font-bold text-white mb-2">
          HalfApp
        </h1>
        <p className="text-xl text-blue-100 font-medium mb-8">
          Driver
        </p>

        {/* Loading Animation */}
        <div className="flex justify-center">
          <div className="w-8 h-8 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
        </div>
      </div>

      {/* Bottom Branding */}
      <div className="absolute bottom-8 left-0 right-0 text-center">
        <p className="text-blue-100 text-sm">
          Your journey starts here
        </p>
      </div>
    </div>
  )
}