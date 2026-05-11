const PHASE = Object.freeze({
  IDLE: 'idle', STARTED: 'started', PLACING: 'placing',
  PLACED: 'placed', WRONG: 'wrong', WON: 'won',
});

const PLAY = Object.freeze({
  IDLE: 'idle', PLAYING: 'playing', PAUSED: 'paused',
});

// ─── API client ────────────────────────────────────────────────────────────

const api = {
  async _get(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? 'Request failed.');
    return res.json();
  },
  async _post(path) {
    const res = await fetch(path, { method: 'POST' });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? 'Request failed.');
    return res.json().catch(() => null);
  },
  referenceYear:  () => api._get('/api/reference-year'),
  resetScore:     () => api._post('/api/score/reset'),
  addScore:       () => api._post('/api/score/add'),
  resetWildcards: () => api._post('/api/wildcard/reset'),
  addWildcard:    () => api._post('/api/wildcard/add'),
  useWildcard:    () => api._post('/api/wildcard/use'),
  getSong: () => {
    const used = game.timeline.map(c => c.track_id).filter(Boolean).join(',');
    return api._get(used ? `/api/song?exclude=${used}` : '/api/song');
  },
  getDevices:     () => api._get('/api/devices'),
  setDevice:      (id) => fetch(`/api/device/${id}`, { method: 'PUT' }),
  play:           (trackId) => api._post(`/api/play/${trackId}`),
  pause:          () => api._post('/api/pause'),
  resume:         () => api._post('/api/resume'),
};

// ─── Game state ────────────────────────────────────────────────────────────

const game = {
  phase: PHASE.IDLE,
  timeline: [],  // Array<{year, name, artist, track_id, isReference}>
  currentTrack: null,
  placedAtIndex: null,
  playState: PLAY.IDLE,
  score: 0,
  wildcards: 0,
  showAddWildcard: false,
  colorPool: [],
  winScore: parseInt(document.getElementById('win-score-select').value, 10), // read before DOM refs freeze
  playerName: 'Player 1',
};

// ─── DOM refs ──────────────────────────────────────────────────────────────

const startScreen      = document.getElementById('start-screen');
const gameScreen       = document.getElementById('game-screen');
const timelineEl       = document.getElementById('timeline');
const currentCard      = document.getElementById('current-card');
const songControls     = document.getElementById('song-controls');
const btnNewSong       = document.getElementById('btn-new-song');
const btnPlayPause     = document.getElementById('btn-play-pause');
const btnReveal        = document.getElementById('btn-reveal');
const btnSkip          = document.getElementById('btn-skip');
const btnAddWildcard   = document.getElementById('btn-add-wildcard');
const stagingArea      = document.getElementById('staging-area');
const btnConfig        = document.getElementById('btn-config');
const configPanel      = document.getElementById('config-panel');
const errorMsg         = document.getElementById('error-msg');
const scoreDisplay     = document.getElementById('score-display');
const wildcardDisplay  = document.getElementById('wildcard-display');
const wildcardCount    = document.getElementById('wildcard-count');
const winScreen        = document.getElementById('win-screen');
const btnReset         = document.getElementById('btn-home');
const btnStart          = document.getElementById('btn-start');
const playerNameDisplay = document.getElementById('player-name-display');
const winScoreStat      = document.getElementById('win-score-stat');
const deviceSelect      = document.getElementById('device-select');

// ─── Config ────────────────────────────────────────────────────────────────

btnConfig.addEventListener('click', () => {
  const open = !configPanel.classList.contains('hidden');
  configPanel.classList.toggle('hidden', open);
  btnConfig.textContent = open ? '⚙ CONFIG' : '⚙ CONFIG ▲';
});

document.getElementById('win-score-select').addEventListener('change', e => {
  game.winScore = parseInt(e.target.value, 10);
});

document.getElementById('player-name-input').addEventListener('input', e => {
  game.playerName = e.target.value || 'Player 1';
  playerNameDisplay.textContent = game.playerName;
});

