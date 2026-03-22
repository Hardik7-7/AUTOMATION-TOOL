import sys
from playwright.sync_api import sync_playwright

def run_test():
    browser = None
    page = None
    try:
        with sync_playwright() as p:
            print("Launching Chromium browser...")
            browser = p.chromium.launch()
            page = browser.new_page()

            # Step 1: Navigate to URL
            print("STEP 1: Navigating to 'http://fresh-install-testsetup-main.corp.coriolis.in/'...")
            url = 'http://fresh-install-testsetup-main.corp.coriolis.in/'
            page.goto(url)
            # Wait for the network to be idle, indicating the page has fully loaded its resources
            page.wait_for_load_state('networkidle')
            print(f"Successfully navigated to {url}")

            # Step 2: Verify the browser tab title
            print("STEP 2: Verifying the browser tab title displays 'Coriolis Technologies'...")
            expected_title = 'Coriolis Technologies'
            # Assert the title is as expected
            assert page.title() == expected_title, f"Assertion Failed: Expected title '{expected_title}' but found '{page.title()}'"
            print(f"Browser tab title '{page.title()}' is correct.")

            # Step 3: Verify 'Coriolis Technologies' brand text in the header navigation bar
            print("STEP 3: Verifying the 'Coriolis Technologies' brand text is visible in the header...")
            # Use a role selector combined with text to locate the brand in the header
            page.wait_for_selector('header:has-text("Coriolis Technologies")', state='visible')
            print("'Coriolis Technologies' brand text is visible in the header navigation bar.")

            # Step 4: Verify hero section main heading and descriptive text
            print("STEP 4: Verifying the main heading and descriptive text in the hero section...")
            # Verify the main heading
            page.wait_for_selector('h1:has-text("Coriolis Tech Solutions")', state='visible')
            # Verify the descriptive text
            page.wait_for_selector('p:has-text("Your one-stop solution for cutting-edge technology and innovation.")', state='visible')
            print("Main heading 'Coriolis Tech Solutions' and its descriptive text are visible in the hero section.")

            # Step 5: Verify 'Our Services' heading
            print("STEP 5: Verifying the 'Our Services' heading is visible...")
            page.wait_for_selector('h2:has-text("Our Services")', state='visible')
            print("'Our Services' heading is visible.")

            # Step 6: Verify all three service cards along with their headings, descriptions, and 'Learn more' buttons
            print("STEP 6: Verifying all three service cards (Web Development, Cloud Solutions, IT Consulting)...")

            # Service Card 1: Web Development
            print("  - Verifying 'Web Development' service card...")
            # Locate the card container first to scope subsequent searches
            web_dev_card = page.locator('div:has-text("Web Development")').filter(has=page.locator('h3:has-text("Web Development")'))
            web_dev_card.wait_for(state='visible')
            # Verify heading within the card
            web_dev_card.locator('h3:has-text("Web Development")').wait_for(state='visible')
            # Verify description within the card
            web_dev_card.locator('p:has-text("Crafting responsive and dynamic web applications that drive your business forward.")').wait_for(state='visible')
            # Verify 'Learn more' button within the card
            web_dev_card.locator('button:has-text("Learn more")').wait_for(state='visible')
            print("    'Web Development' card with heading, description, and 'Learn more' button is visible.")

            # Service Card 2: Cloud Solutions
            print("  - Verifying 'Cloud Solutions' service card...")
            cloud_sol_card = page.locator('div:has-text("Cloud Solutions")').filter(has=page.locator('h3:has-text("Cloud Solutions")'))
            cloud_sol_card.wait_for(state='visible')
            cloud_sol_card.locator('h3:has-text("Cloud Solutions")').wait_for(state='visible')
            cloud_sol_card.locator('p:has-text("Leverage scalable and secure cloud infrastructure to optimize operations and innovation.")').wait_for(state='visible')
            cloud_sol_card.locator('button:has-text("Learn more")').wait_for(state='visible')
            print("    'Cloud Solutions' card with heading, description, and 'Learn more' button is visible.")

            # Service Card 3: IT Consulting
            print("  - Verifying 'IT Consulting' service card...")
            it_consult_card = page.locator('div:has-text("IT Consulting")').filter(has=page.locator('h3:has-text("IT Consulting")'))
            it_consult_card.wait_for(state='visible')
            it_consult_card.locator('h3:has-text("IT Consulting")').wait_for(state='visible')
            it_consult_card.locator('p:has-text("Expert guidance for your digital transformation journey, ensuring strategic and efficient tech adoption.")').wait_for(state='visible')
            it_consult_card.locator('button:has-text("Learn more")').wait_for(state='visible')
            print("    'IT Consulting' card with heading, description, and 'Learn more' button is visible.")
            print("All three service cards and their contents are visible.")

            # Step 7: Verify the footer containing the copyright notice
            print("STEP 7: Verifying the footer copyright notice...")
            page.wait_for_selector('footer:has-text("© 2023 Coriolis Technologies. All rights reserved.")', state='visible')
            print("Footer containing the copyright notice is visible.")

            print("\nTest 'Verify Initial Page Load and Core Content Display' completed successfully!")

    except Exception as e:
        print(f"\nTEST FAILED: {e}", file=sys.stderr)
        if page:
            try:
                # Take a screenshot on failure
                screenshot_path = "screenshot.png"
                page.screenshot(path=screenshot_path)
                print(f"Screenshot '{screenshot_path}' taken on failure.", file=sys.stderr)
            except Exception as screenshot_error:
                print(f"Could not take screenshot: {screenshot_error}", file=sys.stderr)
        sys.exit(1) # Exit with a non-zero code to indicate failure
    finally:
        if browser:
            print("Closing browser...")
            browser.close()

if __name__ == "__main__":
    run_test()