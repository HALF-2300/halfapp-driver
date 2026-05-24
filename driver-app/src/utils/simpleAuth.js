// Simplified, bulletproof authentication for testing
export class SimpleAuth {
  constructor() {
    this.initializeDatabase()
  }

  initializeDatabase() {
    // Only initialize if not already present to preserve registrations
    try {
      const existing = localStorage.getItem('simple_drivers')
      if (existing) {
        const parsed = JSON.parse(existing)
        if (parsed && typeof parsed === 'object') {
          return parsed
        }
      }
    } catch (_) {
      // fall through to initialize fresh
    }

    // Seed with test drivers on first run
    const drivers = {
      "driver1@example.com": {
        id: 1,
        email: "driver1@example.com",
        name: "John Driver",
        role: "driver",
        password: "driver123"
      },
      "driver2@example.com": {
        id: 2,
        email: "driver2@example.com", 
        name: "Jane Driver",
        role: "driver",
        password: "driver456"
      },
      "test@driver.com": {
        id: 3,
        email: "test@driver.com",
        name: "Test Driver", 
        role: "driver",
        password: "password123"
      }
    }

    localStorage.setItem('simple_drivers', JSON.stringify(drivers))
    console.log('✅ Simple auth database initialized')
    return drivers
  }

  getDrivers() {
    try {
      const stored = localStorage.getItem('simple_drivers')
      return stored ? JSON.parse(stored) : this.initializeDatabase()
    } catch (e) {
      console.log('Database error, reinitializing...')
      return this.initializeDatabase()
    }
  }

  async login(email, password) {
    console.log('🔐 SimpleAuth login attempt:', { email, password: password ? '***' : 'empty' })
    
    const drivers = this.getDrivers()
    console.log('📊 Available drivers:', Object.keys(drivers))
    
    const driver = drivers[email]
    if (!driver) {
      console.log('❌ Driver not found')
      throw new Error('No driver account found with this email address. Please check your email or create a new account.')
    }

    console.log('👤 Found driver:', { ...driver, password: '***' })

    if (driver.password !== password) {
      console.log('❌ Password mismatch')
      throw new Error('Incorrect password. Please check your password and try again.')
    }

    // Success
    const token = `simple_token_${driver.id}_${Date.now()}`
    localStorage.setItem('driver_token', token)
    localStorage.setItem('driver_role', 'driver')
    
    console.log('✅ Login successful')
    
    return {
      access_token: token,
      role: 'driver',
      user: {
        id: driver.id,
        email: driver.email,
        name: driver.name,
        role: 'driver'
      }
    }
  }

  async register(userData) {
    console.log('📝 SimpleAuth register attempt:', { ...userData, password: '***' })
    
    const drivers = this.getDrivers()
    
    if (drivers[userData.email]) {
      throw new Error('A driver account with this email already exists. Please sign in instead or use a different email address.')
    }

    const newDriver = {
      id: Date.now(),
      email: userData.email,
      name: userData.name,
      role: 'driver',
      password: userData.password
    }

    drivers[userData.email] = newDriver
    localStorage.setItem('simple_drivers', JSON.stringify(drivers))
    
    // Set up authentication session
    const token = `simple_token_${newDriver.id}_${Date.now()}`
    localStorage.setItem('driver_token', token)
    localStorage.setItem('driver_role', 'driver')
    
    console.log('✅ Registration successful')
    
    return {
      access_token: token,
      role: 'driver',
      user: {
        id: newDriver.id,
        email: newDriver.email,
        name: newDriver.name,
        role: 'driver'
      }
    }
  }

  logout() {
    localStorage.removeItem('driver_token')
    localStorage.removeItem('driver_role')
    console.log('✅ Logout successful')
  }

  isAuthenticated() {
    return !!localStorage.getItem('driver_token')
  }

  async getProfile() {
    const token = localStorage.getItem('driver_token')
    if (!token) throw new Error('Not authenticated')
    
    // Extract user ID from token
    const userId = token.split('_')[2]
    const drivers = this.getDrivers()
    const driver = Object.values(drivers).find(d => d.id.toString() === userId)
    
    if (!driver) throw new Error('Profile not found')
    
    return {
      id: driver.id,
      email: driver.email,
      name: driver.name,
      role: 'driver'
    }
  }
}

// Create global instance
export const simpleAuth = new SimpleAuth()

// Make it available for testing
if (typeof window !== 'undefined') {
  window.simpleAuth = simpleAuth
}

export default simpleAuth