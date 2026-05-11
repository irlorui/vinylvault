---
name: JS architecture patterns
description: DOM ref caching rules, render() ownership of UI state, play state management, multi-player state model, and shuffle correctness in script.js
type: project
---

## DOM ref caching
- All frequently accessed elements are cached as `const` at the top of the DOM refs block
- Cached: startScreen, gameScreen, timelineEl, currentCard, songControls, btnNewSong, btnPlayPause, btnReveal, btnSkip, btnAddWildcard, stagingArea, btnConfig, configPanel, errorMsg, scoreDisplay, wildcardDisplay, wildcardCount, winScreen, btnReset, btnStart, playersList, winScoreStat, winTitle, deviceSelect
- Acceptable uncached: `win-score-select`, `player-count-select`, `player-names-config`, `btn-play-again`, `btn-refresh-devices` — used only for one-shot event wiring or `getElementById` inside functions
- `game.winScore` initial value reads `win-score-select` directly — must stay before the DOM refs block (inside the `game` object literal)

## Multi-player state model (added v1.1)
- `game.players` is an array of `{name, score, wildcards, timeline, colorPool}` — one entry per player
- `game.currentPlayerIndex` tracks whose turn it is
- `game.awaitingNextTurn` is `true` after a correct REVEAL until NEW SONG is clicked (turn advances lazily)
- `currentPlayer()` arrow function returns `game.players[game.currentPlayerIndex]` — always use this, never index directly
- `syncPlayersFromResponse(data)` syncs `score`/`wildcards`/`currentPlayerIndex` from any `PlayersResponse`; does NOT touch `timeline` or `colorPool` (those are frontend-only)
- Turn advances happen at two points: (a) wrong REVEAL → `api.nextTurn()` called immediately in the 1500ms timeout; (b) correct REVEAL → `game.awaitingNextTurn = true`, then `api.nextTurn()` called at the start of the next NEW SONG click

## render() call chain
- `render()` → `renderPlayers()`, `renderTimeline()`, `renderScore()`, wildcard count, `updateUI()`
- `renderPlayers()` builds `.player-chip` elements in `#players-list`; current player gets `.player-chip--current`
- `renderTimeline()` reads from `currentPlayer()?.timeline ?? []`
- `renderScore()` reads from `currentPlayer()?.score ?? 0`
- All three use optional chaining with `?? 0` fallback to handle the brief window before players are initialized

## render() and updateUI() own all UI state
- `btnPlayPause.textContent` is set exclusively in `updateUI()` based on `game.playState`; never set imperatively in event handlers
- All UI visibility is toggled in `updateUI()` via `classList.toggle('hidden', condition)`

## Play state transitions (PLAY.IDLE → PLAYING → PAUSED)
- Transitions happen in event handlers; `render()` is called after state mutation to sync UI
- When navigating away from a song (NEW SONG, SKIP, WIN), always `await api.pause()` before transitioning if `game.playState === PLAY.PLAYING`, then set `game.playState = PLAY.IDLE`

## shuffledColors()
- Uses Fisher-Yates (Knuth) for uniform distribution
- Returns indices 0–9 shuffled; consumed via `currentPlayer().colorPool.shift()` in the REVEAL handler (per-player pool)
- The old `sort(() => Math.random() - 0.5)` pattern is biased — do not revert

## renderTimeline() loop pattern
- Iterates `i = 0..timeline.length` (inclusive) — renders drop zones/pending slots between and around cards
- Drop zones appear at every slot in PLACING; all slots except current `placedAtIndex` in PLACED
- WRONG phase renders the pending card with `isWrong=true` at `placedAtIndex`

## api._post body support
- `api._post(path, body = null)` — body is optional; when provided, sets `Content-Type: application/json` and JSON-stringifies
- `api.initPlayers(names)` sends `{ names: [...] }` — the outer object is the `InitPlayersRequest` Pydantic model shape
