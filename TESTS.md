# Tests

## Strategy

Three layers. Each catches different failure modes:

| Layer | Scope | Speed | When it catches bugs |
|-------|-------|-------|----------------------|
| Unit | one function / one component | ~ms | wrong logic in a pure function, broken prop rendering |
| Integration | multiple layers working together (API + routing + business logic) | ~100ms | route misconfiguration, wrong HTTP status, VIDEOS_DIR isolation |
| System | full running stack + real browser | ~minutes | nginx misconfiguration, WS proxy headers, video range requests, UI interactions |

## How to Run

```bash
# Backend unit + integration tests
PYTHONPATH=backend pytest backend/tests/ -v

# Backend unit tests only (fastest)
PYTHONPATH=backend pytest backend/tests/test_unit.py -v

# Frontend unit + integration tests
cd frontend && npm run test:run

# Watch mode (re-runs on file save — use during development)
cd frontend && npm test
```

---

## Unit Tests

Unit tests cover pure functions and isolated components. No HTTP, no file system, no mocking needed.

### Backend — `backend/tests/test_unit.py`

| Test class | Function under test | What it verifies | Why it matters |
|---|---|---|---|
| `TestParseProgress::test_downloading_status` | `services/downloader.parse_progress()` | Correct extraction of percent, speed, eta from yt-dlp dict | Both poll and WS hooks call this — wrong parsing = broken progress bar |
| `TestParseProgress::test_malformed_percent_returns_zero` | `parse_progress()` | `"N/A"` percent string returns `0.0`, not a crash | yt-dlp emits `N/A` for indeterminate downloads |
| `TestParseProgress::test_missing_keys_return_defaults` | `parse_progress()` | Missing dict keys don't raise `KeyError` | yt-dlp dict shape varies by format/platform |
| `TestParseProgress::test_finished_status_carries_filename` | `parse_progress()` | `filename` field is passed through on `"finished"` status | File listing breaks if filename is lost |
| `TestStateNewJob::test_creates_job_with_uuid` | `state.new_job()` | Returns a Job with a 36-char UUID | Job IDs must be unique and valid for polling |
| `TestStateNewJob::test_job_stored_in_state` | `state.new_job()` | Job is registered in `state.jobs` dict | Poll endpoint reads from this dict |
| `TestStateNewJob::test_initial_status_is_queued` | `state.new_job()` | Initial status is `"queued"`, progress is `0.0` | UI should show queued state before download starts |
| `TestProcessorPresets::test_all_presets_are_non_empty_strings` | `services/processor.PRESETS` | All preset values are non-empty strings | An empty ffmpeg filter string causes a silent bad output |
| `TestProcessorPresets::test_default_presets_exist` | `PRESETS` | `boost_2x` and `normalize` keys exist | Frontend dropdown and API docs reference these by name |

### Frontend — `frontend/src/__tests__/atoms/`

| Test file | Component | What it verifies | Why it matters |
|---|---|---|---|
| `Button.test.jsx::renders children` | `Button` | Text content renders | Sanity — component mounts without crash |
| `Button.test.jsx::calls onClick when clicked` | `Button` | `onClick` fires on click | Core interactivity |
| `Button.test.jsx::does not call onClick when disabled` | `Button` | `disabled` prop blocks click | Download button must not double-submit |
| `Button.test.jsx::applies danger variant class` | `Button` | `variant="danger"` adds `text-red-400` | Variant system drives all button colours — regression-catches typos in `VARIANTS` map |
| `ProgressBar.test.jsx::sets width to value` | `ProgressBar` | `style.width` equals `value%` | Bar width is the primary progress signal |
| `ProgressBar.test.jsx::clamps value above 100` | `ProgressBar` | `value=150` renders as `100%` | yt-dlp sometimes briefly reports > 100% |
| `ProgressBar.test.jsx::uses red colour on error` | `ProgressBar` | `error` prop adds `bg-red-500` | Error state must be visually distinct |

### Frontend — `frontend/src/__tests__/molecules/`

