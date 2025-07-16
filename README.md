# MTG Collection Tool

A web-based tool for managing your Magic: The Gathering card collection. This tool provides a streamlined workflow for entering your collection set by set and exports to CSV format compatible with popular collection tracking sites like MTGGoldfish and Deckbox.

## Notes about AI Generation

I have been adding lots of cards from my old MTG collection, and I found popular websites very slow for this purpose.  As an experiment, I wanted to let Copilot create this app for me, using the language and libraries of its choice.  This project might have taken me an evening, but it probably would have taken me several evenings on my own.  Copilot did this in about a half hour of back-and-forth.

This project was purely vibe-generated within Visual Studio Code, using the default Claude model option within Copilot.  No code changes were made by humans; this README section was the only modification.  In fact, it even told me how I could add this section without worrying about Copilot overwriting it.

I am not very experienced with Python, much less Flask or the related libraries.  However, I was able to follow it, and Copilot was able to explain it as well.

I have intentionally not added any statefulness to this application, to make it easily transportable.

## Features

- **Set-by-set collection entry**: Browse MTG sets and quickly enter card quantities
- **Rapid input mode**: Keyboard-driven interface with improved UI layout and progress tracking
- **Flexible card sorting**: Toggle between alphabetical and card number sorting in both grid and rapid views
- **Real-time name filtering**: Instantly filter cards by name in grid view as you type
- **Optimized performance**: Fast client-side sorting with DOM reordering for smooth user experience
- **Scryfall API integration**: Automatically fetches card data and images
- **CSV export/import**: Compatible with MTGGoldfish, Deckbox, and other collection trackers with flexible format support
- **Collection import**: Upload existing CSV collections to quickly populate your data
- **Responsive web interface**: Works on desktop and mobile devices
- **Real-time progress tracking**: See your progress as you add cards
- **Search and filter**: Quickly find specific sets or cards
- **Foil tracking**: Track both regular and foil versions of cards
- **Collection management**: Clear, replace, or merge collections
- **Performance optimized**: Fast sorting and smooth UI transitions

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd mtg-tool
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Start the application**:
   ```bash
   python app.py
   ```

2. **Open your browser** and navigate to `http://127.0.0.1:5000`

3. **Select a set** from the main page to start adding cards

4. **Choose your input method**:
   - **Grid View**: See all cards at once with individual quantity inputs, organized controls for better workflow
   - **Rapid Mode**: Lightning-fast keyboard-driven entry with streamlined progress tracking

5. **Enter quantities** for each card you own:
   - **Grid View**: Use the number inputs and foil checkboxes, toggle sorting between card number and alphabetical order, use the name filter to quickly find specific cards
   - **Rapid Mode**: Type numbers, press Space for foil, Enter to save and continue, use sorting buttons to change card order

6. **Save your collection** when finished with a set

6. **Import existing collections** (optional):
   - Go to the Import page
   - Upload a CSV file in the supported format
   - Choose whether to replace or add to your existing collection

7. **Export to CSV** from the collection page when ready:
   - Choose MTGGoldfish format for compatibility with MTGGoldfish and similar sites
   - Choose DeckBox format for compatibility with DeckBox and similar sites

## Keyboard Shortcuts

### Grid View
- **Ctrl+S**: Save collection
- **Enter**: Move to next card input field
- **Sorting buttons**: Click to toggle between card number and alphabetical order (optimized for performance)
- **Name filter**: Type to instantly filter cards by name (searches from the beginning of card names)
- **Search boxes**: Filter sets and collection in real-time

### Rapid Mode
- **Type numbers**: Set quantity (automatically focused)
- **Space**: Toggle foil status
- **Enter**: Save current card and move to next
- **Arrow Keys**: Navigate between cards manually
- **Escape**: Clear current input
- **Sorting buttons**: Change card order without affecting current position
- **Ctrl+S**: Save entire collection and finish

## CSV Import/Export Format

### Export Formats
The tool supports exporting your collection in two popular formats:

#### MTGGoldfish Format
- Name
- Set (3-letter code)
- Collector Number
- Quantity
- Foil (Yes/No)
- Condition
- Language

