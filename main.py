from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException

def main():
    # 1. Configure headless Chrome
    chrome_opts = Options()
    # chrome_opts.add_argument("--headless")
    # chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--window-size=1920,1080")

    # 2. Launch driver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_opts)

    try:
        driver.get("https://twitter.com/login")
        wait = WebDriverWait(driver, 15)
        print("Page title:", driver.title)

        # wait for the email field, type your email, then press ENTER
        email = input("Enter your X email: ")
        email_input = wait.until(
            EC.presence_of_element_located((By.NAME, "text"))
        )
        email_input.send_keys(email)
        email_input.send_keys(Keys.ENTER)

        try:
            # wait up to 10s for that span to appear
            wait.until(
                EC.text_to_be_present_in_element(
                    (By.XPATH, "//span[text()='Enter your phone number or username']"),
                    "Enter your phone number or username"
                )
            )
            # Route A: the prompt showed up
            username = input("Enter your X username: ")
            username_input = wait.until(
                EC.presence_of_element_located((By.NAME, "text"))
            )
            username_input.send_keys(username)
            username_input.send_keys(Keys.ENTER)
            # handle_phone_or_username_prompt()
        except TimeoutException:
            # Route B: it never appeared
            print("No phone number or username prompt.")
            print("No code for this section yet.")
            # handle_normal_flow()


        input("Press Enter to exit…")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
