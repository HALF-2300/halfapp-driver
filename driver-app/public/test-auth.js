// Test Authentication Script - Run this in browser console to test role-based auth
// This script tests the role-based authentication directly in the running application

console.log('🔐 Starting Role-Based Authentication Tests...\n');

// Helper function to simulate login attempts
async function testLogin(email, password, expectedResult) {
  console.log(`\n📧 Testing login: ${email}`);
  
  try {
    // Get the email and password inputs
    const emailInput = document.querySelector('input[name="email"]');
    const passwordInput = document.querySelector('input[name="password"]');
    const submitButton = document.querySelector('button[type="submit"]');
    
    if (!emailInput || !passwordInput || !submitButton) {
      console.error('❌ Could not find login form elements');
      return false;
    }
    
    // Clear previous values
    emailInput.value = '';
    passwordInput.value = '';
    
    // Simulate typing
    emailInput.value = email;
    emailInput.dispatchEvent(new Event('input', { bubbles: true }));
    
    passwordInput.value = password;
    passwordInput.dispatchEvent(new Event('input', { bubbles: true }));
    
    // Wait a moment for state to update
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Click submit button
    submitButton.click();
    
    // Wait for response
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Check for error messages or success
    const errorElements = document.querySelectorAll('[class*="error"], [class*="red-"]');
    const successElements = document.querySelectorAll('[class*="success"], [class*="green-"]');
    
    if (expectedResult === 'success') {
      if (window.location.pathname !== '/login') {
        console.log('✅ SUCCESS: Login successful, redirected to dashboard');
        return true;
      } else {
        console.log('❌ FAILED: Login should have succeeded but user still on login page');
        return false;
      }
    } else {
      // Check for error messages
      let errorFound = false;
      errorElements.forEach(el => {
        if (el.textContent.toLowerCase().includes('access denied') || 
            el.textContent.toLowerCase().includes('not allowed') ||
            el.textContent.toLowerCase().includes('invalid')) {
          console.log(`✅ SUCCESS: Login correctly blocked - ${el.textContent}`);
          errorFound = true;
        }
      });
      
      if (!errorFound) {
        console.log('❌ FAILED: Expected error message but none found');
        return false;
      }
      return true;
    }
  } catch (error) {
    console.error(`❌ ERROR during test: ${error.message}`);
    return false;
  }
}

// Main test function
async function runAuthTests() {
  const tests = [
    {
      name: 'Driver Login (Should Succeed)',
      email: 'driver1@example.com',
      password: 'driver123',
      expected: 'success'
    },
    {
      name: 'Admin Login (Should Fail)',
      email: 'admin@example.com', 
      password: 'admin123',
      expected: 'error'
    },
    {
      name: 'Customer Login (Should Fail)',
      email: 'customer@example.com',
      password: 'customer123', 
      expected: 'error'
    },
    {
      name: 'Invalid Login (Should Fail)',
      email: 'invalid@example.com',
      password: 'wrongpassword',
      expected: 'error'
    }
  ];
  
  console.log(`\n🧪 Running ${tests.length} authentication tests...\n`);
  
  let passed = 0;
  let failed = 0;
  
  for (const test of tests) {
    console.log(`\n--- Test: ${test.name} ---`);
    
    // Navigate to login page first
    if (window.location.pathname !== '/login') {
      // If logged in, logout first
      const logoutBtn = document.querySelector('[onclick*="logout"], [class*="logout"]');
      if (logoutBtn) logoutBtn.click();
      
      // Navigate to login
      window.location.href = '/login';
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    const result = await testLogin(test.email, test.password, test.expected);
    
    if (result) {
      passed++;
      console.log(`✅ ${test.name} - PASSED`);
    } else {
      failed++;
      console.log(`❌ ${test.name} - FAILED`);
    }
    
    // Wait between tests
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  console.log(`\n📊 Test Results:`);
  console.log(`   ✅ Passed: ${passed}`);
  console.log(`   ❌ Failed: ${failed}`);
  console.log(`   📈 Success Rate: ${Math.round((passed / (passed + failed)) * 100)}%`);
  
  if (failed === 0) {
    console.log('\n🎉 ALL TESTS PASSED! Role-based authentication is working correctly.');
  } else {
    console.log('\n⚠️  Some tests failed. Please check the implementation.');
  }
}

// Instructions for manual testing
console.log(`
🎯 Authentication Test Instructions:

1. Make sure you're on the login page (http://localhost:3001/login)
2. Run: runAuthTests()
3. Or test manually with these credentials:

   ✅ DRIVER (Should Work):
      Email: driver1@example.com
      Password: driver123

   ❌ ADMIN (Should Fail):
      Email: admin@example.com  
      Password: admin123

   ❌ CUSTOMER (Should Fail):
      Email: customer@example.com
      Password: customer123

   ❌ INVALID (Should Fail):
      Email: invalid@example.com
      Password: wrongpassword

4. Check that error messages are clear and helpful
5. Verify that only drivers can access the dashboard

Type 'runAuthTests()' to run automated tests!
`);

// Export for console use
window.runAuthTests = runAuthTests;
window.testLogin = testLogin;