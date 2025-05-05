from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException
import getpass
from dotenv import load_dotenv
import os
import time
import threading
import sys
import termios
import tty
import hashlib

TWITTER_EMAIL = os.getenv("TWITTER_EMAIL")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD")
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")

paused = False


def start_key_listener():
    """Spawn a daemon thread that flips `paused` whenever spacebar is hit."""
    def listen():
        global paused
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        try:
            while True:
                ch = sys.stdin.read(1)
                if ch == ' ':
                    paused = not paused
                    state = "⏸ Paused" if paused else "▶️ Resumed"
                    print(f"\n{state}\n", end="", flush=True)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    t = threading.Thread(target=listen, daemon=True)
    t.start()

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

def is_in_viewport(driver, elem):
    return driver.execute_script("""
      const r = arguments[0].getBoundingClientRect();
      return r.top>=0 && r.left>=0 &&
             r.bottom<=(window.innerHeight||document.documentElement.clientHeight) &&
             r.right<=(window.innerWidth||document.documentElement.clientWidth);
    """, elem)

def scrollFeed(driver, pause_between=1.0, load_timeout=10):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import hashlib, time, traceback

    # Start your spacebar pause/resume listener
    start_key_listener()       # toggles global `paused`
    seen_hashes = set()        # hashes of tweets we've highlighted
    tweet_index = 0            # counter for which tweet we're on

    # 1) Locate the timeline container
    try:
        timeline = WebDriverWait(driver, load_timeout).until(
            EC.presence_of_element_located((By.XPATH,
                "//div[@aria-label='Timeline: Your Home Timeline']"
            ))
        )
        feed = timeline.find_element(By.XPATH, "./div[1]")
    except Exception as e:
        print("❌ Failed to locate timeline container:", e)
        return

    # 2) Main loop: fetch, filter, highlight
    while True:
        # 2a) Grab all wrappers in the feed
        try:
            wrappers = feed.find_elements(By.XPATH, "./*")
        except Exception as e:
            print("⚠️  Error fetching wrappers:", e)
            time.sleep(pause_between)
            continue

        # 2b) Filter wrappers to those with <article> and compute hashes
        valid = []
        for idx, wrap in enumerate(wrappers):
            try:
                arts = wrap.find_elements(By.TAG_NAME, "article")
                if not arts:
                    continue
                raw = arts[0].get_dom_attribute("aria-labelledby") or ""
                h = hashlib.md5(raw.encode("utf-8")).hexdigest()
                valid.append((wrap, h))
            except Exception as e:
                print(f"⚠️  Error hashing wrapper at index {idx}:", e)
                continue

        # 2c) Pick the first unseen tweet
        next_item = None
        for wrap, h in valid:
            if h not in seen_hashes:
                next_item = (wrap, h)
                break

        # 2d) If none, scroll down and retry
        if not next_item:
            try:
                print("No new tweets found. Scrolling…")
                driver.execute_script("window.scrollBy(0, window.innerHeight);")
            except Exception as e:
                print("⚠️  Scroll error:", e)
            time.sleep(pause_between)
            continue

        # 3) Highlight the next tweet
        wrap, h = next_item
        tweet_index += 1
        print(f"[#{tweet_index}] Highlighting tweet {h}")
        seen_hashes.add(h)

        try:
            driver.execute_script("""
                arguments[0].style.border = '3px solid blue';
                arguments[0].scrollIntoView({block:'center'});
            """, wrap)
        except Exception as e:
            print(f"⚠️  Error highlighting tweet #{tweet_index}:", e)

        # 4) Pause so you can see it (still responsive to spacebar)
        waited = 0.0
        while waited < pause_between:
            try:
                if not paused:
                    time.sleep(0.1)
                    waited += 0.1
                else:
                    time.sleep(0.1)
            except Exception:
                break
        # loop back for the next tweet

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

        # Need to convert this to a try catch block
        if(handleSignIn(driver)):
            print("Sign in successful.")

            if(isTextPresent(driver, "Boost your account security", 5)):
                print("Boost your account security prompt detected.")
                # Handle the prompt as needed (close the window, etc.)
            
            scrollFeed(driver)

            # driver.save_screenshot("screenshots/screenshot.png")
            # print("Screenshot saved as screenshot.png")
            # Ok now here I want to pass the screenshot to the LLM

            input("Press Enter to exit…")
        else:
            print("Sign in failed.")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
