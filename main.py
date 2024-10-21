import csv
import html
import json
import os
import re
from collections import Counter
from datetime import datetime
from typing import Dict, List, Set, Tuple

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

# Define common Portuguese compound expressions
PORTUGUESE_COMPOUNDS = {
    # Question words
    "o que": "o_que",  # what
    "por que": "por_que",  # why
    "para que": "para_que",  # for what/why
    # Preposition compounds
    "de acordo com": "de_acordo_com",  # according to
    "ao lado de": "ao_lado_de",  # next to
    "em frente": "em_frente",  # in front
    "em frente a": "em_frente_a",  # in front of
    "dentro de": "dentro_de",  # inside of
    "fora de": "fora_de",  # outside of
    "em cima de": "em_cima_de",  # on top of
    "em baixo de": "em_baixo_de",  # under
    "a partir de": "a_partir_de",  # starting from
    # Common expressions
    "até logo": "até_logo",  # see you later
    "com certeza": "com_certeza",  # certainly
    "mais ou menos": "mais_ou_menos",  # more or less
    "todo mundo": "todo_mundo",  # everybody
    "todo dia": "todo_dia",  # every day
    "boa noite": "boa_noite",  # good night
    "bom dia": "bom_dia",  # good morning
    "boa tarde": "boa_tarde",  # good afternoon
    # Time expressions
    "de vez em quando": "de_vez_em_quando",  # from time to time
    "de repente": "de_repente",  # suddenly
    "às vezes": "às_vezes",  # sometimes
    # Conjunctions and connectors
    "por isso": "por_isso",  # therefore
    "ou seja": "ou_seja",  # in other words
    "pelo menos": "pelo_menos",  # at least
    "assim que": "assim_que",  # as soon as
    "mesmo que": "mesmo_que",  # even if
    "antes de": "antes_de",  # before
    "depois de": "depois_de",  # after
    # Common verb phrases
    "tem que": "tem_que",  # have to
    "pode ser": "pode_ser",  # could be
    "quer dizer": "quer_dizer",  # means/want to say
    # Additional expressions
    "ainda não": "ainda_não",  # not yet
    "já não": "já_não",  # no longer
    "nem mesmo": "nem_mesmo",  # not even
}


def replace_compounds(text: str) -> str:
    """
    Replace compound expressions with their single-token versions.

    Args:
        text (str): Input text

    Returns:
        str: Text with compound expressions replaced
    """
    processed_text = text.lower()

    # Sort compounds by length (longest first) to avoid partial matches
    sorted_compounds = sorted(PORTUGUESE_COMPOUNDS.keys(), key=len, reverse=True)

    for compound in sorted_compounds:
        processed_text = processed_text.replace(
            compound, PORTUGUESE_COMPOUNDS[compound]
        )

    return processed_text


