from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
import getpass
from dotenv import load_dotenv
import os

TWITTER_EMAIL = os.getenv("TWITTER_EMAIL")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD")
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")

def isTextPresent(driver, text, timeout=1):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{text}')]"))
        )
        return True
    except TimeoutException:
        return False

def handlePhoneEmailOrUsernamePrompt(driver):
    wait = WebDriverWait(driver, 10)
    try:
        wait.until(
            EC.text_to_be_present_in_element(
                (By.XPATH, "//span[text()='Sign in to X']"),
                "Sign in to X"
            )
        )
        if(TWITTER_EMAIL):
            email = TWITTER_EMAIL
        elif(TWITTER_USERNAME):
            email = input("Enter your X email or username: ")
        email_input = wait.until(
            EC.presence_of_element_located((By.NAME, "text"))
        )
        email_input.send_keys(Keys.CONTROL + "a")
        email_input.send_keys(Keys.BACKSPACE)
        email_input.send_keys(email)
        email_input.send_keys(Keys.ENTER)
    except TimeoutException:
        print("No sign in prompt.")

def handlePhoneOrUsernamePrompt(driver):
    wait = WebDriverWait(driver, 10)
    try:
        wait.until(
            EC.text_to_be_present_in_element(
                (By.XPATH, "//span[text()='Enter your phone number or username']"),
                "Enter your phone number or username"
            )
        )

        if(TWITTER_USERNAME):
            username = TWITTER_USERNAME
        elif(TWITTER_EMAIL):
            username = input("Enter your X email or username: ")

        username_input = wait.until(
            EC.presence_of_element_located((By.NAME, "text"))
        )
        username_input.send_keys(Keys.CONTROL + "a")
        username_input.send_keys(Keys.BACKSPACE)
        username_input.send_keys(username)
        username_input.send_keys(Keys.ENTER)
    except TimeoutException:
        print("No phone number or username prompt.")
    
def handlePasswordPrompt(driver):
    wait = WebDriverWait(driver, 10)
    try:
        wait.until(
            EC.text_to_be_present_in_element(
                (By.XPATH, "//span[text()='Enter your password']"),
                "Enter your password"
            )
        )
        if(TWITTER_PASSWORD):
            password = TWITTER_PASSWORD
        else:
            password = getpass.getpass("Enter your X password: ")

        password_input = wait.until(
            EC.presence_of_element_located((By.NAME, "password"))
        )
        password_input.send_keys(Keys.CONTROL + "a")
        password_input.send_keys(Keys.BACKSPACE)
        password_input.send_keys(password)
        password_input.send_keys(Keys.ENTER)
    except TimeoutException:
        print("No password prompt.")

def getCurrentLoginStep(driver):
    print("Current URL:", driver.current_url)

def handleSignIn(driver, maxAttempts=5, failedAttempts=0):
    if failedAttempts >= maxAttempts:
        print("Max attempts reached. Exiting.")
        return False

    if isTextPresent(driver, "Sign in to X"):
        print("Sign in to X prompt detected.")
        handlePhoneEmailOrUsernamePrompt(driver)
        return handleSignIn(driver, maxAttempts, failedAttempts + 1)

    if isTextPresent(driver, "Enter your phone number or username"):
        print("Enter your phone number or username prompt detected.")
        handlePhoneOrUsernamePrompt(driver)
        return handleSignIn(driver, maxAttempts, failedAttempts + 1)

    if isTextPresent(driver, "Enter your password"):
        print("Enter your password prompt detected.")
        handlePasswordPrompt(driver)
        return handleSignIn(driver, maxAttempts, failedAttempts + 1)

    # If no login prompts are found, assume we are logged in
    print("User logged in successfully.")
    return True

def main():
    chrome_opts = Options()
    chrome_opts.add_argument("--window-size=1920,1080")
    # chrome_opts.add_argument("--headless=new")
    # chrome_opts.add_argument("--disable-gpu")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_opts)

    try:
        driver.get("https://twitter.com/login")
        print("Page title:", driver.title)

        if(handleSignIn(driver)):
            print("Sign in successful.")

            driver.save_screenshot("screenshots/screenshot.png")
            print("Screenshot saved as screenshot.png")

            # Ok now here I want to pass the screenshot to the LLM

            input("Press Enter to exit…")
        else:
            print("Sign in failed.")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
