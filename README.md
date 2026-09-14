# PDF-API-

This project API translates PDF content from one language to another and adds a watermark on every page of a PDF.

## Setup

Requires Python 3.11+.

```bash
python -m venv venv
```

Activate the venv:

- Windows (PowerShell): `.\venv\Scripts\Activate.ps1`
- Windows (cmd): `venv\Scripts\activate.bat`
- macOS / Linux: `source venv/bin/activate`

```bash
pip install -r requirements.txt
```

Fonts are already in `fonts/`. No other downloads are required.

## Run the server

```bash
python manage.py migrate
python manage.py runserver
```

The server listens on `http://127.0.0.1:8000`.

> [!CAUTION]
> **Special note:** This project is deployed on Render for public test. After you send the API request in Postman, it can take 60 seconds to show the result. Stay online until then.

## Test both endpoints in Postman

Use a **small 1-page text PDF** (typed text, not a scan or image-only file).

Do **not** use a long story or book PDF (for example `the-most-dangerous-game.pdf`). That file is too big for the public server. The request then hits a **30–60 second** limit and Postman shows `500 Internal Server Error` even when the form is correct.

**Do this the same way for both APIs:**

1. Method must be **POST** (not GET).
2. Leave **Params**, **Authorization**, and **Headers** empty. No bearer token.
3. Open **Body** → select **form-data** only (not raw, not x-www-form-urlencoded).
4. Type every Key **exactly** as shown. Example: `color` not `colour`.
5. For `file`, change the row Type from **Text** to **File**, then choose your PDF.
6. Text values must have **no extra space or new line** (especially `position`).
7. Click **Send**. Wait up to 60 seconds. Then open the downloaded PDF.

### 1. Translate PDF test

1. New request → method **POST**.
2. URL: `https://pdf-api-zm28.onrender.com/api/translate-pdf`
3. Body → **form-data**:

| Key | Type | Value |
|---|---|---|
| `file` | File | a short 1-page text PDF |
| `source_language` | Text | `en` |
| `target_language` | Text | `bn` |

4. Send. Expected: **200** and a downloadable `translated.pdf`.
5. Open that file. The English text should now be in Bangla.

### 2. Watermark PDF test

1. New request → method **POST**.
2. URL: `https://pdf-api-zm28.onrender.com/editor/pdf/watermark`
3. Body → **form-data**:

| Key | Type | Value |
|---|---|---|
| `file` | File | your PDF |
| `text` | Text | `CONFIDENTIAL` |
| `position` | Text | `center` |
| `opacity` | Text | `0.6` |
| `color` | Text | `#FF0000` |

`position` may also be `top-left`, `top-center`, `top-right`, `bottom-left`, `bottom-center`, or `bottom-right`.

4. Send. Expected: **200** and a downloadable `watermarked.pdf`.
5. Open that file. You should see a red **CONFIDENTIAL** stamp on every page.

## Short Postman example

Same rules: **POST**, no auth, **Body → form-data** only. Then download and open the PDF.

**Translate** — `POST https://pdf-api-zm28.onrender.com/api/translate-pdf`  
`file` = a short 1-page text PDF · `source_language` = `en` · `target_language` = `bn`  
→ **200** `translated.pdf` (Bangla text)

**Watermark** — `POST https://pdf-api-zm28.onrender.com/editor/pdf/watermark`  
`file` = your PDF · `text` = `CONFIDENTIAL` · `position` = `center` · `opacity` = `0.6` · `color` = `#FF0000`  
`position` also: `top-left` `top-center` `top-right` `center` `bottom-left` `bottom-center` `bottom-right`  
→ **200** `watermarked.pdf` (red CONFIDENTIAL on each page)