// ─── START ─────────────────────────────────────────────────────────────────

btnStart.addEventListener('click', async () => {
  hideError();
  try {
    const [{ year }, { score }, { wildcards }] = await Promise.all([
      api.referenceYear(),
      api.resetScore(),
      api.resetWildcards(),
    ]);

    game.phase = PHASE.STARTED;
    game.score = score;
    game.wildcards = wildcards;
    game.showAddWildcard = false;
    game.colorPool = shuffledColors();
    game.timeline = [{ year, isReference: true, name: null, artist: null, track_id: null }];

    startScreen.classList.add('hidden');
    gameScreen.classList.remove('hidden');
    render(); // render() → updateUI() sets playerNameDisplay
  } catch (e) {
    showError(e.message);
  }
});

// ─── NEW SONG ──────────────────────────────────────────────────────────────

btnNewSong.addEventListener('click', async () => {
  btnNewSong.disabled = true;
  hideError();
  try {
    if (game.playState === PLAY.PLAYING) {
      await api.pause();
      game.playState = PLAY.IDLE;
    }

    game.currentTrack = await api.getSong();
    game.phase = PHASE.PLACING;
    game.placedAtIndex = null;
    game.playState = PLAY.IDLE;
    game.showAddWildcard = false;
    render();
  } catch (e) {
    showError(e.message);
  } finally {
    btnNewSong.disabled = false;
  }
});

// ─── PLAY / PAUSE ──────────────────────────────────────────────────────────

btnPlayPause.addEventListener('click', async () => {
  if (!game.currentTrack) return;
  hideError();

  try {
    if (game.playState === PLAY.IDLE) {
      await api.play(game.currentTrack.track_id);
      game.playState = PLAY.PLAYING;
    } else if (game.playState === PLAY.PLAYING) {
      await api.pause();
      game.playState = PLAY.PAUSED;
    } else {
      await api.resume();
      game.playState = PLAY.PLAYING;
    }
    render();
  } catch (e) {
    showError(e.message);
  }
});

// ─── REVEAL ────────────────────────────────────────────────────────────────

btnReveal.addEventListener('click', async () => {
  if (game.phase !== PHASE.PLACED || !game.currentTrack) return;

  const year = parseInt(game.currentTrack.year, 10);
  const left  = game.placedAtIndex > 0 ? game.timeline[game.placedAtIndex - 1] : null;
  const right = game.placedAtIndex < game.timeline.length ? game.timeline[game.placedAtIndex] : null;
  const valid = (!left || left.year <= year) && (!right || right.year >= year);

  if (valid) {
    game.timeline.splice(game.placedAtIndex, 0, {
      year,
      name: game.currentTrack.name,
      artist: game.currentTrack.artist,
      track_id: game.currentTrack.track_id,
      isReference: false,
      colorIndex: game.colorPool.shift() ?? Math.floor(Math.random() * 10),
    });
    game.currentTrack = null;
    game.placedAtIndex = null;

    try {
      const { score } = await api.addScore();
      game.score = score;
    } catch (e) {
      showError(e.message);
      return;
    }

    if (game.score >= game.winScore) {
      if (game.playState === PLAY.PLAYING) {
        await api.pause().catch(() => {});
        game.playState = PLAY.IDLE;
      }
      game.phase = PHASE.WON;
      winScoreStat.textContent = `${game.score} / ${game.winScore}`;
    } else {
      game.showAddWildcard = true;
      game.phase = PHASE.STARTED;
    }
    render();
  } else {
    game.showAddWildcard = true;
    game.phase = PHASE.WRONG;
    render();
    setTimeout(() => {
      game.phase = PHASE.STARTED;
      game.currentTrack = null;
      game.placedAtIndex = null;
      render();
    }, 1500);
  }
});

// ─── RESET ─────────────────────────────────────────────────────────────────

