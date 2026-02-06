# WB ExactMatch Total Parser

A cross-platform desktop application for parsing Wildberries search data. The application loads Excel files, cleans data based on stop categories and stop words, and fetches "total" metrics from the Wildberries internal API for unique search queries.

## Features

- **Excel Processing**: Load and parse `.xlsx` files with automatic sheet/header detection
- **Data Cleaning**: 
  - Filter by stop categories (case-insensitive word matching)
  - Filter by stop words (token-start matching rule)
  - Remove numeric-only queries
- **Wildberries API Integration**: 
  - Async/parallel processing with configurable concurrency
  - Exponential backoff retry strategy with jitter
  - Rate limiting respect (Retry-After header)
- **Caching**: SQLite-based cache to avoid re-fetching
- **Checkpointing**: Resume interrupted processing
- **GUI**: User-friendly PySide6 interface with real-time progress monitoring
- **Export**: CSV output with UTF-8-SIG encoding

## Requirements

- Python 3.10 or higher
- See `requirements.txt` for dependencies

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd wb_parser
```

2. Create a virtual environment:
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### GUI Application

Run the desktop application:

```bash
python main.py
```

### Workflow

1. **Select Files**:
   - Choose your Excel file (`.xlsx`)
   - Specify stop categories file (`1stop.txt`)
   - Specify stop words file (`2stop.txt`)

2. **Load and Clean**:
   - Click "Load and Clean Data"
   - Review the data preview showing unique queries

3. **Configure Settings**:
   - **Concurrency**: Number of parallel requests (1-20, default: 4)
   - **Delays**: Random delay range between requests (default: 0.5-1.5s)
   - **Timeout**: Request timeout in seconds (default: 20s)
   - **Max Retries**: Maximum retry attempts for failed requests (default: 5)
   - **Options**: Cache, Force Refresh, Checkpoints

4. **Start Parsing**:
   - Click "Start Parsing"
   - Monitor progress in real-time
   - Use Pause/Resume/Stop controls as needed

5. **Export Results**:
   - Click "Export CSV" when complete
   - Results saved with columns:
     - Поисковый запрос (Search Query)
     - Количество запросов (Query Count)
     - total (API result)
     - status (success/failed/cached)
     - fetched_at (timestamp)
     - error_message (if failed)

### Command Line Usage

You can also use the modules programmatically:

```python
import asyncio
from src.models.config import ParserConfig, CleaningConfig
from src.io.excel_reader import ExcelReader
from src.clean.cleaner import DataCleaner
from src.core.pipeline import ParserPipeline

# Load and clean data
config = CleaningConfig(
    stop_categories_file="data/1stop.txt",
    stop_words_file="data/2stop.txt"
)

reader = ExcelReader("data.xlsx")
df = reader.load()

cleaner = DataCleaner(config)
cleaned_df, removed_df = cleaner.clean(df)
queries = cleaner.extract_unique_queries(cleaned_df)

# Parse queries
parser_config = ParserConfig(concurrency=4)
pipeline = ParserPipeline(parser_config)

results = asyncio.run(pipeline.process_queries(queries))

# Export results
from src.io.csv_writer import CSVWriter
writer = CSVWriter("results.csv")
data = [r.to_dict() for r in results]
writer.write(data, ['Поисковый запрос', 'total', 'status', 'fetched_at'])
```

## Project Structure

```
wb_parser/
├── src/
│   ├── io/              # File operations (Excel, CSV, SQLite)
│   ├── clean/           # Data cleaning logic
│   ├── api/             # Wildberries API client with retry
│   ├── core/            # Pipeline, cache, checkpoints
│   ├── ui/              # GUI components (PySide6)
│   ├── models/          # Data structures
│   └── config/          # Configuration profiles
├── tests/               # Unit and integration tests
│   ├── unit/
│   └── integration/
├── data/                # Example stop files
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Configuration Files

### Stop Categories (1stop.txt)

Contains categories to filter out (case-insensitive word matching):

