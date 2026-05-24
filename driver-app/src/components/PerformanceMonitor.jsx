import React, { useEffect, useState } from 'react'

const PerformanceMonitor = () => {
  const [metrics, setMetrics] = useState({
    loadTime: 0,
    renderTime: 0,
    memoryUsage: 0,
    lastUpdate: null
  })

  useEffect(() => {
    let performanceObserver
    let startTime = performance.now()

    const updateMetrics = () => {
      const navigation = performance.getEntriesByType('navigation')[0]
      const memory = performance.memory || {}
      
      const newMetrics = {
        loadTime: navigation ? Math.round(navigation.loadEventEnd - navigation.navigationStart) : 0,
        renderTime: Math.round(performance.now() - startTime),
        memoryUsage: memory.usedJSHeapSize ? Math.round(memory.usedJSHeapSize / 1048576) : 0,
        lastUpdate: new Date().toLocaleTimeString()
      }

      setMetrics(newMetrics)

      // Log performance for debugging
      if (process.env.NODE_ENV === 'development') {
        console.log('📊 Performance Metrics:', newMetrics)
      }
    }

    // Initial measurement
    setTimeout(updateMetrics, 1000)

    // Monitor Long Tasks API if available
    if (window.PerformanceObserver && window.PerformanceLongTaskTiming) {
      performanceObserver = new PerformanceObserver((list) => {
        list.getEntries().forEach((entry) => {
          console.warn('⚠️ Long Task detected:', {
            name: entry.name,
            duration: Math.round(entry.duration),
            startTime: Math.round(entry.startTime)
          })
        })
      })

      try {
        performanceObserver.observe({ entryTypes: ['longtask'] })
      } catch (e) {
        console.log('Long Task API not supported')
      }
    }

    // Update metrics periodically
    const interval = setInterval(updateMetrics, 5000)

    return () => {
      clearInterval(interval)
      if (performanceObserver) {
        performanceObserver.disconnect()
      }
    }
  }, [])

  const getLoadTimeStatus = (loadTime) => {
    if (loadTime < 1000) return { color: 'text-green-600', label: 'Excellent' }
    if (loadTime < 2000) return { color: 'text-yellow-600', label: 'Good' }
    return { color: 'text-red-600', label: 'Slow' }
  }

  const getMemoryStatus = (memory) => {
    if (memory < 50) return { color: 'text-green-600', label: 'Low' }
    if (memory < 100) return { color: 'text-yellow-600', label: 'Moderate' }
    return { color: 'text-red-600', label: 'High' }
  }

  return (
    <div className="fixed top-4 right-4 bg-white border border-gray-300 rounded-lg shadow-lg p-3 text-xs max-w-xs">
      <div className="font-bold text-gray-800 mb-2 flex items-center">
        📊 Performance
        <button 
          onClick={() => window.location.reload()} 
          className="ml-2 text-blue-500 hover:text-blue-700"
          title="Refresh"
        >
          🔄
        </button>
      </div>
      
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <span className="text-gray-600">Load Time:</span>
          <span className={getLoadTimeStatus(metrics.loadTime).color}>
            {metrics.loadTime}ms {getLoadTimeStatus(metrics.loadTime).label}
          </span>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="text-gray-600">Render Time:</span>
          <span className="text-gray-800">{metrics.renderTime}ms</span>
        </div>
        
        {metrics.memoryUsage > 0 && (
          <div className="flex justify-between items-center">
            <span className="text-gray-600">Memory:</span>
            <span className={getMemoryStatus(metrics.memoryUsage).color}>
              {metrics.memoryUsage}MB {getMemoryStatus(metrics.memoryUsage).label}
            </span>
          </div>
        )}
        
        <div className="text-gray-500 text-xs pt-2 border-t border-gray-200">
          Updated: {metrics.lastUpdate || 'Loading...'}
        </div>
      </div>

      {/* Performance Tips */}
      <div className="mt-2 pt-2 border-t border-gray-200">
        <div className="text-gray-600 text-xs">
          Tips:
        </div>
        <ul className="text-xs text-gray-500 mt-1">
          <li>• Keep load time under 2s</li>
          <li>• Memory under 100MB</li>
          <li>• Watch for long tasks</li>
        </ul>
      </div>
    </div>
  )
}

export default PerformanceMonitor