| Test file | Component | What it verifies | Why it matters |
|---|---|---|---|
| `DownloadInput.test.jsx::calls onSubmit with URL` | `DownloadInput` | `onSubmit(url)` fires on button click | Core molecule contract — pages depend on receiving the URL |
| `DownloadInput.test.jsx::calls onSubmit on Enter` | `DownloadInput` | Enter key triggers submit | UX expectation — keyboard users |
| `DownloadInput.test.jsx::clears input after submit` | `DownloadInput` | Input value resets to `""` | Without this, user must manually clear before next download |
| `DownloadInput.test.jsx::disabled blocks submit` | `DownloadInput` | `disabled=true` prevents `onSubmit` | Active download must block new submission |
| `JobRow.test.jsx::shows URL` | `JobRow` | URL text is in the DOM | User must see which URL they're downloading |
| `JobRow.test.jsx::shows speed and eta` | `JobRow` | Speed/eta rendered while `status="downloading"` | Primary progress info beyond the bar |
| `JobRow.test.jsx::calls onDismiss on ✕` | `JobRow` | ✕ button triggers `onDismiss` | Dismiss closes WS and removes row from state |
| `JobRow.test.jsx::shows error text` | `JobRow` | Error message renders on `status="error"` | User must know why a download failed |

---

## Integration Tests

Integration tests exercise multiple layers together. Backend tests use `TestClient` (full ASGI stack in-process, no network). File system is isolated with `tmp_path` + `monkeypatch`.

### Backend — `backend/tests/test_videos.py`

| Test | Layers exercised | What it verifies | Why it matters |
|---|---|---|---|
| `test_health` | route → handler | `/api/health` returns `{"status":"ok"}` | Baseline — if this fails nothing else matters |
| `test_list_videos_empty` | route → handler → filesystem | Empty dir returns `[]` | Fresh install / empty library should not crash |
| `test_list_videos_returns_files` | route → handler → filesystem | Files appear in response | Core listing feature |
| `test_delete_video` | route → handler → filesystem | File is removed from disk | Delete must actually remove the file |
| `test_delete_missing_video_returns_404` | route → handler | 404 on unknown filename | Client must know the file was already gone |
| `test_delete_path_traversal_blocked` | route → handler → guard | `../../../etc/passwd` returns 400 or 404 | Security: must not escape VIDEOS_DIR |

### Backend — `backend/tests/test_download_poll.py`

| Test | Layers exercised | What it verifies | Why it matters |
|---|---|---|---|
| `test_start_download_returns_job_id` | route → handler → state | POST returns a UUID job_id | Client needs the ID to start polling |
| `test_poll_job_queued` | route → handler → state | GET job returns valid status field | Core poll contract |
| `test_poll_missing_job_returns_404` | route → handler → state | Unknown job_id → 404 | Client must handle "job expired" gracefully |
| `test_job_reflects_progress` | handler → state → route | Progress written to state is returned by poll | Main invariant: poll reads what the download thread writes |

### Backend — `backend/tests/test_process.py`

| Test | Layers exercised | What it verifies | Why it matters |
|---|---|---|---|
| `test_list_presets` | route → handler → PRESETS | Returns list of preset names | Frontend populates dropdown from this endpoint |
| `test_process_missing_file_returns_404` | route → handler → filesystem | 404 when file doesn't exist | User must know the file was not found |
| `test_process_unknown_preset_returns_400` | route → handler → PRESETS | 400 on unknown preset name | Prevents silent ffmpeg failure with garbage filter |
| `test_process_calls_ffmpeg` | route → handler → service (mocked) | ffmpeg mock called, returns filename | Verifies routing + response shape without needing ffmpeg binary in CI |

---

## System Tests [NOT IMPLEMENTED]

See [system-tests/README.md](system-tests/README.md) for planned scope, tooling choice (Playwright), and GitHub Actions integration plan.

**Gap:** No test currently verifies that nginx proxies correctly, the WS connection upgrades through nginx, or that the `<video>` element receives range responses. These are the failure modes most likely to appear on a new machine or after a nginx config change.

---

## What to do when a test becomes stale

A test becomes stale when the feature it covers changes and the test still passes but tests the wrong thing. Signs:
- Test name no longer matches what the function does
- Test mocks something that no longer exists
- Test passes even when you intentionally break the feature

When this happens: **delete or rewrite the test**. A stale passing test is worse than no test — it creates false confidence.

Rule of thumb: when you change a function, look at its test. If the test would still pass with your change reverted, the test is stale.
