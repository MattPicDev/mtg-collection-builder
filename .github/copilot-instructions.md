# Copilot Instructions for MTG Collection Tool

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## Project Overview
This is a Python Flask web application for managing Magic: The Gathering card collections. The tool integrates with the Scryfall API to fetch card data and provides a streamlined workflow for users to enter their collection quantities set by set.

## Key Technologies
- **Flask**: Web framework for the local server
- **Scryfall API**: For retrieving MTG card data
- **CSV Export**: Compatible with popular collection trackers like MTGGoldfish and Deckbox
- **Bootstrap**: For responsive UI styling

## Code Style Guidelines
- Use Python PEP 8 style guidelines
- Include type hints where appropriate
- Add docstrings for all functions and classes
- Use descriptive variable names
- Keep functions focused and single-purpose

## API Integration
- Use the Scryfall API (https://scryfall.com/docs/api) for card data
- Implement proper error handling for API requests
- Cache API responses when appropriate
- Respect API rate limits

## CSV Export Format
The CSV export should include columns compatible with major collection trackers:
- Name
- Set
- Collector Number
- Quantity
- Foil (Yes/No)
- Condition
- Language

## UI/UX Considerations
- Create a clean, responsive interface
- Implement keyboard shortcuts for quick data entry
- Show progress indicators for set completion
- Provide search and filter capabilities
- Include set images and card previews when possible
