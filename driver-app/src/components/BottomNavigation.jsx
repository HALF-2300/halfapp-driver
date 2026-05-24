import React from 'react'
import { useLocation, NavLink } from 'react-router-dom'
import { useDriverPreferences } from '../context/DriverPreferencesContext.jsx'

export default function BottomNavigation({ embedded = false }) {
  const location = useLocation()
  const { unreadNotifications } = useDriverPreferences()

  const tabs = [
    {
      id: 'home',
      label: 'Home',
      path: '/driver',
      icon: (
        <svg width="23" height="20" viewBox="0 0 23 20" fill="none" xmlns="http://www.w3.org/2000/svg" className="h-5 w-6">
          <path
            d="M22.4922 9.98047C22.4922 10.6836 21.9062 11.2344 21.2422 11.2344H19.9922L20.0195 17.4922C20.0195 17.5977 20.0117 17.7031 20 17.8086V18.4375C20 19.3008 19.3008 20 18.4375 20H17.8125C17.7695 20 17.7266 20 17.6836 19.9961C17.6289 20 17.5742 20 17.5195 20H16.25H15.3125C14.4492 20 13.75 19.3008 13.75 18.4375V17.5V15C13.75 14.3086 13.1914 13.75 12.5 13.75H10C9.30859 13.75 8.75 14.3086 8.75 15V17.5V18.4375C8.75 19.3008 8.05078 20 7.1875 20H6.25H5.00391C4.94531 20 4.88672 19.9961 4.82812 19.9922C4.78125 19.9961 4.73438 20 4.6875 20H4.0625C3.19922 20 2.5 19.3008 2.5 18.4375V14.0625C2.5 14.0273 2.5 13.9883 2.50391 13.9531V11.2344H1.25C0.546875 11.2344 0 10.6875 0 9.98047C0 9.62891 0.117188 9.31641 0.390625 9.04297L10.4062 0.3125C10.6797 0.0390625 10.9922 0 11.2656 0C11.5391 0 11.8516 0.078125 12.0859 0.273438L22.0625 9.04297C22.375 9.31641 22.5312 9.62891 22.4922 9.98047Z"
            fill="currentColor"
          />
        </svg>
      ),
    },
    {
      id: 'earnings',
      label: 'Earnings',
      path: '/driver/earnings',
      icon: (
        <svg width="13" height="20" viewBox="0 0 13 20" fill="none" className="h-5 w-3">
          <path
            d="M6.25006 0C6.94146 0 7.50006 0.558594 7.50006 1.25V2.64453C7.56256 2.65234 7.62115 2.66016 7.68365 2.67188L9.60162 3.02344C10.2813 3.14844 10.7305 3.80078 10.6055 4.47656C10.4805 5.15234 9.82818 5.60547 9.1524 5.48047L7.29693 5.14063C6.07428 4.96094 4.99615 5.08203 4.23834 5.38281C3.48053 5.68359 3.17584 6.09766 3.10553 6.48047C3.0274 6.89844 3.08599 7.13281 3.1524 7.27734C3.22271 7.42969 3.36724 7.60156 3.6524 7.79297C4.28912 8.21094 5.26568 8.48438 6.53131 8.82031L6.64459 8.85156C7.76178 9.14844 9.12896 9.50781 10.1446 10.1719C10.6993 10.5352 11.2227 11.0273 11.5469 11.7148C11.879 12.4141 11.9493 13.1953 11.7969 14.0273C11.5274 15.5117 10.504 16.5039 9.23443 17.0234C8.69928 17.2422 8.11724 17.3828 7.50006 17.4531V18.75C7.50006 19.4414 6.94146 20 6.25006 20C5.55865 20 5.00006 19.4414 5.00006 18.75V17.3867C4.98443 17.3828 4.9649 17.3828 4.94927 17.3789H4.94146C3.98834 17.2305 2.42193 16.8203 1.36724 16.3516C0.738338 16.0703 0.453181 15.332 0.734431 14.7031C1.01568 14.0742 1.75396 13.7891 2.38287 14.0703C3.19928 14.4336 4.54302 14.793 5.32037 14.9141C6.56646 15.0977 7.59381 14.9922 8.28912 14.707C8.94928 14.4375 9.25006 14.0469 9.33599 13.5781C9.41021 13.1641 9.35162 12.9258 9.28521 12.7813C9.21099 12.625 9.06646 12.4531 8.7774 12.2617C8.13678 11.8437 7.15631 11.5703 5.88678 11.2344L5.7774 11.207C4.66412 10.9102 3.29693 10.5469 2.28131 9.88281C1.72662 9.51953 1.20709 9.02344 0.882869 8.33594C0.554744 7.63672 0.488338 6.85547 0.644588 6.02344C0.925838 4.53125 2.04303 3.5625 3.31256 3.05859C3.83209 2.85156 4.4024 2.71094 5.00006 2.62891V1.25C5.00006 0.558594 5.55865 0 6.25006 0Z"
            fill="currentColor"
          />
        </svg>
      ),
    },
    {
      id: 'trips',
      label: 'Trips',
      path: '/driver/trips',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="h-5 w-5">
          <path
            d="M3 4.5C3 3.67 3.67 3 4.5 3h11A1.5 1.5 0 0 1 17 4.5v11A1.5 1.5 0 0 1 15.5 17h-11A1.5 1.5 0 0 1 3 15.5v-11Zm2.5.5v2h9V5h-9Zm0 4v2h9V9h-9Zm0 4v2h6v-2H5.5Z"
            fill="currentColor"
          />
        </svg>
      ),
    },
    {
      id: 'notifications',
      label: 'Alerts',
      path: '/driver/notifications',
      badge: unreadNotifications,
      icon: (
        <svg width="18" height="20" viewBox="0 0 20 20" fill="none" className="h-5 w-5">
          <path
            d="M10 2a5 5 0 00-5 5v2.5c0 .7-.3 1.4-.8 1.9L3 13.5h14l-1.2-2.1c-.5-.5-.8-1.2-.8-1.9V7a5 5 0 00-5-5zm0 16a2.5 2.5 0 01-2.45-2h4.9A2.5 2.5 0 0110 18z"
            fill="currentColor"
          />
        </svg>
      ),
    },
    {
      id: 'account',
      label: 'Account',
      path: '/driver/settings',
      icon: (
        <svg width="18" height="20" viewBox="0 0 18 20" fill="none" className="h-5 w-4">
          <path
            d="M8.75 10C10.0761 10 11.3479 9.47322 12.2855 8.53553C13.2232 7.59785 13.75 6.32608 13.75 5C13.75 3.67392 13.2232 2.40215 12.2855 1.46447C11.3479 0.526784 10.0761 0 8.75 0C7.42392 0 6.15215 0.526784 5.21447 1.46447C4.27678 2.40215 3.75 3.67392 3.75 5C3.75 6.32608 4.27678 7.59785 5.21447 8.53553C6.15215 9.47322 7.42392 10 8.75 10ZM6.96484 11.875C3.11719 11.875 0 14.9922 0 18.8398C0 19.4805 0.519531 20 1.16016 20H16.3398C16.9805 20 17.5 19.4805 17.5 18.8398C17.5 14.9922 14.3828 11.875 10.5352 11.875H6.96484Z"
            fill="currentColor"
          />
        </svg>
      ),
    },
  ]

  const isActiveTab = (path) => {
    if (path === '/driver') {
      return location.pathname === '/driver' || location.pathname === '/driver/cockpit' || location.pathname === '/'
    }
    return location.pathname.startsWith(path)
  }

  const positionClass = embedded
    ? 'bottom-nav-dock pointer-events-auto'
    : 'fixed bottom-4 left-1/2 z-30 w-[min(680px,calc(100vw-24px))] -translate-x-1/2 rounded-[24px] border border-white/10 bg-[rgba(7,12,26,0.82)] shadow-[0_18px_60px_rgba(0,0,0,0.36)] backdrop-blur-[20px]'

  return (
    <nav
      className={positionClass}
      data-testid="bottom-nav-dock"
      aria-label="Main navigation"
    >
      <div className="flex h-full items-stretch px-1">
        {tabs.map((tab) => {
          const isActive = isActiveTab(tab.path)
          return (
            <NavLink
              key={tab.id}
              to={tab.path}
              aria-label={tab.label}
              data-testid={`tab-${tab.id}`}
              className={`cockpit-pressable flex flex-1 flex-col items-center justify-center gap-0.5 rounded-[18px] py-2 text-[10px] font-medium transition-colors ${
                isActive ? 'text-[#60A5FA]' : 'text-[#64748B]'
              }`}
            >
              {React.cloneElement(tab.icon, {
                className: `${tab.icon.props.className} ${isActive ? 'text-[#60A5FA]' : 'text-[#64748B]'}`,
              })}
              <span className="relative inline-flex items-center gap-1">
                {tab.label}
                {tab.badge > 0 ? (
                  <span
                    className="min-w-[16px] rounded-full bg-[#ef4444] px-1 text-[9px] font-bold text-white"
                    data-testid={`tab-${tab.id}-badge`}
                  >
                    {tab.badge > 99 ? '99+' : tab.badge}
                  </span>
                ) : null}
              </span>
            </NavLink>
          )
        })}
      </div>
    </nav>
  )
}
