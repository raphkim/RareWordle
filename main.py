import requests
import json
import random
import os
from datetime import datetime, timedelta
from typing import Callable
from flask import Flask, jsonify, request
from flask_cors import CORS

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes, allowing requests from your frontend HTML

# --- Configuration for Caching ---
CACHE_DIR = "wordle_cache"
SOLUTIONS_CACHE_DIR = os.path.join(CACHE_DIR, "solutions")
STARTERS_CACHE_DIR = os.path.join(CACHE_DIR, "starters")
VALID_WORDS_CACHE_FILE = os.path.join(CACHE_DIR, "valid_words.txt")
CACHE_EXPIRY_HOURS = 24  # Cache expires after 24 hours

VALID_WORDS_URL = "https://gist.github.com/dracos/dd0668f281e685bad51479e5acaadb93/raw"
WORDLE_SOLUTION_BASE_URL = "https://www.nytimes.com/svc/wordle/v2/"
WORDLE_STATS_BASE_URL = "https://static01.nyt.com/newsgraphics/2022/2022-01-25-wordle-solver/"

# Ensure cache directories exist
os.makedirs(SOLUTIONS_CACHE_DIR, exist_ok=True)
os.makedirs(STARTERS_CACHE_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)  # Ensure base cache dir exists for valid_words.txt


def _is_cache_valid(filepath: str, expiry_hours: int) -> bool:
    if not os.path.exists(filepath):
        return False
    file_modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
    return datetime.now() - file_modified_time < timedelta(hours=expiry_hours)


def get_solution_for_date(formatted_date: str) -> str:
    cache_filepath = os.path.join(SOLUTIONS_CACHE_DIR, f"{formatted_date}.json")

    if _is_cache_valid(cache_filepath, CACHE_EXPIRY_HOURS):
        print(f"Loading Wordle solution for {formatted_date} from cache...")
        try:
            with open(cache_filepath, 'r', encoding='utf-8') as f:
                return f.readline()
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading solution from cache ({formatted_date}), fetching new data: {e}")

    wordle_solution_url = f"{WORDLE_SOLUTION_BASE_URL}{formatted_date}.json"
    print(f"Fetching Wordle solution from {wordle_solution_url}...")
    try:
        response_wordle_solution = requests.get(wordle_solution_url)
        response_wordle_solution.raise_for_status()
        solution = response_wordle_solution.json()["solution"]
        print(f"Found solution for {formatted_date}: {solution}")

        # Save to cache
        with open(cache_filepath, 'w', encoding='utf-8') as f:
            f.write(solution)
        return solution
    except requests.exceptions.RequestException as e:
        print(f"Error fetching solution: {e}")
        raise e


def get_valid_words() -> set:
    if _is_cache_valid(VALID_WORDS_CACHE_FILE, CACHE_EXPIRY_HOURS):
        print("Loading full list of valid Wordle words from cache...")
        try:
            with open(VALID_WORDS_CACHE_FILE, 'r', encoding='utf-8') as f:
                return set(f.read().split())
        except IOError as e:
            print(f"Error loading valid words from cache, fetching new data: {e}")

    try:
        print("Fetching full list of valid Wordle words...")
        response_valid_words = requests.get(VALID_WORDS_URL)
        response_valid_words.raise_for_status()
        all_valid_words = {w.lower() for w in response_valid_words.text.splitlines() if w.strip()}

        # Save to cache
        with open(VALID_WORDS_CACHE_FILE, 'w', encoding='utf-8') as f:
            f.write(" ".join(all_valid_words))
        print("Valid Wordle words list cached.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching valid words list: {e}")
        raise e

    print(f"Found {len(all_valid_words)} total valid Wordle words.")
    return all_valid_words


