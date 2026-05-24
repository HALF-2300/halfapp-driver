// Quick test - run this in browser console to create a test driver account
function createTestDriver() {
  const testDriver = {
    email: "test@driver.com",
    password: "password123",
    name: "Test Driver"
  };
  
  console.log("Creating test driver account...");
  
  // Get the API instance
  if (window.driverAPI) {
    window.driverAPI.register(testDriver)
      .then(result => {
        console.log("✅ Test driver created:", result);
        console.log("You can now login with:");
        console.log("Email: test@driver.com");
        console.log("Password: password123");
      })
      .catch(error => {
        console.log("❌ Error creating test driver:", error.message);
      });
  } else {
    console.log("❌ driverAPI not found on window object");
  }
}

// Make it available globally
window.createTestDriver = createTestDriver;

console.log("🧪 Test function loaded. Run 'createTestDriver()' in console to create a test account.");