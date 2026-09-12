# PDF Editor APIs

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

## Test both endpoints in Postman

Attach any PDF of your own on the `file` field.

### 1. Translate PDF test

1. New request → method **POST**.
2. URL: `http://127.0.0.1:8000/api/translate-pdf`
3. Body → **form-data**:

| Key | Type | Value |
|---|---|---|
| `file` | File | your PDF |
| `source_language` | Text | `en` |
| `target_language` | Text | `bn` |

4. Send. Expected: **200**, a downloadable `translated.pdf`.



### 2. Watermark PDF test

1. New request → method **POST**.
2. URL: `http://127.0.0.1:8000/editor/pdf/watermark`
3. Body → **form-data**:

| Key | Type | Value |
|---|---|---|
| `file` | File | your PDF |
| `text` | Text | `CONFIDENTIAL` |
| `position` | Text | `center` |
| `opacity` | Text | `0.25` |
| `color` | Text | `#FF0000` |

`position` may also be `top-left`, `top-center`, `top-right`, `bottom-left`, `bottom-center`, or `bottom-right`.

4. Send. Expected: **200**, a downloadable `watermarked.pdf`.

## Short Postman example

Attach **your own PDF** on `file`. Body = **form-data**. Then download the response.

**Translate** — `POST http://127.0.0.1:8000/api/translate-pdf`  
`file` = your PDF · `source_language` = `en` · `target_language` = `bn`  
→ **200** `translated.pdf`

**Watermark** — `POST http://127.0.0.1:8000/editor/pdf/watermark`  
`file` = your PDF · `text` = `CONFIDENTIAL` · `position` = `center` · `opacity` = `0.25` · `color` = `#FF0000`  
`position` also: `top-left` `top-center` `top-right` `center` `bottom-left` `bottom-center` `bottom-right`  
→ **200** `watermarked.pdf`

Full field notes: `POSTMAN.md`  
Collection file: `postman/PDF_Editor_APIs.postman_collection.json`  
Public Postman collection: https://www.postman.com/jesusempireofficial/workspace/pdf-editor-apis-public/collection/52999112-77e47581-6e95-4a38-a142-7010f781916d

