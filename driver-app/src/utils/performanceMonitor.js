/**
 * Performance monitoring utility for React optimizations
 * Demonstrates the effectiveness of memo, useCallback, useMemo patterns
 */

class PerformanceMonitor {
  constructor() {
    this.renderCounts = new Map()
    this.renderTimes = new Map()
    this.memoryUsage = []
  }

  // Track component renders
  trackRender(componentName) {
    const count = this.renderCounts.get(componentName) || 0
    this.renderCounts.set(componentName, count + 1)
    
    const startTime = performance.now()
    this.renderTimes.set(componentName, startTime)
    
    if (process.env.NODE_ENV === 'development') {
      console.log(`🔄 ${componentName} rendered (${count + 1} times)`)
    }
  }

  // Track render completion
  trackRenderComplete(componentName) {
    const startTime = this.renderTimes.get(componentName)
    if (startTime) {
      const endTime = performance.now()
      const duration = endTime - startTime
      
      if (process.env.NODE_ENV === 'development' && duration > 16) {
        console.warn(`⚠️  ${componentName} render took ${duration.toFixed(2)}ms (>16ms threshold)`)
      }
    }
  }

  // Track memory usage
  trackMemory() {
    if (performance.memory) {
      this.memoryUsage.push({
        timestamp: Date.now(),
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit
      })
      
      // Keep only last 100 measurements
      if (this.memoryUsage.length > 100) {
        this.memoryUsage.shift()
      }
    }
  }

  // Get performance report
  getReport() {
    return {
      renderCounts: Object.fromEntries(this.renderCounts),
      memoryUsage: this.memoryUsage.slice(-10), // Last 10 measurements
      optimizations: {
        memo: 'Prevents unnecessary re-renders',
        useCallback: 'Memoizes event handlers',
        useMemo: 'Memoizes expensive calculations',
        lazyLoading: 'Reduces initial bundle size'
      }
    }
  }

  // Log optimization tips
  logOptimizationTips() {
    if (process.env.NODE_ENV === 'development') {
      console.group('🚀 React Performance Optimizations Applied:')
      console.log('✅ React.memo - Prevents unnecessary component re-renders')
      console.log('✅ useCallback - Memoizes event handlers to prevent prop changes')
      console.log('✅ useMemo - Memoizes expensive calculations')
      console.log('✅ Lazy Loading - Reduces initial bundle size with code splitting')
      console.log('✅ Suspense - Provides loading states for async components')
      console.log('✅ Hardware Acceleration - CSS transforms with translateZ(0)')
      console.groupEnd()
    }
  }
}

// Create singleton instance
const performanceMonitor = new PerformanceMonitor()

export default performanceMonitor