# Seller Filter Program

A Python program that filters the `center.csv` file by seller and exports filtered specifications to Excel format (.xlsx) for easy download and analysis.

## Features

- **Interactive Mode**: Browse and select from a list of available sellers
- **Command Line Mode**: Filter by specific seller ID or name
- **Flexible Input**: Automatically detects CSV format and encoding
- **Smart Column Detection**: Uses "Seller Name" column when available, falls back to "Seller Id"
- **Excel Export**: Saves filtered data as Excel (.xlsx) files ready for download and analysis

## Installation

No additional dependencies required beyond the existing project setup. The program uses:
- `pandas` (already installed)
- `argparse` (built-in)
- Standard Python libraries

## Usage

### Interactive Mode

Run without arguments to get an interactive list of sellers:

```bash
python3 seller_filter.py
```

This will:
1. Load the `center.csv` file
2. Show a numbered list of all available sellers
3. Let you select a seller by number
4. Generate a filtered CSV file with that seller's data

### Command Line Mode

#### Filter by Seller ID

```bash
python3 seller_filter.py --seller 4297
```

#### Filter by Seller Name

```bash
python3 seller_filter.py --seller "De online tandarts"
```

#### Custom Output File

```bash
python3 seller_filter.py --seller "Medies BV" --output my_filtered_data.xlsx
```

#### Different Input File

```bash
python3 seller_filter.py --input my_data.csv --seller 1234
```

#### Verbose Output

```bash
python3 seller_filter.py --seller 4297 --verbose
```

## Command Line Options

- `--input`: Input CSV file (default: `center.csv`)
- `--seller`: Seller ID or name to filter by (if not provided, interactive mode)
- `--output`: Output Excel file path (auto-generated if not provided)
- `--verbose`: Enable verbose logging
- `--help`: Show help message

## Output

The program creates filtered Excel files in the `outputs/` directory with the naming pattern:
```
seller_{seller_name}_{timestamp}.xlsx
```

For example:
- `seller_4297_20251026_003112.xlsx`
- `seller_De_online_tandarts_20251026_003118.xlsx`

## Example Output

When filtering by seller "De online tandarts", the program will:

1. Load 11,976 rows from `center.csv`
2. Find 1,045 records for "De online tandarts"
3. Save the filtered data to `outputs/seller_De_online_tandarts_20251026_003118.xlsx`
4. Show a summary with total records and sample data

## Integration with Existing System

The seller filter program is designed to work alongside the existing fulfillment processing system:

1. **Input**: Uses the same `center.csv` file that serves as input to the aggregation process
2. **Output**: Creates filtered Excel files in the same `outputs/` directory
3. **Format**: Exports to Excel format (.xlsx) for better usability
4. **Compatibility**: Can be easily integrated into the Flask API for web-based filtering

## Demo

Run the demo script to see the program in action:

```bash
python3 demo_seller_filter.py
```

This will demonstrate various usage patterns and show the generated output files.

## Future Enhancements

The program is designed to be easily extended for web integration:

1. **Flask API Integration**: Add endpoints to the existing Flask app
2. **Web Interface**: Create a frontend interface for seller selection
3. **Batch Processing**: Support filtering multiple sellers at once
4. **Advanced Filtering**: Add date ranges, order status, or other criteria
5. **Export Formats**: Support Excel, JSON, or other output formats