function resetGame() {
  game.phase = PHASE.IDLE;
  game.timeline = [];
  game.currentTrack = null;
  game.placedAtIndex = null;
  game.score = 0;
  game.wildcards = 0;
  game.showAddWildcard = false;
  game.colorPool = [];
  game.playState = PLAY.IDLE;
  gameScreen.classList.add('hidden');
  winScreen.classList.add('hidden');
  startScreen.classList.remove('hidden');
  btnStart.disabled = !deviceSelect.value;
}

document.getElementById('btn-play-again').addEventListener('click', resetGame);
btnReset.addEventListener('click', resetGame);

// ─── SKIP ──────────────────────────────────────────────────────────────────

btnSkip.addEventListener('click', async () => {
  if (game.wildcards < 1) return;
  btnSkip.disabled = true;
  hideError();
  try {
    if (game.playState === PLAY.PLAYING) {
      await api.pause();
      game.playState = PLAY.IDLE;
    }
    const [{ wildcards }, track] = await Promise.all([api.useWildcard(), api.getSong()]);
    game.wildcards = wildcards;
    game.currentTrack = track;
    game.phase = PHASE.PLACING;
    game.placedAtIndex = null;
    game.playState = PLAY.IDLE;
    game.showAddWildcard = false;
    render();
  } catch (e) {
    showError(e.message);
  } finally {
    btnSkip.disabled = game.wildcards < 1;
  }
});

// ─── ADD WILDCARD ──────────────────────────────────────────────────────────

btnAddWildcard.addEventListener('click', async () => {
  hideError();
  try {
    const { wildcards } = await api.addWildcard();
    game.wildcards = wildcards;
    render();
  } catch (e) {
    showError(e.message);
  }
});

// ─── Drag ──────────────────────────────────────────────────────────────────

function attachDragHandlers(el) {
  el.addEventListener('dragstart', (e) => {
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', 'card');
    el.classList.add('dragging');
  });
  el.addEventListener('dragend', () => el.classList.remove('dragging'));
}

attachDragHandlers(currentCard);

// ─── Render ────────────────────────────────────────────────────────────────

/** Returns indices 0–9 in a uniformly random order (Fisher-Yates). */
function shuffledColors() {
  const arr = [...Array(10).keys()];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function render() {
  renderTimeline();
  renderScore();
  wildcardCount.textContent = game.wildcards;
  updateUI();
}

function renderScore() {
  scoreDisplay.innerHTML = '';
  for (let i = 1; i <= game.winScore; i++) {
    const pip = document.createElement('span');
    pip.className = 'score-pip' + (i <= game.score ? ' filled' : '');
    scoreDisplay.appendChild(pip);
  }
}

function renderTimeline() {
  timelineEl.innerHTML = '';

  const { phase, timeline, placedAtIndex } = game;

  for (let i = 0; i <= timeline.length; i++) {
    if (phase === PHASE.PLACING || (phase === PHASE.PLACED && placedAtIndex !== i)) {
      timelineEl.appendChild(makeDropZone(i));
    } else if (phase === PHASE.PLACED && placedAtIndex === i) {
      timelineEl.appendChild(makePendingCard(false, true));
    } else if (phase === PHASE.WRONG && placedAtIndex === i) {
      timelineEl.appendChild(makePendingCard(true, false));
    }

    if (i < timeline.length) {
      timelineEl.appendChild(makeTimelineCard(timeline[i]));
    }
  }
}

function makeDropZone(index) {
  const el = document.createElement('div');
  el.className = 'drop-zone';

  el.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    el.classList.add('drag-over');
  });
  el.addEventListener('dragleave', () => el.classList.remove('drag-over'));
  el.addEventListener('drop', (e) => {
    e.preventDefault();
    el.classList.remove('drag-over');
    game.placedAtIndex = index;
    game.phase = PHASE.PLACED;
    render();
  });

  return el;
}

