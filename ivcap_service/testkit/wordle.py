#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""
Wordle game simulation worker function (used for the 'wordle' section of a
'test-batch' Request).

Plays a game of Wordle against a built-in AI solver - picking a random
secret word (or using the one provided) and letting the solver guess it
within a configurable number of attempts. Useful as a CPU-light, dependency-
free example of a self-contained, stateful computation.
"""

import random
from time import sleep

from pydantic import BaseModel, Field

from ivcap_service import JobContext, getLogger

logger = getLogger("app")


DEFAULT_THINKING_TIME_SECONDS = 0
DEFAULT_MAX_ATTEMPTS = 6


class WordleTester(BaseModel):
    thinking_time: int | None = Field(
        DEFAULT_THINKING_TIME_SECONDS,
        description="Time (in seconds) to wait before placing each guess",
    )
    max_attempts: int | None = Field(
        DEFAULT_MAX_ATTEMPTS, description="Number of allowed attempts before giving up"
    )


class WordleResult(BaseModel):
    secret: str = Field(..., description="The secret word that was being guessed")
    success: bool = Field(
        ..., description="True if the secret word was guessed within the allowed attempts"
    )
    attempts: int = Field(..., description="Number of attempts used")

# --- Global Word List ---
WORD_LIST = [
    "APPLE", "BAKER", "CRANE", "DAISY", "EAGLE",
    "FANCY", "GRAPE", "HOUSE", "IDEAS", "JUMPS",
    "KITES", "LEMON", "MAGIC", "NIGHT", "OCEAN",
    "PEARL", "QUEEN", "ROBIN", "STACK", "TIGER",
    "UNITY", "VIRUS", "WATER", "XENON", "YACHT",
    "ZONES", "BRICK", "SPOON", "PLANK", "FLAME",
    "SHINE", "BLUES", "CABLE", "DREAM", "FROST",
    "AGILE", "BLANK", "CHAMP", "DRIVE", "EVERY",
    "FAULT", "GHOST", "HASTY", "INDEX", "JOLLY",
    "KNEEL", "LOVER", "MERRY", "NURSE", "OASIS",
    "PAINT", "QUICK", "ROUGH", "SHAPE", "TRICK",
    "UNDER", "VITAL", "WHOLE", "YOUNG", "ZEBRA"
]

# --- WordleGame Class (Simulating the Wordle Game's Behavior) ---


class WordleGame:
    def __init__(self, secret_word):
        self.secret_word = secret_word.upper()
        self.guesses_made = []
        self.is_solved = False

    def check_guess(self, guess):
        """
        Compares a guess to the secret word and returns Wordle-style feedback.
        'G' = Green (correct letter, correct position)
        'Y' = Yellow (correct letter, wrong position)
        'X' = Gray (letter not in the word)
        """
        guess = guess.upper()
        if len(guess) != 5:
            raise ValueError("Guess must be 5 letters long.")
        if not guess.isalpha():
            raise ValueError("Guess must contain only letters.")

        self.guesses_made.append(guess)

        feedback = [''] * 5  # Initialize feedback list
        secret_word_counts = {}

        # Populate counts of letters in the secret word
        for char in self.secret_word:
            secret_word_counts[char] = secret_word_counts.get(char, 0) + 1

        # First pass: Identify Green letters and decrement counts
        for i in range(5):
            if guess[i] == self.secret_word[i]:
                feedback[i] = 'G'  # Green
                secret_word_counts[guess[i]] -= 1

        # Second pass: Identify Yellow and Gray letters
        for i in range(5):
            if feedback[i] == '':  # Only process if not already marked Green
                if guess[i] in self.secret_word and secret_word_counts.get(guess[i], 0) > 0:
                    feedback[i] = 'Y'  # Yellow
                    secret_word_counts[guess[i]] -= 1
                else:
                    feedback[i] = 'X'  # Gray

        if guess == self.secret_word:
            self.is_solved = True

        return feedback

    def is_game_solved(self):
        """Returns True if the secret word has been guessed."""
        return self.is_solved

    def get_guesses_made(self):
        """Returns a list of all guesses made in this game."""
        return self.guesses_made

# --- WordleSolver Class (The AI Player) ---


class WordleSolver:
    def __init__(self, word_list):
        """
        Initializes the solver with a list of all possible words.
        """
        self.all_words = [word.upper() for word in word_list if len(
            word) == 5 and word.isalpha()]
        # Solver's current set of candidates
        self.possible_words = list(self.all_words)

        # Solver's knowledge state:
        # e.g., ['', '', 'A', '', ''] means 'A' is 3rd letter
        self.known_greens = [''] * 5
        # Set of letters known to be yellow at that position
        self.known_yellows = [set() for _ in range(5)]
        self.known_grays = set()  # Set of letters known NOT to be in the word at all

        self.feedback_history = []  # Stores (guess, feedback) tuples

    def filter_words(self, guess, feedback):
        """
        Updates the solver's knowledge and filters the list of possible words
        based on the provided guess and its feedback.
        """
        new_possible_words = []

        # Step 1: Update known information based on the latest feedback
        for i, (char_guess, fb_code) in enumerate(zip(guess, feedback)):
            if fb_code == 'G':
                self.known_greens[i] = char_guess
            elif fb_code == 'Y':
                self.known_yellows[i].add(char_guess)
            elif fb_code == 'X':
                # Add to gray only if the letter isn't known to be green or yellow elsewhere.
                # This handles cases like 'APPLE' where one 'P' might be green/yellow and another gray.
                is_known_present_elsewhere = False
                for j in range(5):
                    if self.known_greens[j] == char_guess:
                        is_known_present_elsewhere = True
                        break
                    if char_guess in self.known_yellows[j]:
                        is_known_present_elsewhere = True
                        break
                if not is_known_present_elsewhere:
                    self.known_grays.add(char_guess)

        # Step 2: Filter `possible_words` based on the updated knowledge
        for word in self.possible_words:
            is_valid = True

            # Rule A: Check greens (must match known green letters at specific positions)
            for i in range(5):
                if self.known_greens[i] != '' and word[i] != self.known_greens[i]:
                    is_valid = False
                    break
            if not is_valid:
                continue

            # Rule B: Check yellows (must contain the yellow letter, but NOT at the yellow's position)
            for i in range(5):
                for yellow_char in self.known_yellows[i]:
                    if yellow_char not in word:  # Word must contain the yellow letter
                        is_valid = False
                        break
                    if word[i] == yellow_char:  # Word must NOT have yellow letter at this position
                        is_valid = False
                        break
                if not is_valid:
                    break
            if not is_valid:
                continue

            # Rule C: Check grays (must not contain any known gray letters)
            # This accounts for letters that were completely ruled out.
            for char_gray in self.known_grays:
                if char_gray in word:
                    is_valid = False
                    break
            if not is_valid:
                continue

            # If all rules pass, the word is still a possibility
            new_possible_words.append(word)

        self.possible_words = new_possible_words
        self.feedback_history.append((guess, feedback))

    def get_next_guess(self):
        """
        Determines the next best guess based on the current list of possible words.
        """
        if not self.possible_words:
            return None  # Solver has no more words to guess

        if len(self.possible_words) == len(self.all_words):
            # First guess strategy: Use a good starting word if available in the list.
            # These words are chosen for having common letters (vowels, S, T, R, N, E, A, I, O)
            good_starters = ["CRANE", "ADIEU", "SLATE", "RAISE", "TRASH"]
            for starter in good_starters:
                if starter in self.possible_words:
                    return starter
            # Fallback for first guess if no good starter is in the list
            return random.choice(self.possible_words)

        # If only one word remains, that's our guess!
        if len(self.possible_words) == 1:
            return self.possible_words[0]

        # Otherwise, for simplicity, pick a random word from the remaining possibilities.
        # A more advanced solver would use entropy or frequency analysis here to maximize
        # information gain.
        return random.choice(self.possible_words)


# --- Main Simulation Function ---


def play_wordle_with_solver(secret_word: str, props: WordleTester) -> WordleResult:
    """
    Simulates a Wordle game played by the AI solver.
    """
    logger.info(f"Starting Game for Secret Word: {secret_word.upper()}")
    game = WordleGame(secret_word)
    # Initialize solver with the global word list
    solver = WordleSolver(WORD_LIST)

    attempts = 0
    max_attempts = props.max_attempts if props.max_attempts is not None else DEFAULT_MAX_ATTEMPTS
    thinking_time = (
        props.thinking_time
        if props.thinking_time is not None
        else DEFAULT_THINKING_TIME_SECONDS
    )

    while not game.is_game_solved() and attempts < max_attempts:
        attempts += 1
        if thinking_time > 0:
            sleep(thinking_time)
        guess = solver.get_next_guess()

        if guess is None:
            logger.warning("Solver ran out of possible words to guess!")
            break

        # Ensure the guess is from the allowed list (important if `get_next_guess` was more complex)
        if guess not in solver.all_words:
            logger.warning(
                f"Solver attempted to guess '{guess}' which is not in its known word list. Skipping.")
            continue  # Or handle as an error / penalize attempt

        # print(f"Attempt {attempts}: Solver guesses '{guess}'")
        feedback = game.check_guess(guess)
        # print(f"Feedback: {feedback}")

        solver.filter_words(guess, feedback)

        # remaining_words_count = len(solver.possible_words)
        # print(f"Remaining possible words for solver: {remaining_words_count}")
        # Uncomment below to see the solver's detailed knowledge at each step
        # print(f"Solver's current knowledge: Greens={solver.known_greens}, Yellows={solver.known_yellows}, Grays={solver.known_grays}")

    return WordleResult(
        secret=secret_word.upper(),
        success=game.is_game_solved(),
        attempts=attempts,
    )


def play_random_wordle(props: WordleTester) -> WordleResult:
    secret_word = random.choice(WORD_LIST)
    return play_wordle_with_solver(secret_word, props)


def handle_wordle(req: WordleTester, ctxt: JobContext) -> WordleResult:
    """
    Plays a random game of Wordle, solved by a built-in AI solver, and
    reports the outcome.

    :param req: WordleTester object containing the thinking time between
        guesses and the maximum number of allowed attempts.
    :return: a WordleResult with the secret word, whether it was solved
        within the allowed attempts, and the number of attempts used.
    """
    with ctxt.report.step(
        "play_wordle",
        f"Playing Wordle (max_attempts={req.max_attempts}, thinking_time={req.thinking_time})",
        thinking_time=req.thinking_time,
        max_attempts=req.max_attempts,
    ) as step:
        result = play_random_wordle(req)
        step.finished(msg=f"Wordle finished - {result}", **result.model_dump())
        return result
