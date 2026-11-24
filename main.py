"""Entrypoint for the Charm the Cartographers entry.

The treasure map in ``entry.png`` was rendered locally by ``render_map.py``
(with PIL and the vendored Noto Serif fonts under ``fonts/``). Rendering at
grade time would depend on PIL and those fonts being present in the grader
sandbox, so the entrypoint itself uses only the Python standard library: it
copies the committed ``entry.png`` to ``/output/entry.png``, byte for byte,
on every run.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "entry.png")
OUTPUT_DIR = "/output"
OUTPUT = os.path.join(OUTPUT_DIR, "entry.png")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(SOURCE, "rb") as fh:
        data = fh.read()
    with open(OUTPUT, "wb") as fh:
        fh.write(data)


if __name__ == "__main__":
    main()
