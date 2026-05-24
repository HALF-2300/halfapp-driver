// Test file to verify validation middleware functionality
import dataValidationMiddleware, { ValidationError } from './validation.js'

// Test validation functions
export const runValidationTests = () => {
  console.log('🧪 Running validation middleware tests...')

  // Test email validation
  try {
    const email = dataValidationMiddleware.validateRequest({ email: 'test@example.com', password: 'test123' }, 'login')
    console.log('✅ Valid email test passed:', email.email)
  } catch (e) {
    console.error('❌ Valid email test failed:', e.message)
  }

  // Test invalid email
  try {
    dataValidationMiddleware.validateRequest({ email: 'invalid-email', password: 'test123' }, 'login')
    console.error('❌ Invalid email should have failed')
  } catch (e) {
    console.log('✅ Invalid email correctly rejected:', e.message)
  }

  // Test password validation
  try {
    const weak = dataValidationMiddleware.validateRequest({ 
      email: 'test@example.com', 
      password: '123456', 
      name: 'Test User'
    }, 'registration')
    console.error('❌ Weak password should have failed')
  } catch (e) {
    console.log('✅ Weak password correctly rejected:', e.message)
  }

  // Test valid registration
  try {
    const valid = dataValidationMiddleware.validateRequest({ 
      email: 'driver@example.com', 
      password: 'driver123', 
      name: 'John Driver'
    }, 'registration')
    console.log('✅ Valid registration test passed:', valid.email)
  } catch (e) {
    console.error('❌ Valid registration test failed:', e.message)
  }

  // Test role validation
  try {
    dataValidationMiddleware.validateResponse({ role: 'admin', email: 'admin@test.com' }, 'user')
    console.error('❌ Admin role should have been rejected')
  } catch (e) {
    console.log('✅ Admin role correctly rejected:', e.message)
  }

  // Test driver role validation
  try {
    const driver = dataValidationMiddleware.validateResponse({ role: 'driver', email: 'driver@test.com' }, 'user')
    console.log('✅ Driver role correctly accepted:', driver.email)
  } catch (e) {
    console.error('❌ Driver role test failed:', e.message)
  }

  console.log('🧪 Validation middleware tests completed!')
}

// Export for console testing
if (typeof window !== 'undefined') {
  window.runValidationTests = runValidationTests
}

export default runValidationTests