def clean_text(text: str) -> str:
    """
    Clean text by removing special characters and converting to lowercase.
    Also handles compound expressions.

    Args:
        text (str): Raw text to clean

    Returns:
        str: Cleaned text
    """
    # Decode HTML entities
    text = html.unescape(text)

    # Convert to lowercase
    text = text.lower()

    # Replace compound expressions before other cleaning
    text = replace_compounds(text)

    # Remove special characters but keep Portuguese accented characters and underscores (for compounds)
    text = re.sub(r"[^a-záéíóúâêîôûãõàèìòùäëïöüçñ\s_]", " ", text)

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def html_to_text(content: str) -> str:
    """
    Convert HTML content to plain text.

    Args:
        content (str): HTML content

    Returns:
        str: Plain text
    """
    soup = BeautifulSoup(content, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    return soup.get_text()


def get_word_frequencies(text: str) -> Counter:
    """
    Get word frequencies from text.

    Args:
        text (str): Text to analyze

    Returns:
        Counter: Word frequency counter
    """
    words = text.split()
    return Counter(words)


def analyze_epub(epub_path: str) -> List[Tuple[str, Dict[str, int]]]:
    """
    Analyze word frequencies by chapter in an EPUB file.

    Args:
        epub_path (str): Path to EPUB file

    Returns:
        List[Tuple[str, Dict[str, int]]]: List of (chapter_title, word_frequencies) tuples
    """
    try:
        book = epub.read_epub(epub_path)
        chapter_analyses = []

        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            # Try to get chapter title from the document
            content = item.get_content().decode("utf-8")
            soup = BeautifulSoup(content, "html.parser")
            title = soup.find("title")
            if title:
                chapter_title = title.get_text()
            else:
                # Try to find first heading if no title
                heading = soup.find(["h1", "h2"])
                chapter_title = heading.get_text() if heading else item.get_name()

            # Convert HTML to text and clean it
            text = html_to_text(content)
            cleaned_text = clean_text(text)

            # Get word frequencies
            frequencies = get_word_frequencies(cleaned_text)

            chapter_analyses.append((chapter_title, dict(frequencies)))

        return chapter_analyses

    except Exception as e:
        print(f"Error processing EPUB: {str(e)}")
        return []


def export_to_csv(
    chapter_analyses: List[Tuple[str, Dict[str, int]]],
    min_frequency: int = 1,
    sort_by: str = "frequency",
) -> None:
    """
    Export word frequency analysis to CSV files.

    Args:
        chapter_analyses: List of (chapter_title, word_frequencies) tuples
        min_frequency: Minimum frequency to include in output
        sort_by: 'frequency' or 'alphabetical'
    """
    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"word_frequency_analysis_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    # Export individual chapter files
    for chapter_title, frequencies in chapter_analyses:
        # Clean filename
        clean_title = re.sub(r"[^\w\s-]", "", chapter_title)
        clean_title = clean_title.replace(" ", "_")
        filename = os.path.join(output_dir, f"{clean_title}_frequencies.csv")

        # Filter and sort frequencies
        filtered_frequencies = {
            word: freq for word, freq in frequencies.items() if freq >= min_frequency
        }

        if sort_by == "frequency":
            sorted_words = sorted(
                filtered_frequencies.items(), key=lambda x: (-x[1], x[0])
            )
        else:  # alphabetical
            sorted_words = sorted(filtered_frequencies.items(), key=lambda x: x[0])

        # Write to CSV
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Word", "Frequency"])
            writer.writerows(sorted_words)

    # Export combined analysis
    combined_filename = os.path.join(output_dir, "combined_analysis.csv")
    all_words = set()
    chapter_word_counts = {}

    # First pass: collect all unique words
    for chapter_title, frequencies in chapter_analyses:
        filtered_frequencies = {
            word: freq for word, freq in frequencies.items() if freq >= min_frequency
        }
        all_words.update(filtered_frequencies.keys())
        chapter_word_counts[chapter_title] = filtered_frequencies

    # Sort words according to specified method
    if sort_by == "frequency":
        # Calculate total frequency across all chapters for sorting
        total_frequencies = Counter()
        for frequencies in chapter_word_counts.values():
            total_frequencies.update(frequencies)
        all_words = sorted(all_words, key=lambda x: (-total_frequencies[x], x))
    else:  # alphabetical
        all_words = sorted(all_words)

    # Write combined CSV
    with open(combined_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Header row with chapter titles
        header = ["Word"] + [title for title, _ in chapter_analyses] + ["Total"]
        writer.writerow(header)

        # Write data for each word
        for word in all_words:
            row = [word]
            total = 0
            for chapter_title, _ in chapter_analyses:
                freq = chapter_word_counts[chapter_title].get(word, 0)
                row.append(freq)
                total += freq
            row.append(total)
            writer.writerow(row)

    print(f"\nCSV files exported to directory: {output_dir}")
    print(f"Individual chapter files and combined analysis have been created.")


def print_compounds_found(chapter_analyses: List[Tuple[str, Dict[str, int]]]) -> None:
    """
    Print statistics about compound expressions found in the text.

    Args:
        chapter_analyses: List of (chapter_title, word_frequencies) tuples
    """
    print("\n=== Compound Expressions Analysis ===")

    # Create reverse mapping for easier lookup
    reverse_compounds = {v: k for k, v in PORTUGUESE_COMPOUNDS.items()}

    # Track compounds found across all chapters
    total_compounds = Counter()

    for chapter_title, frequencies in chapter_analyses:
        compounds_in_chapter = {
            word: freq
            for word, freq in frequencies.items()
            if word in reverse_compounds
        }

        if compounds_in_chapter:
            print(f"\nChapter: {chapter_title}")
            for compound, freq in sorted(
                compounds_in_chapter.items(), key=lambda x: (-x[1], x[0])
            ):
                original = reverse_compounds[compound]
                print(f"'{original}' appears {freq} times")
                total_compounds[compound] += freq

    print("\nTotal Compound Expressions Across All Chapters:")
    for compound, total in sorted(total_compounds.items(), key=lambda x: (-x[1], x[0])):
        original = reverse_compounds[compound]
        print(f"'{original}': {total} total occurrences")


def print_chapter_analysis(
    chapter_analyses: List[Tuple[str, Dict[str, int]]],
    output_format: str = "text",
    min_frequency: int = 1,
    sort_by: str = "frequency",
    export_csv: bool = True,
) -> None:
    """
    Print word frequency analysis for each chapter and optionally export to CSV.

    Args:
        chapter_analyses: List of (chapter_title, word_frequencies) tuples
        output_format: 'text' or 'json'
        min_frequency: Minimum frequency to include in output
        sort_by: 'frequency' or 'alphabetical'
        export_csv: Whether to export results to CSV files
    """
    # Print compound expressions analysis first
    print_compounds_found(chapter_analyses)

    results = {}

    for chapter_title, frequencies in chapter_analyses:
        # Filter words by minimum frequency
        filtered_frequencies = {
            word: freq for word, freq in frequencies.items() if freq >= min_frequency
        }

        # Sort words according to specified method
        if sort_by == "frequency":
            sorted_words = sorted(
                filtered_frequencies.items(), key=lambda x: (-x[1], x[0])
            )
        else:  # alphabetical
            sorted_words = sorted(filtered_frequencies.items(), key=lambda x: x[0])

        if output_format == "json":
            results[chapter_title] = dict(sorted_words)
        else:
            print(f"\n=== {chapter_title} ===")
            print(f"Total unique words: {len(sorted_words)}")
            print("\nWord Frequencies:")
            for word, freq in sorted_words:
                print(f"{word}: {freq}")

            # Print some statistics
            total_words = sum(frequencies.values())
            print(f"\nChapter Statistics:")
            print(f"Total words: {total_words}")
            print(f"Unique words: {len(frequencies)}")

    if export_csv:
        export_to_csv(chapter_analyses, min_frequency, sort_by)


if __name__ == "__main__":
    epub_path = "Short Stories in Brazilian Portuguese for - Olly Richards.epub"

    # Analyze the book
    chapter_analyses = analyze_epub(epub_path)

    # Print results and export to CSV
    print_chapter_analysis(
        chapter_analyses,
        output_format="text",
        min_frequency=1,  # Include all words
        sort_by="frequency",
        export_csv=True,
    )
