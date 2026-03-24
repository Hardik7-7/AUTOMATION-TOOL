import sys
import re
from playwright.sync_api import sync_playwright, Playwright, expect

# Constants for the test
URL = "http://asrm-dump.corp.coriolis.in/#/login"
USERNAME = "Colama"
PASSWORD = "coriolis"
DASHBOARD_TEXT_IDENTIFIER = "text=Dashboard" # A common element expected on the Eigenserv dashboard

def run(playwright: Playwright):
    browser = None
    page = None
    try:
        print("===================================================================")
        print("Starting Test: Successful User Login and Dashboard Access")
        print("===================================================================")

        print("Step 1: Launching Chromium browser in headless mode...")
        browser = playwright.chromium.launch(headless=True) # Set headless=False for visual debugging
        page = browser.new_page()
        print("Browser launched and new page created.")

        print(f"Step 2: Navigating to the Eigenserv login page at {URL}")
        page.goto(URL)
        print("Navigation initiated.")

        print("Step 3: Waiting for key login page elements to ensure page load...")
        # Wait for the username, password input fields, and the login button
        page.wait_for_selector('[placeholder="Username"]', timeout=10000)
        page.wait_for_selector('[placeholder="Password"]', timeout=10000)
        page.wait_for_selector('text=LOGIN', timeout=10000)
        print("Login page loaded successfully, elements visible.")

        print(f"Step 4: Entering username '{USERNAME}' into the 'Username' field.")
        page.fill('[placeholder="Username"]', USERNAME)
        # Verify the username was entered correctly
        expect(page.locator('[placeholder="Username"]')).to_have_value(USERNAME)
        print("Username entered and verified.")

        print("Step 5: Entering password 'coriolis' into the 'Password' field.")
        page.fill('[placeholder="Password"]', PASSWORD)
        # Verify the password was entered correctly (input_value returns actual value)
        expect(page.locator('[placeholder="Password"]')).to_have_value(PASSWORD)
        print("Password entered and verified.")

        print("Step 6: Clicking the 'LOGIN' button to submit credentials.")
        page.click('text=LOGIN')
        print("LOGIN button clicked. Waiting for system response and redirection...")

        print("Step 7: Waiting for redirection to the Eigenserv dashboard.")
        # Wait for the URL to change to typically include '#/dashboard' after successful login
        # Increased timeout for navigation as login processing might take longer
        page.wait_for_url(re.compile(r".*#/dashboard"), timeout=30000)
        print(f"Redirected to dashboard URL: {page.url()}.")

        # Wait for a specific element that confirms dashboard access
        page.wait_for_selector(DASHBOARD_TEXT_IDENTIFIER, timeout=10000)
        print(f"Successfully identified '{DASHBOARD_TEXT_IDENTIFIER}' on the page, confirming dashboard access.")

        print("===================================================================")
        print("Test PASSED: User successfully logged in and accessed the dashboard.")
        print("===================================================================")

    except Exception as e:
        print("\n===================================================================")
        print(f"Test FAILED: An error occurred - {e}")
        print("===================================================================")
        if page:
            print("Attempting to take a screenshot 'screenshot.png' for debugging...")
            try:
                page.screenshot(path="screenshot.png")
                print("Screenshot saved as 'screenshot.png' in the current directory.")
            except Exception as se:
                print(f"Failed to take screenshot: {se}")
        sys.exit(1) # Exit with non-zero code on failure
    finally:
        if browser:
            print("Closing browser...")
            browser.close()
            print("Browser closed.")
            print("===================================================================")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
    sys.exit(0) # Exit with zero code on success