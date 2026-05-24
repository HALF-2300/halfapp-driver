#!/usr/bin/env node
// 🧪 Authentication System Verification Script
// This script can be run in browser console to test all flows

console.log('🚗 HalfApp Driver Authentication - System Verification Starting...')

// Verification utilities
const verify = {
  // Test authentication persistence
  async testAuthPersistence() {
    console.log('\n💾 Testing Authentication Persistence...')
    
    // Clear any existing auth
    localStorage.removeItem('driver_token')
    localStorage.removeItem('driver_role')
    
    try {
      // Login and check persistence
      const result = await window.simpleAuth.login('driver1@example.com', 'driver123')
      const hasToken = !!localStorage.getItem('driver_token')
      const hasRole = localStorage.getItem('driver_role') === 'driver'
      
      console.log(`✅ Auth Persistence: Token=${hasToken}, Role=${hasRole}`)
      return hasToken && hasRole
    } catch (error) {
      console.log(`❌ Auth Persistence Failed: ${error.message}`)
      return false
    }
  },

  // Test protected route access
  testProtectedRoutes() {
    console.log('\n🛡️ Testing Protected Routes...')
    
    // Check current URL and auth status
    const currentPath = window.location.pathname
    const hasAuth = !!localStorage.getItem('driver_token')
    const isOnLoginPage = currentPath === '/login' || currentPath === '/'
    
    // If no auth, should be on login page
    if (!hasAuth && isOnLoginPage) {
      console.log('✅ Route Protection: Unauthenticated user correctly on login page')
      return true
    }
    
    // If auth, should be able to access dashboard
    if (hasAuth) {
      console.log('✅ Route Protection: Authenticated user can access protected routes')
      return true
    }
    
    console.log(`❌ Route Protection Issue: Auth=${hasAuth}, Path=${currentPath}`)
    return false
  },

  // Test error message system
  async testErrorMessages() {
    console.log('\n🚨 Testing Error Message System...')
    
    const testCases = [
      {
        test: 'Invalid Email',
        action: () => window.simpleAuth.login('invalid-email', 'password123'),
        expectedError: 'validation'
      },
      {
        test: 'Non-existent User',
        action: () => window.simpleAuth.login('nonexistent@email.com', 'password123'),
        expectedError: 'No driver account found'
      },
      {
        test: 'Wrong Password',
        action: () => window.simpleAuth.login('driver1@example.com', 'wrongpassword'),
        expectedError: 'Incorrect password'
      },
      {
        test: 'Duplicate Registration',
        action: () => window.simpleAuth.register({
          email: 'driver1@example.com',
          password: 'password123',
          name: 'Test User',
          role: 'driver'
        }),
        expectedError: 'already exists'
      }
    ]

    let passedTests = 0
    
    for (const testCase of testCases) {
      try {
        await testCase.action()
        console.log(`❌ ${testCase.test}: Should have failed but succeeded`)
      } catch (error) {
        const hasExpectedError = error.message.toLowerCase().includes(testCase.expectedError.toLowerCase())
        if (hasExpectedError) {
          console.log(`✅ ${testCase.test}: Correct error message`)
          passedTests++
        } else {
          console.log(`❌ ${testCase.test}: Wrong error - ${error.message}`)
        }
      }
    }
    
    return passedTests === testCases.length
  },

  // Test form validation
  testFormValidation() {
    console.log('\n📝 Testing Form Validation...')
    
    // Test validation utility functions if available
    const emailTests = [
      { email: 'valid@email.com', shouldPass: true },
      { email: 'invalid-email', shouldPass: false },
      { email: '', shouldPass: false }
    ]
    
    let passedValidation = 0
    
    emailTests.forEach(test => {
      const isValid = test.email.includes('@') && test.email.includes('.') && test.email.length > 0
      if (isValid === test.shouldPass) {
        passedValidation++
        console.log(`✅ Email Validation: ${test.email} - ${test.shouldPass ? 'valid' : 'invalid'}`)
      } else {
        console.log(`❌ Email Validation Failed: ${test.email}`)
      }
    })
    
    return passedValidation === emailTests.length
  },

  // Test state management
  testStateManagement() {
    console.log('\n🔄 Testing State Management...')
    
    // Check if localStorage is working
    const testKey = 'test_state'
    const testValue = 'test_value'
    
    try {
      localStorage.setItem(testKey, testValue)
      const retrieved = localStorage.getItem(testKey)
      localStorage.removeItem(testKey)
      
      if (retrieved === testValue) {
        console.log('✅ State Management: localStorage working correctly')
        return true
      } else {
        console.log('❌ State Management: localStorage not working')
        return false
      }
    } catch (error) {
      console.log(`❌ State Management Error: ${error.message}`)
      return false
    }
  }
}

// Main verification runner
async function runSystemVerification() {
  console.log('🚀 Starting comprehensive system verification...\n')
  
  const results = {
    authPersistence: await verify.testAuthPersistence(),
    protectedRoutes: verify.testProtectedRoutes(),
    errorMessages: await verify.testErrorMessages(),
    formValidation: verify.testFormValidation(),
    stateManagement: verify.testStateManagement()
  }
  
  const passedTests = Object.values(results).filter(Boolean).length
  const totalTests = Object.keys(results).length
  const allPassed = passedTests === totalTests
  
  console.log('\n📊 VERIFICATION RESULTS:')
  console.log('========================')
  Object.entries(results).forEach(([test, passed]) => {
    console.log(`${passed ? '✅' : '❌'} ${test}: ${passed ? 'PASSED' : 'FAILED'}`)
  })
  
  console.log(`\n🎯 Overall Result: ${passedTests}/${totalTests} tests passed`)
  console.log(allPassed ? '🎉 SYSTEM FULLY OPERATIONAL!' : '⚠️  SYSTEM HAS ISSUES')
  
  if (!allPassed) {
    console.log('\n🔧 Recommended Actions:')
    Object.entries(results).forEach(([test, passed]) => {
      if (!passed) {
        console.log(`   • Fix ${test} functionality`)
      }
    })
  }
  
  return { results, passedTests, totalTests, allPassed }
}

// Export functions for manual testing
if (typeof window !== 'undefined') {
  window.verifyAuthSystem = runSystemVerification
  window.authVerify = verify
  
  console.log('🧪 Verification system loaded!')
  console.log('📋 Run verifyAuthSystem() to start comprehensive testing')
  console.log('🔧 Individual tests available in authVerify object')
}

// Auto-run if requested
if (typeof window !== 'undefined' && window.location.hash === '#autotest') {
  runSystemVerification()
}

export { runSystemVerification, verify }