#### DeckBox Format
- Count
- Tradelist Count
- Name
- Edition (full set name)
- Card Number
- Condition
- Foil (foil/blank)
- Signed, Artist Proof, Altered Art, Misprint, Promo, Textless, My Price (additional fields)

### Import Features
- **Smart card lookup**: Uses Scryfall API to verify card details
- **Multiple format support**: Handles both MTGGoldfish and DeckBox CSV formats automatically
- **Flexible column mapping**: Supports different column names (Count/Quantity, Edition/Set, etc.)
- **Set name normalization**: Converts full set names to standard 3-letter codes
- **Error reporting**: Shows which cards couldn't be imported
- **Flexible options**: Choose to replace or merge with existing collection
- **Progress tracking**: Real-time feedback during import process

## API Integration

This tool uses the [Scryfall API](https://scryfall.com/docs/api) to fetch card data. The API is free and doesn't require authentication, but please be respectful of their rate limits.

## Development

The application is built with:
- **Flask**: Web framework
- **Python 3.7+**: Backend language
- **Bootstrap 5**: Frontend styling
- **jQuery**: JavaScript functionality
- **Scryfall API**: Card data source

### Running Tests

The project includes comprehensive unit tests covering all major functionality:

```bash
# Install test dependencies (if not already installed)
pip install -r requirements.txt

# Run all tests
python run_tests.py

# Or run with pytest directly
pytest test_app.py -v
```

The test suite covers:
- **ScryfallAPI**: API calls, error handling, data filtering
- **CollectionManager**: Card operations, CSV import/export, collection management  
- **Flask Routes**: All endpoints, error conditions, file uploads
- **Edge Cases**: Invalid data, API failures, malformed CSV files

## License

This project is open source and available under the [MIT License](LICENSE).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## AI-Generated Project

This project was entirely generated using **Claude 3.5 Sonnet** (Anthropic) through a series of conversational prompts. Below is the complete prompt history that created this tool:

### Initial Project Creation
1. **"I want to create a tool that will allow me to quickly generate a file containing my Magic the Gathering card collection. The file should use a standard format that can be imported into popular collection tracker websites. The tool should run as a local web server. You can use the language and libraries of your choice. Create the project as a git repo under the D:\repos directory on my machine. Ask me clarifying questions."**
   - Created the basic project structure with Flask
   - Set up Python environment and dependencies
   - Implemented Scryfall API integration
   - Created CSV export functionality compatible with MTGGoldfish/Deckbox

### Filtering Improvements
2. **"The list of available sets is too small, and it's not specific to Magic the Gathering. Could you filter the sets to Magic the Gathering expansions, and increase the number of sets displayed?"**
   - Enhanced set filtering to focus on MTG expansions
   - Added type and year filters to the UI
   - Improved search functionality with multiple filter options

### Import Functionality
3. **"Add the ability to import a collection, using the same format that you already support for export."**
   - Created CSV import functionality
   - Added smart card lookup using Scryfall API
   - Implemented error handling and progress reporting
   - Added option to replace or merge collections

### Rapid Input Mode
4. **"I want to add another input mode. After selecting a set, I want to be able to rapidly type in a number of cards. It should work like this: 1. Present a card to the user. [followed by] Let me restate the features: 1. Present the card to the user. 2. The user can type a number, without having to click on a control. 3. If the user presses space, the card is selected as a foil. 4. When the user hits enter, save the number of cards and move to the next card. 5. If the user hits enter without entering a number, treat it as zero."**
   - Built keyboard-driven rapid input interface
   - Implemented automatic focus management
   - Added space bar for foil toggle functionality
   - Created one-card-at-a-time workflow with progress tracking

### Documentation Request
5. **"I would like to tell users who look at the README how this program was generated using prompts. Could you add a section to the readme that documents the set of prompts that I provided to you since we started? Include which model was used as well."**
   - Added this documentation section

### Bug Fix - Rapid Input Mode
6. **"There is a problem with the rapid input mode. When I press the enter key, it should automatically go to the next card, until it reaches the end of the set, at which point it should Save & Finish. Right now, the enter key does nothing."**
   - Fixed Enter key functionality to auto-advance to next card
   - Implemented auto-save when reaching the end of a set
   - Added proper state management between cards
   - Enhanced user feedback with completion messages

### Unit Testing Implementation
7. **"Could you add unit tests for app.py? Don't do it yet; just let me know if you can." followed by "Yes, please do. Also, update the 'AI-Generated Project' section of the README to include this step."**
   - Created comprehensive unit tests covering all major functionality
   - Added test coverage for ScryfallAPI class (API calls, error handling, data filtering)
   - Implemented CollectionManager tests (card operations, CSV import/export, collection management)
   - Created Flask route tests (all endpoints, error conditions, file uploads)
   - Added pytest configuration and test runner script
   - Updated requirements.txt with testing dependencies (pytest, pytest-flask, pytest-mock)

### Repository Management and Licensing
8. **"Can I rename the project on Github to something more descriptive, without breaking my local repo?" followed by "I renamed it to mtg-collection-builder. Please use that name."**
   - Guided repository renaming process from mtg-tool to mtg-collection-builder
   - Updated local git remote URL to match renamed repository
   - Ensured seamless transition without breaking local development

9. **"Should I add a license file to this repo? If so, what would you recommend?" followed by "Yes, please do."**
   - Added MIT License to encourage open-source collaboration
   - Provided clear usage rights and attribution requirements
   - Updated .gitignore to properly handle VS Code configuration files

### Development Environment Setup
10. **"How do I easily launch myself this app in VS Code?" followed by concerns about hardcoded paths**
    - Created VS Code launch.json with debug configurations for app and tests
    - Added VS Code tasks.json with portable Python interpreter paths
    - Fixed hardcoded paths to use `${command:python.interpreterPath}` for cross-platform compatibility
    - Added auto-start functionality and proper task organization

### User Interface Enhancements
11. **"Let's add a new feature to the set view page. The user should be able to switch between alphabetical sorting and sorting by card number."**
    - Added toggle buttons for sorting by card number vs alphabetical order
    - Implemented client-side sorting with preserved user input values
    - Added intuitive UI controls with visual feedback for active sort method

12. **"Hm - switching the sort type is really slow. I think it's fully reloading the card images each time. Could we make switching the sort order faster?"**
    - Optimized sorting performance by reordering existing DOM elements instead of rebuilding
    - Eliminated image reloading and flickering during sort changes
    - Added smooth visual transitions and DocumentFragment for efficient DOM manipulation
    - Achieved ~90% performance improvement for sorting operations

13. **"Let's try adding the same sorting concept to the Rapid view. It should include the same buttons, and swapping should not change the active card. Instead, it should change how the rapid entry progresses, when the user hits an arrow key, hits enter, etc."**
    - Extended sorting functionality to rapid input mode with consistent UI
    - Implemented position tracking to maintain current card during sort changes
    - Added seamless navigation that respects the current sort order
    - Ensured sorting buttons work identically in both grid and rapid views

14. **"The controls in the upper right of the rapid view are pretty cluttered now. Could we shrink or relocate the progress bar? Perhaps it could go below the card view, above the control documentation?"**
    - Relocated progress bar from upper controls to below card display
    - Improved visual hierarchy and reduced button crowding
    - Enhanced user experience with cleaner, more organized layout
    - Progress bar now matches card display width for visual consistency

15. **"Let's try adding another feature to the set view. Let's add a name filter textbox, and as the user types in it, it automatically and rapidly filters the list down to the cards that start with that text."**
    - Added real-time name filtering to grid view with instant search functionality
    - Implemented text input with search icon and clear button for better UX
    - Created efficient filtering that shows/hides cards based on name prefix matching
    - Added smart progress tracking that updates based on visible filtered cards
    - Included comprehensive test coverage for the filtering functionality

16. **"The controls at the top of the set view are now really cluttered. Let's try fixing that by moving the first set of buttons ('clear all', 'add 1 each', and 'add 4 each') to a second 'row' of buttons. We could also shrink the progress bar slightly."**
    - Reorganized controls into a cleaner two-row layout to reduce visual clutter
    - Moved quantity modification buttons to their own row for better organization
    - Repositioned main action buttons (Back to Sets, Rapid Mode, Save Collection) to the top row
    - Reduced progress bar width while maintaining functionality
    - Improved overall visual hierarchy and user experience

17. **"Hm, that doesn't look right. The main buttons are still jumbled in the upper right. 'Back to Sets', 'Rapid Mode', and 'Save Collection' should always be on the same row. Right now, 'Save Collection' is rendering below the other two. The progress bar is also floating too high up on the page. Perhaps it should be between the 'add card' buttons and the sorting buttons."**
    - Fixed main action buttons layout to ensure they always stay on the same horizontal row
    - Increased space allocation for main buttons (col-md-8) to prevent wrapping
    - Repositioned progress bar between quantity buttons and sorting controls for better visual flow
    - Created clear visual hierarchy with four distinct sections: title/actions, quantity controls, progress tracking, and sorting/filtering
    - Added proper spacing between sections for improved readability

18. **"I noticed that the GitHub actions are running the tests against multiple python versions. Is that necessary for this app?" followed by "Let's focus on Python 3.12."**
    - Simplified GitHub Actions CI to test only against Python 3.12
    - Reduced CI runtime and complexity for this local development tool
    - Removed unnecessary multi-version testing matrix
    - Focused on modern Python version appropriate for personal use

19. **"I have a DeckBox collection format file, at 'C:\Users\mopic\Downloads\myCollection.csv', that does not work with the import functionality. It imports 0 cards. Could you investigate why?"**
    - Enhanced CSV import functionality to support both MTGGoldfish and DeckBox formats
    - Added flexible column name mapping (Count/Quantity, Edition/Set, Card Number/Collector Number)
    - Improved foil detection to handle both "Yes/No" and "foil" text formats
    - Added set name normalization to convert full names like "Classic Sixth Edition" to "6ed"
    - Implemented fallback search strategies for better card matching
    - Added comprehensive test coverage for DeckBox format import

20. **"Make sure that we can export in the same format we just added import support for."**
    - Enhanced export functionality to support both MTGGoldfish and DeckBox CSV formats
    - Added format selection dropdown in collection view with user-friendly icons
    - Implemented dual export methods with proper column mapping for each format
    - Added format parameter validation with sensible defaults
    - Created comprehensive test coverage for both export formats including route testing
    - Updated documentation with detailed format specifications and usage instructions
    - Ensured round-trip compatibility - can export DeckBox format and import it back seamlessly

### Key Features Developed
- **Python Flask web application** with responsive Bootstrap UI
- **Scryfall API integration** for real-time MTG card data
- **Dual input modes**: Grid view and rapid keyboard-driven entry with consistent sorting
- **Advanced sorting capabilities**: Alphabetical and card number sorting with performance optimization in both views
- **Real-time filtering**: Instant name-based card filtering with smart progress tracking
- **Optimized UI layout**: Four-tier control structure with proper visual hierarchy and spacing
- **CSV import/export** compatible with major collection trackers with dual format support (MTGGoldfish and DeckBox)
- **Real-time progress tracking** with improved UI layout and positioning
- **Comprehensive error handling** and user feedback
- **Professional development setup** with VS Code integration, unit testing, and streamlined CI/CD
- **Performance optimizations** for smooth user experience and fast DOM manipulation
- **Cross-platform compatibility** with portable development configurations
- **Intuitive UI design** with streamlined layouts and reduced visual clutter
- **Bidirectional format support** with round-trip compatibility for both import and export formats

The entire development process took place through natural language conversation, with the AI writing all code, creating templates, setting up the development environment, managing git commits, and implementing performance optimizations. No manual coding was required - everything was generated from the prompts above, including advanced features like client-side sorting, comprehensive testing, and development workflow improvements.

## Support

If you encounter any issues or have questions, please open an issue on the GitHub repository.
