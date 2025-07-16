# Files to Keep for Production Implementation

## Design Documents (Keep)
- `docs/production_plan_tdd.md` - Our new TDD plan
- `library_comparison.md` - Technology decision rationale
- `persistent_sporadic_sync.py` - Reference for sporadic sync logic
- `monitor_chrome_memory.py` - Useful for validating memory constraints
- `SETUP_GUIDE.md` - User documentation template

## Useful Reference Code (Keep for now)
- `minimal_playwright_poc.py` - Shows the connection approach
- `refactored_dni_extractor.py` - BeautifulSoup extraction patterns

## Models to Adapt (Keep structure)
- `src/extractors/models.py` - Pydantic models to reuse

## To Remove (POC/Test files)
All test_*.py files in root (moved functionality to proper tests/)
All debug_*.py and check_*.py files
All scripts in scripts/ except maybe launch_chrome_with_claude.py

## New Structure Needed
- Proper pytest test structure
- Async pychrome implementation
- Production-ready error handling
- Configuration management