function makeTimelineCard(card) {
  const el = document.createElement('div');
  el.className = 'timeline-card ' + (card.isReference ? 'ref-card' : `placed-card placed-card-${card.colorIndex}`);

  const yearEl = document.createElement('div');
  yearEl.className = 'tc-year';
  yearEl.textContent = card.year;
  el.appendChild(yearEl);

  if (card.isReference) {
    const refEl = document.createElement('div');
    refEl.className = 'tc-label';
    refEl.textContent = 'REF';
    el.appendChild(refEl);
  } else {
    const nameEl = document.createElement('div');
    nameEl.className = 'tc-name';
    nameEl.textContent = card.name;
    el.appendChild(nameEl);

    const artistEl = document.createElement('div');
    artistEl.className = 'tc-artist';
    artistEl.textContent = card.artist;
    el.appendChild(artistEl);
  }

  return el;
}

function makePendingCard(isWrong, isDraggable) {
  const el = document.createElement('div');
  el.className = 'timeline-card pending-card' + (isWrong ? ' wrong-card' : '') + (isDraggable ? ' is-draggable' : '');
  el.innerHTML = '<div class="tc-mystery">?</div>';

  if (isDraggable) {
    el.draggable = true;
    attachDragHandlers(el);
  }

  return el;
}

function updateUI() {
  const { phase } = game;
  const hasSong = game.currentTrack !== null;

  currentCard.classList.toggle('hidden', phase !== PHASE.PLACING);
  currentCard.draggable = phase === PHASE.PLACING;

  songControls.classList.toggle('hidden', !hasSong || phase === PHASE.WRONG);
  btnReveal.disabled = phase !== PHASE.PLACED;

  btnPlayPause.textContent = game.playState === PLAY.PLAYING ? '⏸ PAUSE' : '▶ PLAY';

  btnNewSong.classList.toggle('hidden', phase !== PHASE.STARTED);

  scoreDisplay.classList.toggle('hidden', phase === PHASE.IDLE);
  winScreen.classList.toggle('hidden', phase !== PHASE.WON);

  wildcardDisplay.classList.toggle('hidden', phase === PHASE.IDLE);
  btnReset.classList.toggle('hidden', phase === PHASE.IDLE || phase === PHASE.WON);
  stagingArea.classList.toggle('hidden', phase === PHASE.WON);

  btnSkip.classList.toggle('hidden', !hasSong || phase === PHASE.WRONG);
  btnSkip.disabled = game.wildcards < 1;
  btnSkip.title = game.wildcards < 1 ? 'No wildcards available' : 'Skip this song and get a new one (uses 1 wildcard)';

  btnAddWildcard.classList.toggle('hidden', !game.showAddWildcard || phase === PHASE.WON);

  playerNameDisplay.textContent = game.playerName;
}

// ─── Helpers ───────────────────────────────────────────────────────────────

/**
 * Fetches available Spotify devices and populates the device select.
 * Auto-selects the active device and enables the start button if found.
 */
async function loadDevices() {
  try {
    const devices = await api.getDevices();
    const current = deviceSelect.value;
    deviceSelect.innerHTML = '<option value="">Select a device…</option>';
    devices.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.device_id;
      opt.textContent = d.name + (d.is_active ? ' ✓' : '');
      if (d.device_id === current) opt.selected = true;
      deviceSelect.appendChild(opt);
    });
    if (!deviceSelect.value) {
      const active = devices.find(d => d.is_active);
      if (active) {
        deviceSelect.value = active.device_id;
        await api.setDevice(active.device_id).catch(() => {});
        btnStart.disabled = false;
      }
    }
  } catch {
    showError('Could not load Spotify devices.');
  }
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.classList.remove('hidden');
}

function hideError() {
  errorMsg.textContent = '';
  errorMsg.classList.add('hidden');
}

deviceSelect.addEventListener('change', async e => {
  const deviceId = e.target.value;
  btnStart.disabled = !deviceId;
  if (!deviceId) return;
  try {
    await api.setDevice(deviceId);
  } catch {
    showError('Could not select device.');
    btnStart.disabled = true;
  }
});

document.getElementById('btn-refresh-devices').addEventListener('click', loadDevices); // no cached ref needed — event wired once

loadDevices();
