"""
Setup Script - Verify installation and configuration
"""

import sys
from pathlib import Path


def check_dependencies():
    """Check if all required packages are installed"""
    print("Checking dependencies...\n")

    required = [
        ('google-api-python-client', 'googleapiclient'),
        ('youtube-transcript-api', 'youtube_transcript_api'),
        ('python-dotenv', 'dotenv'),
        ('rich', 'rich'),
        ('pyyaml', 'yaml'),
        ('requests', 'requests'),
    ]

    missing = []
    for package_name, import_name in required:
        try:
            __import__(import_name)
            print(f"  [OK] {package_name}")
        except ImportError:
            print(f"  [MISSING] {package_name}")
            missing.append(package_name)

    return missing


def check_env():
    """Check if .env file exists and has required keys"""
    print("\nChecking environment configuration...\n")

    env_path = Path(__file__).parent.parent / '.env'

    if not env_path.exists():
        print("  [MISSING] .env file")
        print("  -> Copy .env.example to .env and fill in your API keys")
        return False

    from dotenv import load_dotenv
    import os

    load_dotenv(env_path)

    required_keys = ['YOUTUBE_API_KEY']
    missing = []

    for key in required_keys:
        value = os.getenv(key)
        if value and value != 'your_api_key_here':
            print(f"  [OK] {key}")
        else:
            print(f"  [MISSING] {key}")
            missing.append(key)

    return len(missing) == 0


def check_youtube_api():
    """Test YouTube API connection"""
    print("\nTesting YouTube API connection...\n")

    from dotenv import load_dotenv
    import os

    load_dotenv()
    api_key = os.getenv('YOUTUBE_API_KEY')

    if not api_key or api_key == 'your_api_key_here':
        print("  [SKIP] No API key configured")
        return False

    try:
        from googleapiclient.discovery import build
        youtube = build('youtube', 'v3', developerKey=api_key)

        # Test with a simple request
        request = youtube.channels().list(
            part='snippet',
            id='UC_x5XG1OV2P6uZZ5FSM9Ttw'  # Google Developers channel
        )
        response = request.execute()

        if response.get('items'):
            print("  [OK] YouTube API connection successful")
            return True
        else:
            print("  [FAIL] API returned no data")
            return False

    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def main():
    print("=" * 50)
    print("YouTube Recommendation System - Setup Check")
    print("=" * 50)

    # Check dependencies
    missing_deps = check_dependencies()

    if missing_deps:
        print(f"\nInstall missing packages with:")
        print(f"  pip install {' '.join(missing_deps)}")
        print("\nOr install all dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    # Check environment
    env_ok = check_env()

    if not env_ok:
        print("\nPlease configure your .env file before continuing.")
        sys.exit(1)

    # Test API
    api_ok = check_youtube_api()

    print("\n" + "=" * 50)
    if api_ok:
        print("Setup complete! You can now run:")
        print('  python scripts/fetch_channel.py "Two Minute Papers"')
    else:
        print("Setup incomplete. Please fix the issues above.")
    print("=" * 50)


if __name__ == '__main__':
    main()
