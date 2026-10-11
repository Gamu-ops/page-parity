# page-parity — web

The page that shows the checker's findings. It needs the API running alongside it.

## Running it

Two terminals, both starting from the repo root.

**1. The API**

```
.\.venv\Scripts\Activate.ps1
uvicorn checker.api:app --reload
```

Serves `http://localhost:8000`.

**2. The page**

```
cd web
npm install        # first time only
npm run dev
```

Open `http://localhost:5173`.

## Notes

The pair of fixtures is fixed in `src/App.jsx`; there is no file picker. The page calls
`GET /check` once on load.

If the API is not running, the page says so. It does not show an empty table — an empty table
means the pages agree, and that must never be confused with not having checked.
