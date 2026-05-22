# System Tests [NOT IMPLEMENTED]

System tests verify the entire stack — nginx, FastAPI, yt-dlp, and the browser UI — running together via `docker compose up`.

## What needs testing

| Flow | Tool | Status |
|------|------|--------|
| Library page loads and lists videos | Playwright | NOT IMPLEMENTED |
| Download Poll page: paste URL, see progress bar move, file appears in Library | Playwright | NOT IMPLEMENTED |
| Download WS page: paste URL, see real-time bar, file appears in Library | Playwright | NOT IMPLEMENTED |
| Video plays in browser (nginx range request + `<video>` element) | Playwright | NOT IMPLEMENTED |
| Delete a video from Library | Playwright | NOT IMPLEMENTED |
| Concurrent WS downloads (multiple rows update independently) | Playwright | NOT IMPLEMENTED |

## Planned approach

```bash
# 1. Start stack
docker compose up --build -d

# 2. Run Playwright tests against http://localhost
npx playwright test system-tests/

# 3. Tear down
docker compose down
```

## Why Playwright (not Cypress)

- Playwright: headless Chromium/Firefox/WebKit, native async, excellent WebSocket inspection
- Cypress: easier for beginners but no native WebSocket support and no Firefox
- For testing WS progress bars specifically, Playwright is the better fit

## When to implement

Add system tests when:
- The backend API stabilises (no more route changes)
- Both Poll and WS download flows are confirmed working manually
- CI has enough capacity to run Docker Compose (GitHub Actions: use `ubuntu-latest`, ~6 min build)

## GitHub Actions integration (planned)

```yaml
system-tests:
  runs-on: ubuntu-latest
  needs: [docker-build]
  steps:
    - uses: actions/checkout@v4
    - run: docker compose up --build -d
    - run: npx playwright install --with-deps chromium
    - run: npx playwright test system-tests/
    - run: docker compose down
```
