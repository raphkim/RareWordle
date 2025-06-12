import requests
import json
import random
import os
from datetime import datetime, timedelta
from typing import Callable

# --- Configuration for Caching ---
CACHE_DIR = "wordle_cache"
SOLUTIONS_CACHE_DIR = os.path.join(CACHE_DIR, "solutions")
STARTERS_CACHE_DIR = os.path.join(CACHE_DIR, "starters")
VALID_WORDS_CACHE_FILE = os.path.join(CACHE_DIR, "valid_words.txt")
CACHE_EXPIRY_HOURS = 24  # Cache expires after 24 hours

VALID_WORDS_URL = "https://gist.github.com/dracos/dd0668f281e685bad51479e5acaadb93/raw"

# Ensure cache directories exist
os.makedirs(SOLUTIONS_CACHE_DIR, exist_ok=True)
os.makedirs(STARTERS_CACHE_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True) # Ensure base cache dir exists for valid_words.txt


def _is_cache_valid(filepath: str, expiry_hours: int) -> bool:
    if not os.path.exists(filepath):
        return False
    file_modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
    return datetime.now() - file_modified_time < timedelta(hours=expiry_hours)


def get_solution_for_date(date: datetime) -> str:
    formatted_date = date.strftime("%Y-%m-%d")
    cache_filepath = os.path.join(SOLUTIONS_CACHE_DIR, f"{formatted_date}.json")

    if _is_cache_valid(cache_filepath, CACHE_EXPIRY_HOURS):
        print(f"Loading Wordle solution for {formatted_date} from cache...")
        try:
            with open(cache_filepath, 'r', encoding='utf-8') as f:
                return f.readline()
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading solution from cache ({formatted_date}), fetching new data: {e}")

    wordle_solution_url = f"https://www.nytimes.com/svc/wordle/v2/{formatted_date}.json"
    print(f"Fetching Wordle solution from {formatted_date}...")
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


def get_used_starters_from_date(date: datetime, mode: str = "hard") -> set:
    solution = get_solution_for_date(date)
    if not solution:
        print(f"Could not retrieve solution for {date.strftime('%Y-%m-%d')}, skipping starter stats for this date.")
        return set()

    formatted_date = date.strftime("%Y-%m-%d")
    cache_filepath = os.path.join(STARTERS_CACHE_DIR, f"{formatted_date}_{mode}.json")
    if _is_cache_valid(cache_filepath, CACHE_EXPIRY_HOURS):
        print(f"Loading Wordle starter stats for {formatted_date} ({mode}) from cache...")
        try:
            with open(cache_filepath, 'r', encoding='utf-8') as f:
                return set(f.read().split())
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading starter stats from cache ({formatted_date}, {mode}), fetching new data: {e}")

    wordle_stats_url = f"https://static01.nyt.com/newsgraphics/2022/2022-01-25-wordle-solver/{solution}/guesses-by-round-{mode}.json"

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


def generate_unused_wordle_starter(
        days: int = 3,
        hard: bool = True,
        normal: bool = True,
        custom_filter: Callable[[str], bool] = None
):
    """
    Fetches Wordle usage stats and a full list of valid words,
    then returns a random word that hasn't been used as a solution.
    """

    all_valid_words = get_valid_words()
    used_starters = set()

    today = datetime.now()
    for day_delta in range(days):
        date = today - timedelta(days=day_delta)
        if normal:
            used_starters.update(get_used_starters_from_date(date, "normal"))
        if hard:
            used_starters.update(get_used_starters_from_date(date, "hard"))

    # Find words that are valid but haven't been used as solutions
    unused_starters = [w for w in all_valid_words if w not in used_starters]

    if not unused_starters:
        print("No unused valid words found. All valid words seem to have been used as solutions!")
        return None

    print(f"Found {len(unused_starters)} valid words that have not been used as starters in the past {days} days.")

    if custom_filter:
        unused_starters = list(filter(custom_filter, unused_starters))
        print(f"Found {len(unused_starters)} that matched the provided filter")

    print(sorted(list(unused_starters)))

    # Randomly select one of the unused words
    random_unused_word = random.choice(unused_starters)
    return random_unused_word


if __name__ == "__main__":
    def no_plurals(starter_word) -> bool:
        return starter_word[-1] != 's'

    word = generate_unused_wordle_starter(custom_filter=no_plurals)
    if word:
        print(f"\nYour random unused Wordle starter word is: {word.upper()}")
