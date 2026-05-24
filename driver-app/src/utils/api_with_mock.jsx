// API Configuration with Mock Mode for Development
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const IS_PRODUCTION_BUILD = import.meta.env.PROD
const USE_MOCK_MODE = !IS_PRODUCTION_BUILD && (import.meta.env.VITE_USE_MOCK ?? 'true') === 'true'

class DriverAPI {
  constructor() {
    this.baseUrl = API_BASE
    this.token = localStorage.getItem('driver_token')
    this.mockMode = USE_MOCK_MODE
  }

  // Mock data for development
  getMockData() {
    return {
      users: {
        "driver1@example.com": {
          id: 1,
          email: "driver1@example.com",
          name: "John Driver",
          role: "driver",
          phone: "+1234567890"
        },
        "driver2@example.com": {
          id: 2,
          email: "driver2@example.com", 
          name: "Jane Driver",
          role: "driver",
          phone: "+0987654321"
        }
      },
      rides: [
        {
          id: 1,
          pickup_location: "Downtown Station",
          destination: "Airport",
          passenger_name: "Alice Johnson",
          status: "available",
          fare: 25.50,
          distance_km: 12.5
        },
        {
          id: 2,
          pickup_location: "Mall Plaza", 
          destination: "University",
          passenger_name: "Bob Smith",
          status: "available",
          fare: 18.00,
          distance_km: 8.2
        }
      ],
      myRides: [
        {
          id: 101,
          pickup_location: "Main Street",
          destination: "Shopping Center", 
          passenger_name: "Previous Passenger",
          status: "completed",
          fare: 22.00,
          distance_km: 9.5,
          completed_at: "2025-11-13T10:30:00"
        }
      ],
      stats: {
        total_rides_completed: 15,
        total_distance_km: 245.5,
        rating: 4.7,
        earnings_today: 125.50,
        earnings_week: 780.25
      }
    }
  }

  // Helper method to simulate network delay
  async mockDelay(ms = 500) {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  // Helper method to get headers with auth
  getHeaders() {
    const headers = {
      'Content-Type': 'application/json'
    }
    
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }
    
    return headers
  }

  // Generic API call method with mock support
  async call(endpoint, options = {}) {
    // Mock mode responses
    if (this.mockMode) {
      await this.mockDelay(300) // Simulate network delay
      
      const mockData = this.getMockData()
      
      // Handle different endpoints with mock data
      if (endpoint === '/auth/login' && options.method === 'POST') {
        const body = JSON.parse(options.body)
        const user = mockData.users[body.email]
        
        if (user) {
          return {
            access_token: `mock_token_${user.id}`,
            token: `mock_token_${user.id}`,
            user: user,
            role: 'driver'
          }
        } else {
          throw new Error('Invalid email or password')
        }
      }
      
      if (endpoint === '/auth/register' && options.method === 'POST') {
        return {
          access_token: 'mock_token_new_user',
          token: 'mock_token_new_user',
          role: 'driver',
          message: 'Registration successful'
        }
      }
      
      if (endpoint === '/auth/me') {
        return mockData.users["driver1@example.com"]
      }
      
      if (endpoint === '/drivers/available-rides') {
        return mockData.rides
      }
      
      if (endpoint === '/drivers/my-rides') {
        return mockData.myRides
      }
      
      if (endpoint === '/drivers/statistics') {
        return mockData.stats
      }
      
      if (endpoint.startsWith('/drivers/accept-ride/')) {
        return { message: 'Ride accepted successfully' }
      }
      
      // Default mock response
      return { message: 'Mock response', data: mockData }
    }

    // Real API call (when backend is running)
    const url = `${this.baseUrl}${endpoint}`
    
    const config = {
      headers: this.getHeaders(),
      ...options
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
        throw new Error(error.detail || `HTTP ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error(`API call failed: ${endpoint}`, error)
      
      // Fallback to mock mode if real API fails
      if (!IS_PRODUCTION_BUILD && !this.mockMode) {
        console.warn('API call failed, falling back to mock mode')
        this.mockMode = true
        return this.call(endpoint, options)
      }
      
      throw error
    }
  }

  // Authentication methods
  async login(email, password) {
    try {
      const response = await this.call('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      })
      
      this.token = response.access_token || response.token
      localStorage.setItem('driver_token', this.token)
      localStorage.setItem('driver_role', response.role || 'driver')
      
      return response
    } catch (error) {
      // Re-throw with user-friendly message
      throw new Error('Network error. Please check your connection and try again.')
    }
  }

  async register(email, password, name = '') {
    try {
      const response = await this.call('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, name, role: 'driver' })
      })
      
      this.token = response.access_token || response.token
      localStorage.setItem('driver_token', this.token)
      localStorage.setItem('driver_role', response.role || 'driver')
      
      return response
    } catch (error) {
      throw new Error('Registration failed. Please try again.')
    }
  }

  async getProfile() {
    return await this.call('/auth/me')
  }

  // Driver-specific methods
  async getAvailableRides() {
    return await this.call('/drivers/available-rides')
  }

  async getMyRides() {
    return await this.call('/drivers/my-rides')
  }

  async acceptRide(rideId) {
    return await this.call(`/drivers/accept-ride/${rideId}`, {
      method: 'POST'
    })
  }

  async getStatistics() {
    return await this.call('/drivers/statistics')
  }

  // Utility methods
  logout() {
    this.token = null
    localStorage.removeItem('driver_token')
    localStorage.removeItem('driver_role')
  }

  isAuthenticated() {
    return !!this.token && localStorage.getItem('driver_role') === 'driver'
  }

  // Enable/disable mock mode
  setMockMode(enabled) {
    this.mockMode = !IS_PRODUCTION_BUILD && enabled
    console.log(`Mock mode ${enabled ? 'enabled' : 'disabled'}`)
  }
}

// Create singleton instance
export const driverAPI = new DriverAPI()

// Export for use in components
export default driverAPI