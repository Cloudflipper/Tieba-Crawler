#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baidu Tieba crawler - handles DOM recycling behavior
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import re


def clean_tieba_text(input_file, output_file=None):
    """
    Clean Tieba text files by removing separators and floor markers.

    Args:
        input_file: Input file path.
        output_file: Output file path (if None, save as a cleaned file).
    """
    if output_file is None:
        output_file = input_file.replace('.txt', '_cleaned.txt')

    print(f"\nCleaning file: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned_lines = []
    removed_count = 0

    for line in lines:
        # Check whether this is a separator line (5+ consecutive dashes).
        if re.match(r'^-{5,}\s*$', line):
            removed_count += 1
            continue

        # Check whether this is a floor marker (e.g., [Floor 12]).
        if re.match(r'^\[Floor\s+\d+\]', line):
            removed_count += 1
            continue

        # Keep this line.
        cleaned_lines.append(line)

    # Save cleaned content.
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)

    print(f"✓ Cleaning completed! Removed {removed_count} lines, kept {len(cleaned_lines)} lines")
    print(f"  Cleaned file: {output_file}")

    return output_file

def crawl_tieba_post(url, output_file='tieba_content.txt', only_lz=True):
    """
    Crawl all text content from a Baidu Tieba post.

    Args:
        url: Tieba post URL.
        output_file: Output filename.
        only_lz: Whether to view only the original poster (default: True).
    """
    # Initialize Chrome browser.
    options = webdriver.ChromeOptions()
    # Uncomment the following line to run headless.
    # options.add_argument('--headless')

    # Disable unnecessary automation-related features for better stability.
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)

    try:
        print(f"Opening page: {url}")
        driver.get(url)

        # Maximize window for better scrolling behavior.
        driver.maximize_window()

        # Wait 15 seconds for manual verification.
        print("Waiting 15 seconds for verification...")
        time.sleep(15)

        # Wait additionally for page content to load.
        print("Waiting for page content to load...")
        try:
            # Try waiting for post containers to appear.
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, '.l_post')) > 0 or
                         len(d.find_elements(By.CSS_SELECTOR, 'div[class*="post"]')) > 0
            )
            print("Page content loaded")
        except:
            print("Wait timed out, continuing...")

        # Click the "Only OP" button.
        if only_lz:
            print("\nTrying to click 'Only OP'...")
            try:
                only_lz_btns = driver.find_elements(By.CSS_SELECTOR, '.lzl_link_unfold') or \
                              driver.find_elements(By.XPATH, "//*[contains(text(), '只看楼主')]") or \
                              driver.find_elements(By.CSS_SELECTOR, 'input[name="lz_only"]')

                if only_lz_btns:
                    only_lz_btns[0].click()
                    print("Clicked 'Only OP'")
                    time.sleep(2)  # Wait for page refresh.
                else:
                    print("'Only OP' button not found, continuing...")
            except Exception as e:
                print(f"Failed to click 'Only OP': {e}")

        # Store all collected floor posts.
        collected_posts = []

        print("=" * 60)
        print("Starting to crawl floor content...")
        print("=" * 60)

        # Track collected text keys to avoid duplicates.
        collected_texts = set()
        scroll_count = 0
        no_new_content_count = 0
        max_no_new_count = 5  # Stop after 5 consecutive rounds with no new content.

        while True:
            scroll_count += 1
            print(f"\n--- Scroll #{scroll_count} ---")

            # Try multiple selectors to find post containers.
            post_containers = []
            selectors_to_try = [
                '.pb-content-item',  # New Tieba layout.
                '.l_post',           # Legacy Tieba layout.
                'div[data-field]',   # Legacy fallback selector.
            ]

            for selector in selectors_to_try:
                post_containers = driver.find_elements(By.CSS_SELECTOR, selector)
                if post_containers:
                    print(f"Selector '{selector}' found {len(post_containers)} post containers")
                    break

            if not post_containers:
                print("No post containers found!")
                # Save debug info.
                with open('page_source_debug.html', 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                print("Saved page source to page_source_debug.html")
                break

            current_batch_count = 0

            # Iterate over each post container.
            for idx, container in enumerate(post_containers):
                try:
                    # Get all text content from the container.
                    text = container.text.strip()

                    # Filter out noisy content.
                    if not text or len(text) < 10:
                        continue
                    if '首页' in text and '大家都在逛的吧' in text:  # Skip sidebar.
                        continue
                    if '百度版权声明' in text:  # Skip footer.
                        continue
                    if '搜索吧或者贴子' in text:  # Skip search box.
                        continue
                    if '登录' in text and '注册' in text and len(text) < 50:  # Skip login box.
                        continue

                    # Use text as dedup key (new layout may not expose unique IDs).
                    text_key = text[:100]  # Use first 100 chars as the key.
                    if text_key in collected_texts:
                        continue

                    collected_texts.add(text_key)

                    # Try extracting floor metadata (from text or attributes).
                    floor_num = idx + 1
                    author_name = "Unknown User"

                    # Try extracting author/floor info from text.
                    lines = text.split('\n')
                    if len(lines) > 1:
                        # The first line may be author or title.
                        first_line = lines[0].strip()
                        if len(first_line) < 30:  # Likely author name.
                            author_name = first_line

                    # Save floor info.
                    collected_posts.append({
                        'floor': floor_num,
                        'author': author_name,
                        'content': text,
                        'text_key': text_key
                    })

                    current_batch_count += 1
                    print(f"  ✓ Collected #{floor_num}: {author_name} - {text[:50]}...")

                except Exception as e:
                    # Silently skip single-post errors.
                    continue

            print(f"This scroll collected {current_batch_count} new items; total {len(collected_posts)}")

            # If no new content was collected in this round.
            if current_batch_count == 0:
                no_new_content_count += 1
                print(f"No new content for {no_new_content_count}/{max_no_new_count} consecutive rounds")
                if no_new_content_count >= max_no_new_count:
                    print("No new content for multiple rounds, crawling completed")
                    break
            else:
                no_new_content_count = 0  # Reset counter.

            # Try multiple scrolling strategies.
            # Method 1: Scroll to page bottom.
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            # Method 2: Scroll last post container into view.
            if post_containers:
                try:
                    last_container = post_containers[-1]
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'end'});", last_container)
                    print(f"Scrolled to container #{len(post_containers)}")
                except:
                    pass

            # Method 3: Send Page Down keys.
            try:
                from selenium.webdriver.common.keys import Keys
                body = driver.find_element(By.TAG_NAME, 'body')
                body.send_keys(Keys.PAGE_DOWN)
                body.send_keys(Keys.PAGE_DOWN)
            except:
                pass

            # Wait for new content to load.
            print("Waiting for new content...")
            time.sleep(3)

            # Check if near page bottom.
            page_height = driver.execute_script("return document.body.scrollHeight")
            current_pos = driver.execute_script("return window.pageYOffset + window.innerHeight")

            print(f"Page height: {page_height}, current position: {current_pos}")

            if current_pos >= page_height - 200:  # Within 200px from the bottom.
                print("Near page bottom, trying two more times...")
                no_new_content_count += 1

            # Limit to 150 scrolls to avoid infinite loops.
            if scroll_count >= 150:
                print("Reached max scroll count, stopping crawl")
                break

        print(f"\nCrawling completed! Collected {len(collected_posts)} floors in total")

        # Save raw text file.
        raw_file = output_file.replace('.txt', '_raw.txt')
        print(f"\nSaving raw file: {raw_file}")
        with open(raw_file, 'w', encoding='utf-8') as f:
            f.write(f"Baidu Tieba Post Content\n")
            f.write(f"URL: {url}\n")
            f.write(f"Crawl time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Collected floors: {len(collected_posts)}\n")
            f.write("=" * 80 + "\n\n")

            for post in collected_posts:
                f.write(f"[Floor {post['floor']}] {post['author']}\n")
                f.write(f"{post['content']}\n")
                f.write("-" * 80 + "\n\n")

        # Also save JSON format.
        json_file = output_file.replace('.txt', '.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(collected_posts, f, ensure_ascii=False, indent=2)

        print(f"✓ Raw file saved: {raw_file}")
        print(f"✓ JSON file saved: {json_file}")

        # Automatically clean the text file.
        cleaned_file = clean_tieba_text(raw_file, output_file)

        print(f"\n" + "=" * 60)
        print(f"✓ All done!")
        print(f"  Raw file: {raw_file}")
        print(f"  Cleaned file: {cleaned_file}")
        print(f"  JSON file: {json_file}")
        print(f"  Collected floors: {len(collected_posts)}")
        print("=" * 60)

    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Close browser.
        print("\nPress Enter to close the browser...")
        input()
        driver.quit()


if __name__ == "__main__":
    # target url example: https://tieba.baidu.com/p/1145141919810
    url = "your_tieba_post_url_here"

    # Start crawling.
    # only_lz=True means only original poster; False means all floors.
    crawl_tieba_post(url, output_file='tieba_4989988691.txt', only_lz=True)
