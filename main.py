from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
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

def getWebElementHash(element):
    post_art = element.find_element(By.TAG_NAME, "article")
    post_raw = post_art.get_attribute("aria-labelledby") or ""
    post_hash = hashlib.md5(post_raw.encode("utf-8")).hexdigest()
    return post_hash

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

def scrollFeed(driver, pause_between=1, load_timeout=10):
    start_key_listener()
    hashedPosts = []

    timeline = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH,
            "//div[@aria-label='Timeline: Your Home Timeline']"
        ))
    )
    feed = timeline.find_element(By.XPATH, "./div[1]")

    # --- grab the first tweet's raw aria-labelledby & hash it ---
    first_wrap   = feed.find_elements(By.XPATH, "./*")[0]
    first_art    = first_wrap.find_element(By.TAG_NAME, "article")
    first_raw    = first_art.get_attribute("aria-labelledby") or ""
    first_hash   = hashlib.md5(first_raw.encode("utf-8")).hexdigest()
    print(f"Tracking first tweet hash = {first_hash}\n")

    index = 0
    while True:
        print("fetching new posts…")
        posts = feed.find_elements(By.XPATH, "./*")

        # remove the count because it is not needed due to how the lazy load works
        # I will do this in the morning
        count = len(posts)

        realIndex = 0
        for post in posts:
            post_hash = getWebElementHash(post)
            print(f"[Post] Tweet {post_hash}")
            if (len(hashedPosts) == 0):
                break
            if (post_hash == hashedPosts[-1]):
                realIndex += 1
                break
            realIndex += 1

        print(f"[realIndex] {realIndex}")

        # print(f"[Status] Tweet {first_hash} is {status}")

        # --- lazy‑load logic ---
        if index >= count:
            if count == 0:
                print("No posts at all—exiting.")
                break
            print(f"Reached {count} posts; loading more…")
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                posts[-1]
            )
            try:
                WebDriverWait(driver, load_timeout).until(
                    lambda d: len(feed.find_elements(By.XPATH, "./*")) > count
                )
            except TimeoutException:
                print("No additional posts loaded—done.")
                break
            continue

        # --- pause support ---
        while paused:
            time.sleep(0.1)

        # --- highlight next post ---
        try:
            post = posts[realIndex]

            snippet = post.text.replace("\n", " ")[:30]
            print(f"→ Highlighting [{index+1}/{count}] '{snippet}…'")

            post_hash = getWebElementHash(post)
            print(f"[Current] Tweet {post_hash}")
            if (len(hashedPosts) > 1 and index > 1):
                prev_hash = getWebElementHash(posts[index-1])
                if (prev_hash != hashedPosts[-1]):
                    print(f"[Previous] Tweet error {prev_hash} != {hashedPosts[-1]}")\
                    # calcualte the diff between the two hashes and set the index 
     

            hashedPosts.append(post_hash)

            driver.execute_script("""
                arguments[0].style.border='3px solid blue';
                arguments[0].scrollIntoView({block:'center'});
            """, post)

            index += 1
            # interruptible sleep
            waited = 0
            while waited < pause_between:
                if not paused:
                    time.sleep(0.1)
                    waited += 0.1
                else:
                    # print the previous 8 tweet's hash for loop
                    print("here")
                    for i in range(5):
                        post_hash = getWebElementHash(posts[index-i-1])
                        print(f"[Previous] Tweet {post_hash}")       
                    break

        except StaleElementReferenceException:
            print(f"⚠️  Post at index {index} went stale—retrying.")
            time.sleep(1)
            continue

    print("✨ Finished iterating all lazy‑loaded posts.")
    print("✨ Finished list: ", hashedPosts)

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