```
# Comments start with #
алкоголь
сигареты
табак
```

### Stop Words (2stop.txt)

Contains stop words with token-start matching:

```
# Token-start matching: "термо" matches "термокружка" 
# but not "гидротермокружка"
термо
био
эко
```

## API Details

The application uses the Wildberries internal API:

```
https://www.wildberries.ru/__internal/search/exactmatch/ru/common/v18/search
```

Parameters:
- `query`: Search query string
- `appType`: 1
- `curr`: rub
- `dest`: -1257786
- `resultset`: catalog
- `sort`: popular
- `spp`: 30
- `suppressSpellcheck`: false

The application extracts the top-level `"total"` field (integer) from the JSON response.

### Rate Limiting & Retry

- **Exponential Backoff**: Base delay × (2 ^ attempt) with ±25% jitter
- **Retry Conditions**: HTTP 429, 5xx errors, timeouts
- **Retry-After Header**: Respected when provided by server
- **Max Retries**: Configurable (default: 5)

## Caching

Results are cached in SQLite database (`wb_cache.db`) to avoid re-fetching:

- **Cache Structure**: Query → (total, status, timestamp, error)
- **Force Refresh**: Option to bypass cache
- **Cache Stats**: View cached vs fresh results

## Checkpointing

Progress is saved periodically (default: every 50 queries) to `wb_checkpoint.json`:

- **Resume**: Continue from where you left off after interruption
- **Automatic**: Saves completed queries and results
- **Manual Control**: Clear checkpoint to start fresh

## Testing

Run tests:

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/unit/test_stop_words.py
```

## Development

### Code Quality

Format code:
```bash
black src/ tests/
```

Lint code:
```bash
ruff check src/ tests/
```

Type check:
```bash
mypy src/
```

### Architecture

The application follows a modular architecture:

1. **IO Layer**: Handles all file operations (Excel, CSV, SQLite)
2. **Clean Layer**: Data cleaning and filtering logic
3. **API Layer**: Async HTTP client with retry/backoff
4. **Core Layer**: Main processing pipeline with caching/checkpointing
5. **UI Layer**: PySide6 GUI with background workers
6. **Models Layer**: Data structures and configuration
7. **Config Layer**: Configuration management and profiles

### Key Design Patterns

- **Async/Await**: For concurrent API requests
- **Worker Thread**: Non-blocking GUI with background processing
- **Strategy Pattern**: Configurable retry strategies
- **Repository Pattern**: SQLite cache abstraction
- **Observer Pattern**: Progress callbacks and signals

## Troubleshooting

### Excel File Issues

- Ensure file is `.xlsx` format (not `.xls`)
- Check that sheet "Детальная информация" exists
- Verify columns: "Поисковый запрос", "Категория", "Количество запросов"

### API Issues

- **Rate Limiting**: Increase delays or reduce concurrency
- **Timeouts**: Increase timeout value in settings
- **Connection Errors**: Check internet connection

### Performance

- **Slow Processing**: Increase concurrency (up to 10-15)
- **Too Many Errors**: Decrease concurrency, increase delays
- **Memory Issues**: Process in batches, reduce checkpoint interval

## Future Enhancements

Planned features:

- [ ] Query history and analytics
- [ ] Suggestions and autocomplete
- [ ] Category filtering
- [ ] Advanced filtering options
- [ ] Charts and visualizations
- [ ] PostgreSQL export
- [ ] Speed profiles
- [ ] Multi-language support
- [ ] Proxy support
- [ ] Custom API endpoints

## License

MIT License

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run code quality checks
5. Submit a pull request

## Support

For issues and questions:

- **Issues**: GitHub Issues
- **Documentation**: This README
- **Logs**: Check `logs/wb_parser.log`

## Credits

Developed with:
- Python 3.10+
- PySide6 (Qt for Python)
- pandas & openpyxl
- aiohttp
- SQLite

---

**Version**: 1.0.0  
**Last Updated**: 2024