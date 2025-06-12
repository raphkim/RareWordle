import requests
import json
import random
from datetime import datetime, timedelta

VALID_WORDS_URL = "https://gist.github.com/dracos/dd0668f281e685bad51479e5acaadb93/raw"


def get_solution_for_date(date: datetime) -> str:
    formatted_date = date.strftime("%Y-%m-%d")
    wordle_solution_url = f"https://www.nytimes.com/svc/wordle/v2/{formatted_date}.json"
    print(f"Fetching Wordle solution from {formatted_date}...")
    try:
        response_wordle_solution = requests.get(wordle_solution_url)
        response_wordle_solution.raise_for_status()  # Raise an exception for bad status codes
        # Split the text into a list of words, filtering out empty strings
        solution = response_wordle_solution.json()["solution"]
        print(f"Found solution for {formatted_date}: {solution}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching solution: {e}")
        raise e
    return solution


def get_valid_words() -> set:
    try:
        print("Fetching full list of valid Wordle words...")
        response_valid_words = requests.get(VALID_WORDS_URL)
        response_valid_words.raise_for_status()  # Raise an exception for bad status codes
        # Split the text into a list of words, filtering out empty strings
        all_valid_words = {w.lower() for w in response_valid_words.text.splitlines() if w.strip()}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching valid words list: {e}")
        raise e

    print(f"Found {len(all_valid_words)} total valid Wordle words.")
    return all_valid_words


def get_used_starters_from_date(date: datetime, mode: str = "hard") -> set:

    solution = get_solution_for_date(date)
    wordle_stats_url = f"https://static01.nyt.com/newsgraphics/2022/2022-01-25-wordle-solver/{solution}/guesses-by-round-{mode}.json"

    try:
        print("Fetching Wordle usage statistics...")
        response_stats = requests.get(wordle_stats_url)
        response_stats.raise_for_status()  # Raise an exception for bad status codes
        wordle_data = response_stats.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Wordle stats: {e}")
        raise e
    except json.JSONDecodeError as e:
        print(f"Error parsing Wordle stats JSON: {e}")
        raise e

    used_starters = set(wordle_data[0].keys())
    print(f"Found {len(used_starters)} unique used Wordle starters.")
    return used_starters


def generate_unused_wordle_starter(
        days: int = 3,
        hard: bool = True,
        normal: bool = True
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

    # Randomly select one of the unused words
    random_unused_word = random.choice(unused_starters)
    return random_unused_word


if __name__ == "__main__":
    word = generate_unused_wordle_starter()
    if word:
        print(f"\nYour random unused Wordle starter word is: {word.upper()}")
