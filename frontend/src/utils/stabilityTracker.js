// Stability Tracking System for HalfApp
// Monitors application health, errors, performance, and user interactions

class StabilityTracker {
  constructor() {
    this.events = []
    this.errors = []
    this.apiMetrics = {}
    this.startTime = Date.now()
    this.sessionId = this.generateSessionId()
    
    // Initialize tracking
    this.initErrorTracking()
    this.initPerformanceTracking()
    
    console.log(`[Stability Tracker] Initialized for session ${this.sessionId}`)
  }

  generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  initErrorTracking() {
    // Track JavaScript errors
    window.addEventListener('error', (event) => {
      this.logError({
        type: 'javascript_error',
        message: event.error?.message || event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        stack: event.error?.stack
      })
    })

    // Track unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.logError({
        type: 'unhandled_rejection',
        message: event.reason?.message || event.reason,
        stack: event.reason?.stack
      })
    })
  }

  initPerformanceTracking() {
    // Track navigation timing if available
    if (window.performance && window.performance.timing) {
      window.addEventListener('load', () => {
        const timing = window.performance.timing
        this.logEvent('page_performance', {
          loadTime: timing.loadEventEnd - timing.navigationStart,
          domReady: timing.domContentLoadedEventEnd - timing.navigationStart,
          resourcesLoaded: timing.loadEventEnd - timing.domContentLoadedEventEnd
        })
      })
    }
  }

  logEvent(eventType, data = {}) {
    const event = {
      sessionId: this.sessionId,
      timestamp: Date.now(),
      type: eventType,
      data: data,
      userAgent: navigator.userAgent,
      url: window.location.href
    }
    
    this.events.push(event)
    
    // Console log for development
    if (process.env.NODE_ENV === 'development') {
      console.log(`[Stability] ${eventType}:`, data)
    }
    
    // Keep only last 100 events to prevent memory issues
    if (this.events.length > 100) {
      this.events = this.events.slice(-100)
    }
  }

  logError(error) {
    const errorEvent = {
      sessionId: this.sessionId,
      timestamp: Date.now(),
      ...error,
      url: window.location.href,
      userAgent: navigator.userAgent
    }
    
    this.errors.push(errorEvent)
    console.error('[Stability] Error logged:', errorEvent)
    
    // Keep only last 50 errors
    if (this.errors.length > 50) {
      this.errors = this.errors.slice(-50)
    }
  }

  trackComponentMount(componentName) {
    this.logEvent('component_mount', { componentName })
  }

  trackComponentUnmount(componentName) {
    this.logEvent('component_unmount', { componentName })
  }

  trackUserAction(action, details = {}) {
    this.logEvent('user_action', { action, ...details })
  }

  trackApiCall(endpoint, method, startTime) {
    const duration = Date.now() - startTime
    
    if (!this.apiMetrics[endpoint]) {
      this.apiMetrics[endpoint] = {
        calls: 0,
        totalDuration: 0,
        errors: 0,
        methods: {}
      }
    }
    
    this.apiMetrics[endpoint].calls++
    this.apiMetrics[endpoint].totalDuration += duration
    
    if (!this.apiMetrics[endpoint].methods[method]) {
      this.apiMetrics[endpoint].methods[method] = 0
    }
    this.apiMetrics[endpoint].methods[method]++
    
    this.logEvent('api_call', {
      endpoint,
      method,
      duration,
      averageDuration: this.apiMetrics[endpoint].totalDuration / this.apiMetrics[endpoint].calls
    })
  }

  trackApiError(endpoint, method, error) {
    if (!this.apiMetrics[endpoint]) {
      this.apiMetrics[endpoint] = { errors: 0 }
    }
    this.apiMetrics[endpoint].errors++
    
    this.logError({
      type: 'api_error',
      endpoint,
      method,
      message: error.message || error,
      stack: error.stack
    })
  }

  getSessionSummary() {
    const sessionDuration = Date.now() - this.startTime
    
    return {
      sessionId: this.sessionId,
      duration: sessionDuration,
      totalEvents: this.events.length,
      totalErrors: this.errors.length,
      apiMetrics: this.apiMetrics,
      uptime: this.formatDuration(sessionDuration),
      errorRate: this.errors.length / Math.max(this.events.length, 1),
      recentErrors: this.errors.slice(-5),
      recentEvents: this.events.slice(-10)
    }
  }

  formatDuration(ms) {
    const seconds = Math.floor(ms / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    
    if (hours > 0) return `${hours}h ${minutes % 60}m ${seconds % 60}s`
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`
    return `${seconds}s`
  }

  // Export data for external monitoring systems
  exportData() {
    return {
      session: this.getSessionSummary(),
      events: this.events,
      errors: this.errors,
      apiMetrics: this.apiMetrics,
      timestamp: Date.now()
    }
  }

  // Check application health
  getHealthStatus() {
    const summary = this.getSessionSummary()
    const isHealthy = summary.errorRate < 0.1 && this.errors.length < 10
    
    return {
      status: isHealthy ? 'healthy' : 'degraded',
      errorRate: summary.errorRate,
      totalErrors: this.errors.length,
      uptime: summary.uptime,
      lastError: this.errors.length > 0 ? this.errors[this.errors.length - 1] : null
    }
  }

  // Method to manually log application modifications
  trackModification(type, description, component = null) {
    this.logEvent('modification', {
      modificationType: type,
      description,
      component,
      timestamp: new Date().toISOString()
    })
  }
}

// Create singleton instance
const stabilityTracker = new StabilityTracker()

export default stabilityTracker

// Export helper functions for React components
export const useStabilityTracking = (componentName) => {
  const trackMount = () => stabilityTracker.trackComponentMount(componentName)
  const trackUnmount = () => stabilityTracker.trackComponentUnmount(componentName)
  const trackAction = (action, details) => stabilityTracker.trackUserAction(action, details)
  
  return { trackMount, trackUnmount, trackAction }
}

export const trackApiCall = async (apiCall, endpoint, method = 'GET') => {
  const startTime = Date.now()
  try {
    const result = await apiCall()
    stabilityTracker.trackApiCall(endpoint, method, startTime)
    return result
  } catch (error) {
    stabilityTracker.trackApiError(endpoint, method, error)
    throw error
  }
}