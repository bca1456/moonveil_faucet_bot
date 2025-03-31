from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import random

# File paths
evm_file = "evm_addresses.txt"  # File containing EVM addresses
proxy_file = "proxies.txt"  # Proxy file in format host:port:login:password
webdriver_path = "C:\\Webdrivers\\chromedriver.exe"  # Path to your WebDriver executable
switchyomega_crx = "C:\Extensions\SwitchyOmega_Chromium_2_5_19.crx"  # Path to the Proxy SwitchyOmega .crx file

# Load data from files
def load_file(file_path):
    with open(file_path, "r") as file:
        return file.read().splitlines()

evm_addresses = load_file(evm_file)
proxies = load_file(proxy_file)

import zipfile

def create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass):
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = """
    var config = {{
        mode: "fixed_servers",
        rules: {{
            singleProxy: {{
                scheme: "http",
                host: "{0}",
                port: parseInt({1})
            }},
            bypassList: ["localhost"]
        }}
    }};

    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

    function callbackFn(details) {{
        return {{
            authCredentials: {{
                username: "{2}",
                password: "{3}"
            }}
        }};
    }}

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        {{urls: ["<all_urls>"]}},
        ['blocking']
    );
    """.format(proxy_host, proxy_port, proxy_user, proxy_pass)

    pluginfile = 'proxy_auth_plugin.zip'
    with zipfile.ZipFile(pluginfile, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)
    return pluginfile

# Update the `set_up_browser_with_proxy` function
def set_up_browser_with_proxy(proxy):
    proxy_parts = proxy.split(":")  # Split proxy into components: host, port, username, password
    if len(proxy_parts) != 4:
        raise ValueError(f"Invalid proxy format: {proxy}. Expected format: host:port:username:password")

    proxy_host = proxy_parts[0]
    proxy_port = proxy_parts[1]
    proxy_user = proxy_parts[2]
    proxy_pass = proxy_parts[3]

    # Create the proxy authentication extension
    proxy_plugin = create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass)

    # Configure Chrome options
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_extension(proxy_plugin)

    # Initialize WebDriver with options
    service = Service(webdriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver

# Main function to interact with the faucet
def faucet_interact(evm_addresses, proxies):
    while evm_addresses and proxies:  # Continue while there are EVM addresses and proxies left
        evm_address = random.choice(evm_addresses)  # Select an EVM address
        proxy = random.choice(proxies)  # Select a proxy
        print(f"Using proxy: {proxy} | Wallet: {evm_address}")
        
        try:
            # Set up browser with the selected proxy
            driver = set_up_browser_with_proxy(proxy)

            # Navigate to the faucet website
            driver.get("https://faucet.testnet.moonveil.gg/")

            # Wait for the input field to appear
            input_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter your address or ENS name']"))
            )
            input_field.clear()  # Clear any existing input
            input_field.send_keys(evm_address)  # Enter the EVM address

            # Locate and click the "Request" button
            request_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@class='button is-primary is-rounded']"))
            )
            request_button.click()  # Simulate the click

            print(f"Request made for address: {evm_address}")

            # Wait for any notification element to appear (success or warning)
            notification = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'notification')]"))
            )

            # Extract the notification text
            notification_text = notification.text
            print(f"Notification Text: {notification_text}")

            # Check if the notification is a success or warning
            if "is-success" in notification.get_attribute("class"):
                print("Success notification detected.")
            elif "is-warning" in notification.get_attribute("class"):
                print("Warning notification detected.")
            else:
                print("Unknown notification type.")

            # Log the notification text to a file
            with open("notifications.log", "a") as log_file:
                log_file.write(f"Address: {evm_address} | Notification: {notification_text}\n")

            # Remove the used address and proxy
            evm_addresses.remove(evm_address)
            proxies.remove(proxy)
            print(f"Address and proxy removed from the list.")

            # Random delay between requests
            time_to_sleep = random.uniform(5, 10)
            print(f"Sleeping for {time_to_sleep:.2f} seconds...")
            time.sleep(time_to_sleep)

        except Exception as e:
            print(f"Error processing address {evm_address} with proxy {proxy}: {e}")
        finally:
            driver.quit()  # Close the browser

    print("All EVM addresses and proxies used. Script finished.")

# Execute the script
faucet_interact(evm_addresses, proxies)