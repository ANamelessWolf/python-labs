# Image Web Scraper (configurable)

Small **web scraper** in Python that starts from a `startPage`, downloads images from `<img src>` that match filters (file type/extension and minimum size in KB), and moves to the next page by following a configurable **action** (e.g., an `<a class="next">`).

---

## 🧠 Design & Flow

1. Load `config.json` and validate the schema with **pydantic**.
2. Request the `startPage` using **requests** with configurable **headers**.
3. Download images that satisfy:
   - Extension is listed in `imageFilter.types`.
   - Minimum file size `imageFilter.minKB` after download (uses `Content-Length` if available; otherwise the bytes are counted).
4. Find the **action** (`action.tag` + `filters`) to locate the next link:
   - If `tag` is `a`, use its `href` attribute.
   - If `tag` is not `a` (e.g., `nav`, `div`, `button`), find the first descendant `a` and use its `href`.
5. If a next URL is found and `actionsCount < limit`, navigate and repeat from step 3.
6. Loops are avoided with `visited_pages` and `visited_images` sets.
7. The run stops when the next action is not found, the limit is reached, or a repetition is detected.

> **Note:** This scraper targets static sites or classic pagination via `<a href="...">`. It does **not** execute JavaScript. If you need real clicks or SPA support, consider **Playwright** or **Selenium**.

---

## 📦 Requirements

- **Conda** (recommended) or `pip`
- Python 3.11

---

## 🛠️ Install with Conda (recommended)

```bash
cd img-scraper
conda env create -f environment.yml
conda activate img-scraper
```

### Install with pip

```bash
pip install "requests>=2.32" "beautifulsoup4>=4.12" "lxml>=5.2" "pydantic>=2.9" "tqdm>=4.66"
```

---

## ⚙️ Configuration

Copy the sample and edit it (`config.json` is git-ignored):

```bash
copy config.sample.json config.json
```

```json
{
  "startPage": "https://example.com/gallery/",
  "headers": { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PythonImgScraper/1.0" },
  "action": {
    "tag": "a",
    "filters": [{ "prop": "class", "value": "next" }],
    "action": { "type": "click" }
  },
  "imageFilter": { "types": ["jpg", "jpeg", "png", "gif"], "minKB": 80 },
  "limit": 100,
  "request": { "timeoutSeconds": 20, "delaySeconds": 1.0 },
  "output": { "directory": "./output", "naming": "Name_{index}.{ext}" }
}
```

| Key | Description |
|---|---|
| `startPage` | First page to scrape (required) |
| `headers` | Extra HTTP headers for every request (optional) |
| `action.tag` | Tag of the "next page" element (`a`, `nav`, `div`, `button`…) |
| `action.filters` | `[{prop, value}]`: exact attribute matches; for `class`, `value` must be one of the element's classes |
| `action.action.type` | Only `click` is supported (it follows the `href`) |
| `imageFilter.types` | Allowed extensions, without the dot (case-insensitive) |
| `imageFilter.minKB` | Minimum size in KB; smaller images are discarded |
| `limit` | Maximum number of page jumps (1–10000, default 100) |
| `request.timeoutSeconds` | Timeout per request (1–120, default 20) |
| `request.delaySeconds` | Pause between pages (0–10, default 1.0) |
| `output.directory` | Output folder (can be overridden with `--output`) |
| `output.naming` | File name pattern (default `Name_{index}.{ext}`) |

If no element matches the action, the scraper also tries `<link rel="next">` and `<a rel="next">`.

### File names (`output.naming`)

- `{index}`: image number, zero-padded to the width of `limit` (`limit: 1000` → `0001`).
- `{ext}`: lowercase extension, without the dot.
- An explicit Python format such as `{index:05d}` is used as is.
- Without `output.naming`, or with unsupported placeholders, the name is `<sha1 hash>_<original name>`.

---

## ▶️ Usage

```bash
python scraper.py --config config.json
python scraper.py --config config.json --output ./output --limit 20 --delay 2 --verbose
```

| Option | Description |
|---|---|
| `--config` | Path to the configuration JSON (required) |
| `--output` | Output folder; overrides `output.directory` (one of the two is required) |
| `--limit` | Overrides `limit` |
| `--delay` | Overrides `request.delaySeconds` |
| `--verbose` | Logs every page and downloaded image (`INFO` level) |

A progress bar shows the page jumps. Images already downloaded in the same run are skipped, and the index only
advances when an image is actually saved.
