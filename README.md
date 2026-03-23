# Baidu Tieba Crawler

A Selenium-based web crawler for Baidu Tieba that handles DOM recycling mechanisms to scrape complete post content.

## Features

- ✅ **Handles DOM Recycling**: Baidu Tieba dynamically recycles scrolled DOM nodes - this crawler solves the problem through real-time collection
- ✅ **Auto-Scroll Loading**: Continuously scrolls down to automatically load all floor content
- ✅ **Smart Deduplication**: Automatically filters duplicate content and irrelevant information (sidebars, ads, etc.)
- ✅ **OP-Only Mode**: Option to scrape only original poster's content
- ✅ **Auto-Cleaning**: Automatically removes floor markers and separators for clean text output
- ✅ **Multiple Formats**: Generates raw text, cleaned text, and JSON formats simultaneously

## Requirements

- Python 3.6+
- Chrome Browser
- ChromeDriver (automatically managed with Selenium 4.x)

## Installation

1. Clone the repository
```bash
git clone https://github.com/your-username/tieba-crawler.git
cd tieba-crawler
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Modify the URL in `tieba_crawler.py`, then run:

```bash
python tieba_crawler.py
```

### Custom Settings

Modify parameters in the script:

```python
crawl_tieba_post(
    url="https://tieba.baidu.com/p/YOUR_POST_ID",
    output_file='output.txt',
    only_lz=True  # True: OP only, False: all floors
)
```

### Workflow

1. Program opens browser and navigates to the post
2. **Wait 15 seconds** - for completing CAPTCHA verification (if any)
3. Auto-click "Show OP Only" (optional)
4. Start scrolling and real-time content collection
5. Auto-save to three format files

## Output Files

Three files are generated after execution:

| File | Description |
|------|-------------|
| `*_raw.txt` | Raw version (with floor markers and separators) |
| `*.txt` | Cleaned version (pure text) |
| `*.json` | JSON format data |

### Text File Examples

**Raw File** (`*_raw.txt`):
```
【第1楼】 Author Name
Post content...
--------------------------------------------------------------------------------

【第2楼】 Author Name
Post content...
--------------------------------------------------------------------------------
```

**Cleaned File** (`*.txt`):
```
Post content...

Post content...
```

## Important Notes

⚠️ **Warnings**

1. **CAPTCHA**: If verification appears, complete it manually within the 15-second wait period
2. **Crawl Speed**: 3-second delay after each scroll to avoid anti-crawling mechanisms
3. **Legal Use**: Follow Tieba terms of service, use responsibly, avoid excessive crawling
4. **Personal Use**: This tool is for learning and personal use only, not for commercial purposes

## How It Works

Baidu Tieba uses virtual scrolling technology:
- Unscrolled floors are not loaded
- Scrolled floors get recycled from DOM

This crawler solves this by:
1. Continuously scrolling down the page
2. Real-time collection of currently visible floor content
3. Content hash deduplication to avoid duplicates
4. Auto-detection and filtering of irrelevant content

## Troubleshooting

### Issue: No content collected

- Check if CAPTCHA verification was completed
- Ensure network connection is stable
- Review generated `page_source_debug.html` file for analysis

### Issue: Incomplete content

- Increase scroll wait time (modify seconds in `time.sleep(3)`)
- Check if maximum scroll count limit was reached

## Roadmap

- [ ] Multi-threaded batch crawling support
- [ ] Resume from breakpoint functionality
- [ ] Image scraping support
- [ ] GUI interface

## License

MIT License

## Disclaimer

This project is for learning and research purposes only. Users assume all risks associated with using this tool and must comply with relevant laws and website terms of service. The author is not responsible for any consequences resulting from the use of this tool.

---

⭐ If this project helps you, please give it a star!
