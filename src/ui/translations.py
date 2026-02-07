"""UI translations for English and Russian."""

TRANSLATIONS = {
    "en": {
        # Window title
        "app_title": "WB ExactMatch Total Parser",
        # File section
        "file_selection": "File Selection",
        "excel_file": "Excel File:",
        "excel_placeholder": "Select Excel file (.xlsx)",
        "browse": "Browse...",
        "stop_categories": "Stop Categories (1stop.txt):",
        "stop_words": "Stop Words (2stop.txt):",
        "load_and_clean": "Load and Clean Data",
        # Parser settings
        "parser_settings": "Parser Settings",
        "concurrency": "Concurrency:",
        "min_delay": "Min Delay (s):",
        "max_delay": "Max Delay (s):",
        "timeout": "Timeout (s):",
        "max_retries": "Max Retries:",
        "use_cache": "Use Cache",
        "force_refresh": "Force Refresh",
        "enable_checkpoints": "Enable Checkpoints",
        # Controls
        "controls": "Controls",
        "start_parsing": "Start Parsing",
        "pause": "Pause",
        "resume": "Resume",
        "stop": "Stop",
        "export_csv": "Export CSV",
        # Progress
        "progress": "Progress",
        "total": "Total",
        "completed": "Completed",
        "success": "Success",
        "failed": "Failed",
        "cached": "Cached",
        "speed": "Speed",
        # Preview
        "data_preview": "Data Preview",
        "preview_query": "Query",
        "preview_count": "Count",
        "preview_status": "Status",
        "preview_pending": "Pending",
        # Log
        "log": "Log",
        # Tabs
        "tab_parsing": "Parsing",
        "tab_settings": "Settings",
        # Settings tab
        "app_settings": "Application Settings",
        "language": "Language:",
        "language_en": "English",
        "language_ru": "Russian (Русский)",
        "show_tooltips": "Show Tooltips",
        # Tooltips
        "tooltip_concurrency": "Number of simultaneous requests (1-20)",
        "tooltip_min_delay": "Minimum delay between requests in seconds",
        "tooltip_max_delay": "Maximum delay between requests in seconds",
        "tooltip_timeout": "Request timeout in seconds",
        "tooltip_max_retries": "Maximum number of retry attempts for failed requests",
        "tooltip_use_cache": "Use local database cache to avoid re-fetching data",
        "tooltip_force_refresh": "Force refresh cached data (ignore cache)",
        "tooltip_enable_checkpoints": "Save progress periodically to resume later",
        "tooltip_show_tooltips": "Enable or disable tooltips for all controls",
        # Messages
        "msg_select_excel": "Please select an Excel file",
        "msg_loading": "Loading Excel file...",
        "msg_loaded": "Loaded {count} rows",
        "msg_cleaning": "Cleaning data...",
        "msg_cleaned": "Cleaned: {kept} kept, {removed} removed",
        "msg_unique_queries": "Found {count} unique queries",
        "msg_no_queries": "No queries to process",
        "msg_starting": "Starting parsing...",
        "msg_paused": "Paused",
        "msg_resumed": "Resumed",
        "msg_stopping": "Stopping...",
        "msg_complete": "Parsing complete: {count} results",
        "msg_no_results": "No results to export",
        "msg_exporting": "Exporting results...",
        "msg_exported": "Exported to {path}",
        "msg_exported_removed": "Exported removed rows to {path}",
        "msg_export_error": "Export error: {error}",
        "msg_saved_categories": "Saved removed categories to {path}",
        "msg_saved_stop_words": "Saved removed stop words to {path}",
        # Dialog titles
        "dialog_error": "Error",
        "dialog_warning": "Warning",
        "dialog_success": "Success",
        "dialog_complete": "Complete",
        "dialog_config_error": "Configuration Error",
        "dialog_complete_msg": "Parsing complete!\n\nTotal: {total}\nSuccess: {success}\nFailed: {failed}",
        "dialog_export_success": "Results exported successfully!",
        "dialog_select_excel_title": "Select Excel File",
        "dialog_select_stop_cat_title": "Select Stop Categories File",
        "dialog_select_stop_words_title": "Select Stop Words File",
        "dialog_save_csv_title": "Save CSV File",
        "dialog_excel_filter": "Excel Files (*.xlsx *.xls)",
        "dialog_text_filter": "Text Files (*.txt)",
        "dialog_csv_filter": "CSV Files (*.csv)",
    },
    "ru": {
        # Window title
        "app_title": "WB ExactMatch Total Parser",
        # File section
        "file_selection": "Выбор файлов",
        "excel_file": "Excel файл:",
        "excel_placeholder": "Выберите Excel файл (.xlsx)",
        "browse": "Обзор...",
        "stop_categories": "Стоп-категории (1stop.txt):",
        "stop_words": "Стоп-слова (2stop.txt):",
        "load_and_clean": "Загрузить и очистить данные",
        # Parser settings
        "parser_settings": "Настройки парсера",
        "concurrency": "Параллельность:",
        "min_delay": "Мин. задержка (сек):",
        "max_delay": "Макс. задержка (сек):",
        "timeout": "Таймаут (сек):",
        "max_retries": "Макс. попыток:",
        "use_cache": "Использовать кэш",
        "force_refresh": "Принудительное обновление",
        "enable_checkpoints": "Включить контрольные точки",
        # Controls
        "controls": "Управление",
        "start_parsing": "Начать парсинг",
        "pause": "Пауза",
        "resume": "Возобновить",
        "stop": "Остановить",
        "export_csv": "Экспорт CSV",
        # Progress
        "progress": "Прогресс",
        "total": "Всего",
        "completed": "Завершено",
        "success": "Успешно",
        "failed": "Ошибки",
        "cached": "Из кэша",
        "speed": "Скорость",
        # Preview
        "data_preview": "Предпросмотр данных",
        "preview_query": "Запрос",
        "preview_count": "Количество",
        "preview_status": "Статус",
        "preview_pending": "Ожидание",
        # Log
        "log": "Лог",
        # Tabs
        "tab_parsing": "Парсинг",
        "tab_settings": "Настройки",
        # Settings tab
        "app_settings": "Настройки приложения",
        "language": "Язык:",
        "language_en": "English",
        "language_ru": "Русский",
        "show_tooltips": "Показывать подсказки",
        # Tooltips
        "tooltip_concurrency": "Количество одновременных запросов (1-20)",
        "tooltip_min_delay": "Минимальная задержка между запросами в секундах",
        "tooltip_max_delay": "Максимальная задержка между запросами в секундах",
        "tooltip_timeout": "Таймаут запроса в секундах",
        "tooltip_max_retries": "Максимальное количество повторных попыток при ошибках",
        "tooltip_use_cache": "Использовать локальный кэш для избежания повторной загрузки",
        "tooltip_force_refresh": "Принудительно обновить кэшированные данные (игнорировать кэш)",
        "tooltip_enable_checkpoints": "Периодически сохранять прогресс для возможности продолжения",
        "tooltip_show_tooltips": "Включить или отключить подсказки для всех элементов",
        # Messages
        "msg_select_excel": "Пожалуйста, выберите Excel файл",
        "msg_loading": "Загрузка Excel файла...",
        "msg_loaded": "Загружено {count} строк",
        "msg_cleaning": "Очистка данных...",
        "msg_cleaned": "Очищено: {kept} оставлено, {removed} удалено",
        "msg_unique_queries": "Найдено {count} уникальных запросов",
        "msg_no_queries": "Нет запросов для обработки",
        "msg_starting": "Начало парсинга...",
        "msg_paused": "Приостановлено",
        "msg_resumed": "Возобновлено",
        "msg_stopping": "Остановка...",
        "msg_complete": "Парсинг завершен: {count} результатов",
        "msg_no_results": "Нет результатов для экспорта",
        "msg_exporting": "Экспорт результатов...",
        "msg_exported": "Экспортировано в {path}",
        "msg_exported_removed": "Удаленные строки экспортированы в {path}",
        "msg_export_error": "Ошибка экспорта: {error}",
        "msg_saved_categories": "Удаленные категории сохранены в {path}",
        "msg_saved_stop_words": "Удаленные стоп-слова сохранены в {path}",
        # Dialog titles
        "dialog_error": "Ошибка",
        "dialog_warning": "Предупреждение",
        "dialog_success": "Успех",
        "dialog_complete": "Завершено",
        "dialog_config_error": "Ошибка конфигурации",
        "dialog_complete_msg": "Парсинг завершен!\n\nВсего: {total}\nУспешно: {success}\nОшибок: {failed}",
        "dialog_export_success": "Результаты успешно экспортированы!",
        "dialog_select_excel_title": "Выберите Excel файл",
        "dialog_select_stop_cat_title": "Выберите файл стоп-категорий",
        "dialog_select_stop_words_title": "Выберите файл стоп-слов",
        "dialog_save_csv_title": "Сохранить CSV файл",
        "dialog_excel_filter": "Excel файлы (*.xlsx *.xls)",
        "dialog_text_filter": "Текстовые файлы (*.txt)",
        "dialog_csv_filter": "CSV файлы (*.csv)",
    },
}


def get_text(key: str, language: str = "ru", **kwargs) -> str:
    """
    Get translated text for a key.

    Args:
        key: Translation key
        language: Language code ("en" or "ru")
        **kwargs: Format arguments for the text

    Returns:
        Translated and formatted text, or the key itself if not found
    """
    lang_dict = TRANSLATIONS.get(language, TRANSLATIONS["ru"])
    text = lang_dict.get(key, key)

    # Format with kwargs if provided
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass

    return text
