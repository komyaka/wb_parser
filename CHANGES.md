# Changes Summary

## Problem 1: Rate Limiting (HTTP 498) Thundering Herd Fix

### Root Cause
When the Wildberries API returns HTTP 498 (rate limited), multiple concurrent requests all get rate-limited simultaneously. Each request then retries independently at nearly the same time, creating a "thundering herd" effect that causes continuous 498 errors.

### Solution
Implemented global rate-limiting coordination:

1. **Global Event Coordination** (`src/core/pipeline.py`)
   - Added `_rate_limit_event` (asyncio.Event) that starts SET (allowing requests)
   - Added `_rate_limit_lock` (asyncio.Lock) to prevent concurrent backoff attempts
   - Added `_consecutive_rate_limits` counter for exponential backoff tracking

2. **Exponential Backoff** (`src/core/pipeline.py`)
   - Implemented `_on_rate_limited()` callback method
   - Backoff sequence: 5s, 10s, 20s, 40s, 60s (max)
   - Configured via constants: `RATE_LIMIT_BASE_BACKOFF_SECONDS=5.0`, `RATE_LIMIT_MAX_BACKOFF_SECONDS=60.0`
   - Counter resets on successful requests

3. **Client Integration** (`src/api/client.py`)
   - Added `rate_limit_callback: Callable[[], Awaitable[None]] | None` parameter
   - Client invokes callback when HTTP 498/429 is received
   - Pipeline passes its `_on_rate_limited` method to client

4. **Request Coordination** (`src/core/pipeline.py`)
   - All requests wait on `_rate_limit_event` before making API calls
   - When rate limited, event is cleared, blocking ALL concurrent requests
   - After backoff, event is set, allowing requests to continue

### How It Works
```
Request 1 → 498 → callback() → clears event → waits 5s → sets event
Request 2 → waits on event →                          → continues
Request 3 → waits on event →                          → continues
```

### Testing
- All 85 existing tests pass
- Manual test verifies only 1 backoff occurs from 3 concurrent callbacks
- Manual test confirms event coordination works correctly

---

## Problem 2: Add Detailed Logging Checkbox

### Feature
Added UI checkbox to enable detailed DEBUG-level logging to file for troubleshooting.

### Implementation

1. **Settings Persistence** (`src/config/settings.py`)
   - Added `detailed_logging: bool = False` field
   - Loads/saves with existing settings in JSON format

2. **UI Components** (`src/ui/main_window.py`)
   - Added checkbox in Settings tab with "❓" tooltip
   - Checkbox state synced with settings
   - `_on_detailed_logging_changed()` handler saves state and applies logging
   - `_apply_detailed_logging()` manages logger configuration dynamically

3. **Translations** (`src/ui/translations.py`)
   - English: "Detailed Logging (save to file)" / "Enable detailed DEBUG-level logging to file for troubleshooting"
   - Russian: "Детальный лог (сохранение в файл)" / "Включить детальный DEBUG-уровень логирования в файл для диагностики"

4. **Startup Configuration** (`main.py`)
   - `setup_logging()` checks `detailed_logging` setting
   - Configures root logger to DEBUG level if enabled
   - Creates `logs/wb_parser_debug.log` file handler

5. **Dynamic Logging Management** (`src/ui/main_window.py`)
   - Uses `.resolve()` for reliable path comparison across symlinks/relative paths
   - Prevents duplicate file handlers
   - Properly closes handlers when disabling

### User Experience
- Toggle checkbox in Settings → immediately applies
- No restart required for logging changes
- Debug logs written to `logs/wb_parser_debug.log`
- Standard logs still go to `logs/wb_parser.log`

### Testing
- All settings tests updated to verify `detailed_logging` field
- Tests confirm default is `False`
- Tests verify persistence across save/load cycles
- Tests handle partial JSON data gracefully

---

## Code Quality Improvements

### Review Feedback Addressed
1. ✅ Used `collections.abc.Callable` and `Awaitable` (Python 3.9+ standard)
2. ✅ Proper type hint: `Callable[[], Awaitable[None]]` for async callback
3. ✅ Extracted magic numbers as module-level constants
4. ✅ Used `.resolve()` for reliable path comparison

### Type Safety
- All new parameters have proper type hints
- Async callback signature properly typed
- Path objects used consistently

### Maintainability
- Constants at module level for easy configuration
- Clear docstrings explain rate limiting logic
- Path handling uses modern `pathlib` patterns

---

## Files Modified

```
main.py                     (+22, -2)   - Startup logging configuration
src/api/client.py           (+9, -1)    - Rate limit callback parameter
src/config/settings.py      (+3)        - Detailed logging field
src/core/pipeline.py        (+44)       - Global rate limit coordination
src/ui/main_window.py       (+73)       - Detailed logging checkbox + handlers
src/ui/translations.py      (+4)        - New translation strings
tests/unit/test_settings.py (+8)        - Updated tests for new field
```

**Total**: 163 lines added, 3 lines removed across 7 files

---

## Verification Results

### Static Analysis
✅ Python syntax validation passed  
✅ Module imports successful  
✅ Type hints properly declared  

### Test Suite
✅ All 85 tests pass  
✅ Settings tests updated and passing  
✅ Integration tests still passing  

### Manual Testing
✅ Rate limit event coordination verified  
✅ Concurrent backoff prevention confirmed  
✅ API client callback integration tested  
✅ Detailed logging persistence validated  

---

## Backward Compatibility

### Configuration
- New `detailed_logging` field defaults to `False`
- Existing settings files load correctly
- Missing field in JSON falls back to default

### API
- `rate_limit_callback` is optional (defaults to `None`)
- Existing code without callback continues to work
- No breaking changes to public interfaces

### Behavior
- Rate limiting now coordinates globally (improvement, not breaking change)
- Logging level changes only when explicitly enabled
- All existing functionality preserved
