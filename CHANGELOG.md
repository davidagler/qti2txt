# Changelog

## v0.1.0 (2026-02-18)

- Extracts resources (e.g., imgs, gifs, etc.) from quizzes.
- Replaces Wiris/Canvas `data-mathml` image tags (not raw mathml) with inline LaTeX.
- Improved QTI parsing and text2qti compatibility for a wider variety of Canvas exports

## v0.0.1 (2025-08-19)

- Initial release of QTI2TXT
- Support for Canvas QTI file conversion
- Multiple question type support (Multiple Choice, True/False, Short Answer, Essay, Numerical, Matching)
- LaTeX formula conversion from Canvas format to standard LaTeX
- CSV export of question details
- Two-stage logging setup
- Unique temporary file naming to prevent conflicts
- Basic QTI parsing functionality
- CLI interface with argparse
- Output directory specification
