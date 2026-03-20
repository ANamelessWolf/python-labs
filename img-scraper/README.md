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
cd webscraper
conda env create -f environment.yml
conda activate img-scraper
