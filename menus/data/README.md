# Menu Data Management

## Overview
The UMass SmartDine Finder application now uses a **database-first** approach for menu data. All menu information is stored in the SQLite database and loaded dynamically.

## Data Flow

```
Scraped Data (JSON) → Import Script → Database → Django Views → Frontend
```

## Files

### Data Files
- `scraped_menus.json` - Raw scraped menu data from UMass Dining website
- `menus.json` - Legacy file (no longer used)

### Scripts
- `../../scripts/scrape_menus.py` - Web scraper to fetch menu data
- `../../scripts/import_to_db.py` - Import scraped data into database
- `../../scripts/verify_db_data.py` - Verify database contents

### Django Management Command
- `../../menus/management/commands/import_menus.py` - Django command to import data

## Usage

### 1. Scrape Latest Menu Data
```bash
cd /path/to/project
python3 scripts/scrape_menus.py
```

This will create/update `menus/data/scraped_menus.json` with the latest menu data.

**Important:** The scraper correctly handles weekends - Saturday and Sunday have NO breakfast service.

### 2. Import Data to Database
```bash
python3 scripts/import_to_db.py
```

This will:
- Clear existing dining hall data
- Import all menu data from `scraped_menus.json` into the database
- Display import statistics

### 3. Verify Database
```bash
python3 scripts/verify_db_data.py
```

This will display all dining halls and their menu item counts.

### 4. Alternative: Django Management Command
```bash
python manage.py import_menus --clear
```

This does the same as `import_to_db.py` but requires Django environment.

## Database Schema

### Table: `menus_dininghall`
- `id` (INTEGER PRIMARY KEY)
- `hallName` (VARCHAR) - e.g., "Worcester", "Hampshire", "Berkshire", "Franklin"
- `hours` (VARCHAR) - e.g., "07:00-21:00"
- `mealHours` (JSON) - Object with breakfast/lunch/dinner hours
- `meals` (JSON) - Object with breakfast/lunch/dinner menu items

### Sample `meals` JSON Structure
```json
{
  "breakfast": [
    {
      "name": "Scrambled Eggs",
      "calories": 200,
      "weeklySelections": 450,
      "dietCategories": ["local", "sustainable"],
      "ingredients": "Farm-fresh eggs, butter, salt",
      "allergens": ["eggs", "dairy"]
    }
  ],
  "lunch": [...],
  "dinner": [...]
}
```

## Weekend Handling

**Important:** On weekends (Saturday & Sunday), dining halls do NOT serve breakfast.

This is handled in multiple places:
1. **Scraper** - Does not scrape breakfast data on weekends
2. **Frontend** - Disables breakfast tab/option on weekends
3. **Backend Views** - Returns lunch when breakfast is requested on weekends

## Data Updates

To update menu data with fresh scraped information:
```bash
# Step 1: Scrape latest data
python3 scripts/scrape_menus.py

# Step 2: Import to database
python3 scripts/import_to_db.py

# Step 3: Verify (optional)
python3 scripts/verify_db_data.py
```

## Cache Management

Menu data is cached in memory for performance. To clear the cache:
```python
from menus.views import clear_menu_cache
clear_menu_cache()
```

Or restart the Django server.

## Notes

- All 4 dining halls (Worcester, Hampshire, Berkshire, Franklin) are included
- Menu items include detailed nutritional and allergen information
- Weekly selection counts reflect popularity
- The system automatically handles hall open/closed status based on current time
