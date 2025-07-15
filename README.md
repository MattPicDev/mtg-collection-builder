# MTG Collection Tool

A web-based tool for managing your Magic: The Gathering card collection. This tool provides a streamlined workflow for entering your collection set by set and exports to CSV format compatible with popular collection tracking sites like MTGGoldfish and Deckbox.

## Features

- **Set-by-set collection entry**: Browse MTG sets and quickly enter card quantities
- **Rapid input mode**: Keyboard-driven interface for lightning-fast collection entry
- **Scryfall API integration**: Automatically fetches card data and images
- **CSV export/import**: Compatible with MTGGoldfish, Deckbox, and other collection trackers
- **Collection import**: Upload existing CSV collections to quickly populate your data
- **Responsive web interface**: Works on desktop and mobile devices
- **Real-time progress tracking**: See your progress as you add cards
- **Search and filter**: Quickly find specific sets or cards
- **Foil tracking**: Track both regular and foil versions of cards
- **Collection management**: Clear, replace, or merge collections

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
   - **Grid View**: See all cards at once with individual quantity inputs
   - **Rapid Mode**: Lightning-fast keyboard-driven entry, one card at a time

5. **Enter quantities** for each card you own:
   - **Grid View**: Use the number inputs and foil checkboxes
   - **Rapid Mode**: Type numbers, press Space for foil, Enter to save and continue

6. **Save your collection** when finished with a set

6. **Import existing collections** (optional):
   - Go to the Import page
   - Upload a CSV file in the supported format
   - Choose whether to replace or add to your existing collection

7. **Export to CSV** from the collection page when ready

## Keyboard Shortcuts

### Grid View
- **Ctrl+S**: Save collection
- **Enter**: Move to next card input field
- **Search boxes**: Filter sets and collection in real-time

### Rapid Mode
- **Type numbers**: Set quantity (automatically focused)
- **Space**: Toggle foil status
- **Enter**: Save current card and move to next
- **Arrow Keys**: Navigate between cards manually
- **Escape**: Clear current input
- **Ctrl+S**: Save entire collection and finish

## CSV Import/Export Format

The CSV format includes the following columns:
- Name
- Set (3-letter code)
- Collector Number
- Quantity
- Foil (Yes/No)
- Condition
- Language

This format is compatible with:
- MTGGoldfish
- Deckbox
- Most other collection tracking sites

### Import Features
- **Smart card lookup**: Uses Scryfall API to verify card details
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

### Key Features Developed
- **Python Flask web application** with responsive Bootstrap UI
- **Scryfall API integration** for real-time MTG card data
- **Dual input modes**: Grid view and rapid keyboard-driven entry
- **CSV import/export** compatible with major collection trackers
- **Real-time progress tracking** and collection management
- **Comprehensive error handling** and user feedback

The entire development process took place through natural language conversation, with the AI writing all code, creating templates, setting up the development environment, and managing git commits. No manual coding was required - everything was generated from the prompts above.

## Support

If you encounter any issues or have questions, please open an issue on the GitHub repository.
