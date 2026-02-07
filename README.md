# WB ExactMatch Total Parser

[Русский](#русский) | [English](#english)

---

## Русский

Кроссплатформенное десктопное приложение для парсинга данных поиска Wildberries. Приложение загружает Excel файлы, очищает данные на основе стоп-категорий и стоп-слов, и получает метрики "total" из внутреннего API Wildberries для уникальных поисковых запросов.

### Возможности

- **Обработка Excel**: Загрузка и парсинг `.xlsx` файлов с автоматическим определением листов/заголовков
- **Очистка данных**: 
  - Фильтрация по стоп-категориям (регистронезависимое сопоставление слов)
  - Фильтрация по стоп-словам (правило сопоставления начала токена)
  - Удаление запросов, состоящих только из цифр
- **Интеграция с API Wildberries**: 
  - Асинхронная/параллельная обработка с настраиваемым количеством одновременных запросов
  - Стратегия повторных попыток с экспоненциальной задержкой и джиттером
  - Соблюдение ограничений скорости (заголовок Retry-After)
- **Кэширование**: Кэш на основе SQLite для избежания повторной загрузки
- **Контрольные точки**: Возобновление прерванной обработки
- **GUI**: Удобный интерфейс PySide6 с мониторингом прогресса в реальном времени
- **Экспорт**: Вывод в CSV с кодировкой UTF-8-SIG

### Требования

- Python 3.10 или выше
- См. `requirements.txt` для зависимостей

### Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd wb_parser
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv

# В Windows:
venv\Scripts\activate

# В macOS/Linux:
source venv/bin/activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

### Использование

#### GUI приложение

Запустите десктопное приложение:

```bash
python main.py
```

#### Рабочий процесс

1. **Выбор файлов**:
   - Выберите ваш Excel файл (`.xlsx`)
   - Укажите файл стоп-категорий (`1stop.txt`)
   - Укажите файл стоп-слов (`2stop.txt`)

2. **Загрузка и очистка**:
   - Нажмите "Загрузить и очистить данные"
   - Просмотрите предпросмотр данных с уникальными запросами

3. **Настройка параметров**:
   - **Параллельность**: Количество параллельных запросов (1-20, по умолчанию: 4)
   - **Задержки**: Диапазон случайной задержки между запросами (по умолчанию: 0.5-1.5с)
   - **Таймаут**: Таймаут запроса в секундах (по умолчанию: 20с)
   - **Макс. попыток**: Максимальное количество повторных попыток для неудачных запросов (по умолчанию: 5)
   - **Опции**: Кэш, Принудительное обновление, Контрольные точки

4. **Запуск парсинга**:
   - Нажмите "Начать парсинг"
   - Отслеживайте прогресс в реальном времени
   - Используйте элементы управления Пауза/Возобновить/Остановить по необходимости

5. **Экспорт результатов**:
   - Нажмите "Экспорт CSV" по завершении
   - Результаты сохранены со столбцами:
     - Поисковый запрос
     - Количество запросов
     - total (результат API)
     - status (success/failed/cached)
     - fetched_at (временная метка)
     - error_message (если неудачно)

#### Использование через командную строку

Вы также можете использовать модули программно:

```python
import asyncio
from src.models.config import ParserConfig, CleaningConfig
from src.io.excel_reader import ExcelReader
from src.clean.cleaner import DataCleaner
from src.core.pipeline import ParserPipeline

# Загрузка и очистка данных
config = CleaningConfig(
    stop_categories_file="data/1stop.txt",
    stop_words_file="data/2stop.txt"
)

reader = ExcelReader("data.xlsx")
df = reader.load()

cleaner = DataCleaner(config)
cleaned_df, removed_df = cleaner.clean(df)
queries = cleaner.extract_unique_queries(cleaned_df)

# Парсинг запросов
parser_config = ParserConfig(concurrency=4)
pipeline = ParserPipeline(parser_config)

results = asyncio.run(pipeline.process_queries(queries))

# Экспорт результатов
from src.io.csv_writer import CSVWriter
writer = CSVWriter("results.csv")
data = [r.to_dict() for r in results]
writer.write(data, ['Поисковый запрос', 'total', 'status', 'fetched_at'])
```

### Структура проекта

```
wb_parser/
├── src/
│   ├── io/              # Файловые операции (Excel, CSV, SQLite)
│   ├── clean/           # Логика очистки данных
│   ├── api/             # Клиент API Wildberries с повторными попытками
│   ├── core/            # Конвейер, кэш, контрольные точки
│   ├── ui/              # GUI компоненты (PySide6)
│   ├── models/          # Структуры данных
│   └── config/          # Профили конфигурации
├── tests/               # Модульные и интеграционные тесты
│   ├── unit/
│   └── integration/
├── data/                # Примеры стоп-файлов
├── main.py              # Точка входа приложения
├── requirements.txt     # Зависимости Python
└── README.md            # Этот файл
```

### Конфигурационные файлы

#### Стоп-категории (1stop.txt)

Содержит категории для фильтрации (регистронезависимое сопоставление слов):

```
# Комментарии начинаются с #
алкоголь
сигареты
табак
```

#### Стоп-слова (2stop.txt)

Содержит стоп-слова с сопоставлением начала токена:

```
# Сопоставление начала токена: "термо" соответствует "термокружка" 
# но не "гидротермокружка"
термо
био
эко
```

### Детали API

Приложение использует внутренний API Wildberries:

```
https://www.wildberries.ru/__internal/search/exactmatch/ru/common/v18/search
```

Параметры:
- `query`: Строка поискового запроса
- `appType`: 1
- `curr`: rub
- `dest`: -1257786
- `resultset`: catalog
- `sort`: popular
- `spp`: 30
- `suppressSpellcheck`: false

Приложение извлекает поле `"total"` (целое число) верхнего уровня из JSON-ответа.

#### Ограничение скорости и повторные попытки

- **Экспоненциальная задержка**: Базовая задержка × (2 ^ попытка) с джиттером ±25%
- **Условия повторной попытки**: HTTP 429, ошибки 5xx, таймауты
- **Заголовок Retry-After**: Соблюдается при предоставлении сервером
- **Макс. попыток**: Настраивается (по умолчанию: 5)

### Кэширование

Результаты кэшируются в базе данных SQLite (`wb_cache.db`) для избежания повторной загрузки:

- **Структура кэша**: Запрос → (total, статус, временная метка, ошибка)
- **Принудительное обновление**: Опция обхода кэша
- **Статистика кэша**: Просмотр кэшированных и свежих результатов

### Контрольные точки

Прогресс сохраняется периодически (по умолчанию: каждые 50 запросов) в `wb_checkpoint.json`:

- **Возобновление**: Продолжить с места остановки после прерывания
- **Автоматически**: Сохраняет завершенные запросы и результаты
- **Ручное управление**: Очистка контрольной точки для начала заново

### Тестирование

Запуск тестов:

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=src --cov-report=html

# Конкретный тестовый файл
pytest tests/unit/test_stop_words.py
```

### Разработка

#### Качество кода

Форматирование кода:
```bash
black src/ tests/
```

Линтинг кода:
```bash
ruff check src/ tests/
```

Проверка типов:
```bash
mypy src/
```

#### Архитектура

Приложение следует модульной архитектуре:

1. **Слой IO**: Обрабатывает все файловые операции (Excel, CSV, SQLite)
2. **Слой очистки**: Логика очистки и фильтрации данных
3. **Слой API**: Асинхронный HTTP-клиент с повторными попытками/задержкой
4. **Основной слой**: Главный конвейер обработки с кэшированием/контрольными точками
5. **Слой UI**: GUI PySide6 с фоновыми рабочими процессами
6. **Слой моделей**: Структуры данных и конфигурация
7. **Слой конфигурации**: Управление конфигурацией и профили

#### Ключевые шаблоны проектирования

- **Async/Await**: Для одновременных API-запросов
- **Рабочий поток**: Неблокирующий GUI с фоновой обработкой
- **Паттерн стратегии**: Настраиваемые стратегии повторных попыток
- **Паттерн репозитория**: Абстракция кэша SQLite
- **Паттерн наблюдателя**: Обратные вызовы прогресса и сигналы

### Устранение неполадок

#### Проблемы с Excel файлами

- Убедитесь, что файл в формате `.xlsx` (не `.xls`)
- Проверьте наличие листа "Детальная информация"
- Проверьте столбцы: "Поисковый запрос", "Категория", "Количество запросов"

#### Проблемы с API

- **Ограничение скорости**: Увеличьте задержки или уменьшите параллельность
- **Таймауты**: Увеличьте значение таймаута в настройках
- **Ошибки подключения**: Проверьте интернет-соединение

#### Производительность

- **Медленная обработка**: Увеличьте параллельность (до 10-15)
- **Слишком много ошибок**: Уменьшите параллельность, увеличьте задержки
- **Проблемы с памятью**: Обрабатывайте партиями, уменьшите интервал контрольных точек

### Будущие улучшения

Планируемые функции:

- [ ] История запросов и аналитика
- [ ] Предложения и автозаполнение
- [ ] Фильтрация по категориям
- [ ] Расширенные опции фильтрации
- [ ] Графики и визуализации
- [ ] Экспорт в PostgreSQL
- [ ] Профили скорости
- [ ] Поддержка нескольких языков
- [ ] Поддержка прокси
- [ ] Пользовательские конечные точки API

### Лицензия

MIT License

### Вклад

Приветствуются вклады! Пожалуйста:

1. Сделайте форк репозитория
2. Создайте ветку функций
3. Внесите изменения с тестами
4. Запустите проверки качества кода
5. Отправьте pull request

### Поддержка

Для вопросов и проблем:

- **Issues**: GitHub Issues
- **Документация**: Этот README
- **Логи**: Проверьте `logs/wb_parser.log`

### Благодарности

Разработано с использованием:
- Python 3.10+
- PySide6 (Qt для Python)
- pandas & openpyxl
- aiohttp
- SQLite

---

**Версия**: 1.0.0  
**Последнее обновление**: 2024

---

## English

A cross-platform desktop application for parsing Wildberries search data. The application loads Excel files, cleans data based on stop categories and stop words, and fetches "total" metrics from the Wildberries internal API for unique search queries.

### Features

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

### Requirements

- Python 3.10 or higher
- See `requirements.txt` for dependencies

### Installation

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

### Usage

#### GUI Application

Run the desktop application:

```bash
python main.py
```

#### Workflow

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

#### Command Line Usage

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

### Project Structure

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

### Configuration Files

#### Stop Categories (1stop.txt)

Contains categories to filter out (case-insensitive word matching):

```
# Comments start with #
алкоголь
сигареты
табак
```

#### Stop Words (2stop.txt)

Contains stop words with token-start matching:

```
# Token-start matching: "термо" matches "термокружка" 
# but not "гидротермокружка"
термо
био
эко
```

### API Details

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

#### Rate Limiting & Retry

- **Exponential Backoff**: Base delay × (2 ^ attempt) with ±25% jitter
- **Retry Conditions**: HTTP 429, 5xx errors, timeouts
- **Retry-After Header**: Respected when provided by server
- **Max Retries**: Configurable (default: 5)

### Caching

Results are cached in SQLite database (`wb_cache.db`) to avoid re-fetching:

- **Cache Structure**: Query → (total, status, timestamp, error)
- **Force Refresh**: Option to bypass cache
- **Cache Stats**: View cached vs fresh results

### Checkpointing

Progress is saved periodically (default: every 50 queries) to `wb_checkpoint.json`:

- **Resume**: Continue from where you left off after interruption
- **Automatic**: Saves completed queries and results
- **Manual Control**: Clear checkpoint to start fresh

### Testing

Run tests:

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/unit/test_stop_words.py
```

### Development

#### Code Quality

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

#### Architecture

The application follows a modular architecture:

1. **IO Layer**: Handles all file operations (Excel, CSV, SQLite)
2. **Clean Layer**: Data cleaning and filtering logic
3. **API Layer**: Async HTTP client with retry/backoff
4. **Core Layer**: Main processing pipeline with caching/checkpointing
5. **UI Layer**: PySide6 GUI with background workers
6. **Models Layer**: Data structures and configuration
7. **Config Layer**: Configuration management and profiles

#### Key Design Patterns

- **Async/Await**: For concurrent API requests
- **Worker Thread**: Non-blocking GUI with background processing
- **Strategy Pattern**: Configurable retry strategies
- **Repository Pattern**: SQLite cache abstraction
- **Observer Pattern**: Progress callbacks and signals

### Troubleshooting

#### Excel File Issues

- Ensure file is `.xlsx` format (not `.xls`)
- Check that sheet "Детальная информация" exists
- Verify columns: "Поисковый запрос", "Категория", "Количество запросов"

#### API Issues

- **Rate Limiting**: Increase delays or reduce concurrency
- **Timeouts**: Increase timeout value in settings
- **Connection Errors**: Check internet connection

#### Performance

- **Slow Processing**: Increase concurrency (up to 10-15)
- **Too Many Errors**: Decrease concurrency, increase delays
- **Memory Issues**: Process in batches, reduce checkpoint interval

### Future Enhancements

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

### License

MIT License

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run code quality checks
5. Submit a pull request

### Support

For issues and questions:

- **Issues**: GitHub Issues
- **Documentation**: This README
- **Logs**: Check `logs/wb_parser.log`

### Credits

Developed with:
- Python 3.10+
- PySide6 (Qt for Python)
- pandas & openpyxl
- aiohttp
- SQLite

---

**Version**: 1.0.0  
**Last Updated**: 2024
