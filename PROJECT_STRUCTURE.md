# FolderSnapshot Project Structure

This document outlines the organization of the FolderSnapshot project.

## Root Directory

- `FolderSnapshot.py`: Main application file containing all core functionality
- `README.md`: Project documentation in English
- `LICENSE`: MIT License file
- `FolderSnapshot_old_version.py`: Previous version of the program (kept for compatibility reference)

## Directories

### config/
Contains configuration files:
- `requirements.txt`: Project dependencies

### docs/
Documentation files:
- `INTERACTIVE_GUIDE.md`: Detailed guide for interactive mode usage
- `README_zh.md`: Project documentation in Chinese

### .github/
GitHub specific files:
- `README.md`: GitHub project description
- `workflows/ci.yml`: Continuous integration configuration

### Other Directories
- `.claude/`: Claude AI related configuration
- `.pytest_cache/`: pytest test cache files
- `scripts/`: Script files directory (to be populated)
- `test/`: Test files directory (to be populated)
- `tests/`: Test files directory (to be populated)

## Development Guidelines

### Code Standards
1. Follow PEP 8 Python coding standards
2. Functions and classes should have clear docstrings
3. Use meaningful English names for variables
4. Add comments for important functionality

### Testing
1. Use pytest for unit testing
2. Each major functional module should have corresponding test cases
3. Test files should be placed in the `tests/` directory

### Documentation
1. Important feature changes should update README.md
2. Interactive mode updates should update INTERACTIVE_GUIDE.md
3. Chinese documentation should be kept in sync with English documentation

## Release Process
1. Ensure all tests pass
2. Update version number and CHANGELOG
3. Update README documentation
4. Create Git tag
5. Push updates to repository