def get_used_starters_from_date(formatted_date: str, mode: str = "hard") -> set:
    solution = get_solution_for_date(formatted_date)
    if not solution:
        print(f"Could not retrieve solution for {formatted_date}, skipping starter stats for this date.")
        return set()

    cache_filepath = os.path.join(STARTERS_CACHE_DIR, f"{formatted_date}_{mode}.json")
    if _is_cache_valid(cache_filepath, CACHE_EXPIRY_HOURS):
        print(f"Loading Wordle starter stats for {formatted_date} ({mode}) from cache...")
        try:
            with open(cache_filepath, 'r', encoding='utf-8') as f:
                return set(f.read().split())
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading starter stats from cache ({formatted_date}, {mode}), fetching new data: {e}")

    wordle_stats_url = f"{WORDLE_STATS_BASE_URL}{solution}/guesses-by-round-{mode}.json"

    try:
        print("Fetching Wordle usage statistics...")
        response_stats = requests.get(wordle_stats_url)
        response_stats.raise_for_status()  # Raise an exception for bad status codes
        wordle_data = response_stats.json()
        starters = set(wordle_data[0].keys()) if wordle_data and len(wordle_data) > 0 else set()

        # Save to cache
        with open(cache_filepath, 'w', encoding='utf-8') as f:
            f.write(" ".join(starters))
        print(f"Wordle starter stats for {formatted_date} ({mode}) cached.")
        print(f"Found {len(starters)} unique used Wordle starters.")
        return starters
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Wordle stats: {e}")
        raise e
    except json.JSONDecodeError as e:
        print(f"Error parsing Wordle stats JSON: {e}")
        raise e


def is_not_plural(starter: str) -> bool:
    return starter[-1] != 's'


def generate_unused_wordle_starters(
        days: int = 3,
        hard: bool = True,
        normal: bool = True,
        custom_filter: Callable[[str], bool] = None
) -> list:
    """
    Fetches Wordle usage stats and a full list of valid words,
    then returns a random word that hasn't been used as a solution.
    """

    all_valid_words = get_valid_words()
    used_starters = set()

    today = datetime.now()
    for day_delta in range(days):
        date = today - timedelta(days=day_delta)
        formatted_date = date.strftime("%Y-%m-%d")

        if normal:
            used_starters.update(get_used_starters_from_date(formatted_date, "normal"))
        if hard:
            used_starters.update(get_used_starters_from_date(formatted_date, "hard"))

    # Find words that are valid but haven't been used as solutions
    unused_starters = [w for w in all_valid_words if w not in used_starters]

    if not unused_starters:
        print("No unused valid words found. All valid words seem to have been used as solutions!")
        return []

    print(f"Found {len(unused_starters)} valid words that have not been used as starters in the past {days} days.")

    if custom_filter:
        unused_starters = list(filter(custom_filter, unused_starters))
        print(f"Found {len(unused_starters)} that matched the provided filter")

    unused_starters.sort()
    print(unused_starters)
    return unused_starters


# --- API Endpoints ---
@app.route('/api/generate_word', methods=['GET'])
def generate_word():
    """
    API endpoint to generate a random unused Wordle starter word.
    Accepts optional query parameters:
    - days (int): Number of past days to consider (default: 5)
    - hard (bool): Include hard mode stats (default: true)
    - normal (bool): Include normal mode stats (default: true)
    - excludePlural (bool): Exclude words ending with "s" (default: true)
    """
    days = request.args.get('days', default=5, type=int)
    hard_mode = request.args.get('hard', default='true').lower() == 'true'
    normal_mode = request.args.get('normal', default='true').lower() == 'true'
    exclude_plural = request.args.get('excludePlural', default='true').lower() == 'true'

    unused_starters = generate_unused_wordle_starters(
        days=days,
        hard=hard_mode,
        normal=normal_mode,
        custom_filter=is_not_plural if exclude_plural else None
    )

    if not unused_starters:
        print("No unused valid words found. All valid words seem to have been used as starters!")
        return jsonify({"word": "N/A", "message": "No unused valid words found."}), 200

    random_unused_word = random.choice(unused_starters)
    print(f"Generated word: {random_unused_word.upper()}")

    return jsonify({
        "word": random_unused_word.upper(),
        "message": f"Generated word considering last {days} days."
    }), 200


@app.route('/')
def home():
    """Simple home route, usually for testing if the server is up."""
    return "Wordle Backend is running! Access /api/generate_word to get a word."


if __name__ == '__main__':
    # Run the app in debug mode. In production, use a production-ready WSGI server.
    app.run(debug=True, port=5000)
