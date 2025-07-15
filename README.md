# MTG Collection Tool

A web-based tool for managing your Magic: The Gathering card collection. This tool provides a streamlined workflow for entering your collection set by set and exports to CSV format compatible with popular collection tracking sites like MTGGoldfish and Deckbox.

## Features

- **Set-by-set collection entry**: Browse MTG sets and quickly enter card quantities
- **Scryfall API integration**: Automatically fetches card data and images
- **CSV export**: Compatible with MTGGoldfish, Deckbox, and other collection trackers
- **Responsive web interface**: Works on desktop and mobile devices
- **Real-time progress tracking**: See your progress as you add cards
- **Search and filter**: Quickly find specific sets or cards
- **Foil tracking**: Track both regular and foil versions of cards

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

4. **Enter quantities** for each card you own:
   - Use the number inputs to set quantities
   - Check the "Foil" checkbox for foil versions
   - Use keyboard shortcuts for faster entry

5. **Save your collection** when finished with a set

6. **Export to CSV** from the collection page when ready

## Keyboard Shortcuts

- **Ctrl+S**: Save collection (on set view page)
- **Enter**: Move to next card input field
- **Search boxes**: Filter sets and collection in real-time

## CSV Export Format

The exported CSV includes the following columns:
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

## Support

If you encounter any issues or have questions, please open an issue on the GitHub repository.
