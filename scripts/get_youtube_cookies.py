"""
Get YouTube cookies using Playwright browser automation.
This creates a cookies.txt file that can be used to bypass rate limiting.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Installing playwright...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright", "-q"])
    from playwright.async_api import async_playwright


def cookies_to_netscape(cookies: list, domain: str = ".youtube.com") -> str:
    """Convert Playwright cookies to Netscape cookie format."""
    lines = ["# Netscape HTTP Cookie File", "# https://curl.se/docs/http-cookies.html", ""]

    for cookie in cookies:
        # Netscape format: domain, flag, path, secure, expiration, name, value
        domain_val = cookie.get('domain', domain)
        flag = "TRUE" if domain_val.startswith('.') else "FALSE"
        path = cookie.get('path', '/')
        secure = "TRUE" if cookie.get('secure', False) else "FALSE"
        expires = int(cookie.get('expires', 0))
        name = cookie.get('name', '')
        value = cookie.get('value', '')

        line = f"{domain_val}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}"
        lines.append(line)

    return '\n'.join(lines)


async def get_youtube_cookies(output_path: str = "cookies.txt", headless: bool = True):
    """
    Navigate to YouTube and capture cookies.

    Args:
        output_path: Path to save cookies.txt
        headless: Whether to run browser in headless mode
    """
    print("Starting browser...")

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("Navigating to YouTube...")
        await page.goto("https://www.youtube.com", wait_until="networkidle")

        # Wait a bit for cookies to be set
        await page.wait_for_timeout(3000)

        # Try to dismiss any consent dialogs
        try:
            # Look for accept buttons (common in EU)
            accept_button = page.locator('button:has-text("Accept all")')
            if await accept_button.count() > 0:
                await accept_button.first.click()
                await page.wait_for_timeout(2000)
        except Exception:
            pass

        # Get cookies
        cookies = await context.cookies()
        print(f"Captured {len(cookies)} cookies")

        # Filter YouTube-related cookies
        youtube_cookies = [c for c in cookies if 'youtube' in c.get('domain', '').lower() or 'google' in c.get('domain', '').lower()]
        print(f"YouTube/Google cookies: {len(youtube_cookies)}")

        # Convert to Netscape format
        cookie_content = cookies_to_netscape(youtube_cookies)

        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cookie_content)

        print(f"Cookies saved to: {output_path}")

        await browser.close()

        return len(youtube_cookies)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Get YouTube cookies using Playwright')
    parser.add_argument('--output', '-o', default='cookies.txt', help='Output file path')
    parser.add_argument('--visible', '-v', action='store_true', help='Show browser window')
    args = parser.parse_args()

    output_path = Path(args.output)

    try:
        count = asyncio.run(get_youtube_cookies(str(output_path), headless=not args.visible))
        if count > 0:
            print(f"\nSuccess! {count} cookies saved to {output_path}")
            print("\nYou can now run the fetch script with cookies:")
            print(f'  python scripts/fetch_channel.py "@GregIsenberg" --days 30 --save-transcripts')
        else:
            print("\nWarning: No cookies captured. Try running with --visible flag.")
    except Exception as e:
        print(f"Error: {e}")
        print("\nTry installing browser binaries:")
        print("  playwright install chromium")
        sys.exit(1)


if __name__ == "__main__":
    main()
