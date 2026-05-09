const WIN_SCORE = 4;

// Game state
const game = {
  phase: 'idle', // 'idle' | 'started' | 'placing' | 'placed' | 'wrong' | 'won'
  timeline: [],  // Array<{year, name, artist, track_id, isReference}>
  currentTrack: null,
  placedAtIndex: null,
  playState: 'idle', // 'idle' | 'playing' | 'paused'
  score: 0,
  wildcards: 0,
  showAddWildcard: false,
};

// DOM refs
const startScreen = document.getElementById('start-screen');
const gameScreen = document.getElementById('game-screen');
const timelineEl = document.getElementById('timeline');
const currentCard = document.getElementById('current-card');
const songControls = document.getElementById('song-controls');
const btnNewSong = document.getElementById('btn-new-song');
const btnPlayPause = document.getElementById('btn-play-pause');
const btnReveal = document.getElementById('btn-reveal');
const btnSkip = document.getElementById('btn-skip');
const btnAddWildcard = document.getElementById('btn-add-wildcard');
const errorMsg = document.getElementById('error-msg');
const scoreDisplay = document.getElementById('score-display');
const wildcardDisplay = document.getElementById('wildcard-display');
const wildcardCount = document.getElementById('wildcard-count');
const winScreen = document.getElementById('win-screen');
const deviceSelector = document.getElementById('device-selector');

// START
document.getElementById('btn-start').addEventListener('click', async () => {
  hideError();
  try {
    const [refRes, scoreRes, wcRes] = await Promise.all([
      fetch('/api/reference-year'),
      fetch('/api/score/reset', { method: 'POST' }),
      fetch('/api/wildcard/reset', { method: 'POST' }),
    ]);
    if (!refRes.ok || !scoreRes.ok || !wcRes.ok) { showError('Failed to start game.'); return; }
    const { year } = await refRes.json();
    const { score } = await scoreRes.json();
    const { wildcards } = await wcRes.json();

    game.phase = 'started';
    game.score = score;
    game.wildcards = wildcards;
    game.showAddWildcard = false;
    game.timeline = [{ year, isReference: true, name: null, artist: null, track_id: null }];

    startScreen.classList.add('hidden');
    gameScreen.classList.remove('hidden');
    render();
  } catch {
    showError('Could not reach the server.');
  }
});

// NEW SONG
btnNewSong.addEventListener('click', async () => {
  btnNewSong.disabled = true;
  hideError();
  try {
    if (game.playState === 'playing') {
      await fetch('/api/pause', { method: 'POST' });
      game.playState = 'idle';
    }

    const res = await fetch('/api/song');
    if (!res.ok) {
      showError((await res.json().catch(() => ({}))).detail ?? 'Failed to load a song.');
      return;
    }

    game.currentTrack = await res.json();
    game.phase = 'placing';
    game.placedAtIndex = null;
    game.playState = 'idle';
    game.showAddWildcard = false;
    btnPlayPause.textContent = '▶ PLAY';
    render();
  } catch {
    showError('Could not reach the server.');
  } finally {
    btnNewSong.disabled = false;
  }
});

// PLAY / PAUSE
btnPlayPause.addEventListener('click', async () => {
  if (!game.currentTrack) return;
  hideError();

  if (game.playState === 'idle') {
    const res = await fetch(`/api/play/${game.currentTrack.track_id}`, { method: 'POST' });
    if (!res.ok) { showError((await res.json().catch(() => ({}))).detail ?? 'Playback failed.'); return; }
    game.playState = 'playing';
    btnPlayPause.textContent = '⏸ PAUSE';
  } else if (game.playState === 'playing') {
    const res = await fetch('/api/pause', { method: 'POST' });
    if (!res.ok) { showError((await res.json().catch(() => ({}))).detail ?? 'Pause failed.'); return; }
    game.playState = 'paused';
    btnPlayPause.textContent = '▶ PLAY';
  } else {
    const res = await fetch('/api/resume', { method: 'POST' });
    if (!res.ok) { showError((await res.json().catch(() => ({}))).detail ?? 'Resume failed.'); return; }
    game.playState = 'playing';
    btnPlayPause.textContent = '⏸ PAUSE';
  }
});

// REVEAL
btnReveal.addEventListener('click', async () => {
  if (game.phase !== 'placed' || !game.currentTrack) return;

  const year = parseInt(game.currentTrack.year, 10);
  const left = game.placedAtIndex > 0 ? game.timeline[game.placedAtIndex - 1] : null;
  const right = game.placedAtIndex < game.timeline.length ? game.timeline[game.placedAtIndex] : null;
  const valid = (!left || left.year <= year) && (!right || right.year >= year);

  if (valid) {
    game.timeline.splice(game.placedAtIndex, 0, {
      year,
      name: game.currentTrack.name,
      artist: game.currentTrack.artist,
      track_id: game.currentTrack.track_id,
      isReference: false,
    });
    game.currentTrack = null;
    game.placedAtIndex = null;

    const scoreRes = await fetch('/api/score/add', { method: 'POST' });
    if (!scoreRes.ok) { showError('Failed to update score.'); return; }
    const { score, won } = await scoreRes.json();
    game.score = score;

    if (won) {
      if (game.playState === 'playing') {
        await fetch('/api/pause', { method: 'POST' }).catch(() => {});
        game.playState = 'idle';
      }
      game.phase = 'won';
    } else {
      game.showAddWildcard = true;
      game.phase = 'started';
    }
    render();
  } else {
    game.showAddWildcard = true;
    game.phase = 'wrong';
    render();
    setTimeout(() => {
      game.phase = 'started';
      game.currentTrack = null;
      game.placedAtIndex = null;
      render();
    }, 1500);
  }
});

// PLAY AGAIN
document.getElementById('btn-play-again').addEventListener('click', () => {
  game.phase = 'idle';
  game.timeline = [];
  game.currentTrack = null;
  game.placedAtIndex = null;
  game.score = 0;
  game.wildcards = 0;
  game.showAddWildcard = false;
  game.playState = 'idle';
  btnPlayPause.textContent = '▶ PLAY';
  gameScreen.classList.add('hidden');
  winScreen.classList.add('hidden');
  startScreen.classList.remove('hidden');
  deviceSelector.classList.remove('hidden');
  const selectedDevice = document.getElementById('device-select').value;
  document.getElementById('btn-start').disabled = !selectedDevice;
});

// SKIP
btnSkip.addEventListener('click', async () => {
  if (game.wildcards < 1) return;
  btnSkip.disabled = true;
  hideError();
  try {
    if (game.playState === 'playing') {
      await fetch('/api/pause', { method: 'POST' });
      game.playState = 'idle';
    }
    const [useRes, songRes] = await Promise.all([
      fetch('/api/wildcard/use', { method: 'POST' }),
      fetch('/api/song'),
    ]);
    if (!useRes.ok || !songRes.ok) { showError('Failed to skip song.'); return; }
    const { wildcards } = await useRes.json();
    game.wildcards = wildcards;
    game.currentTrack = await songRes.json();
    game.phase = 'placing';
    game.placedAtIndex = null;
    game.playState = 'idle';
    game.showAddWildcard = false;
    btnPlayPause.textContent = '▶ PLAY';
    render();
  } catch {
    showError('Could not skip song.');
  } finally {
    btnSkip.disabled = game.wildcards < 1;
  }
});

// ADD WILDCARD
btnAddWildcard.addEventListener('click', async () => {
  hideError();
  try {
    const res = await fetch('/api/wildcard/add', { method: 'POST' });
    if (!res.ok) { showError('Failed to add wildcard.'); return; }
    const { wildcards } = await res.json();
    game.wildcards = wildcards;
    render();
  } catch {
    showError('Could not reach the server.');
  }
});

// Drag events on staging card
currentCard.addEventListener('dragstart', (e) => {
  if (game.phase !== 'placing') { e.preventDefault(); return; }
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', 'card');
  currentCard.classList.add('dragging');
});

currentCard.addEventListener('dragend', () => {
  currentCard.classList.remove('dragging');
});

// ─── Render ────────────────────────────────────────────────────────────────

function render() {
  renderTimeline();
  renderScore();
  wildcardCount.textContent = game.wildcards;
  updateUI();
}

function renderScore() {
  scoreDisplay.innerHTML = '';
  for (let i = 1; i <= WIN_SCORE; i++) {
    const pip = document.createElement('span');
    pip.className = 'score-pip' + (i <= game.score ? ' filled' : '');
    scoreDisplay.appendChild(pip);
  }
}

function renderTimeline() {
  timelineEl.innerHTML = '';

  const { phase, timeline, placedAtIndex } = game;

  for (let i = 0; i <= timeline.length; i++) {
    if (phase === 'placing' || (phase === 'placed' && placedAtIndex !== i)) {
      timelineEl.appendChild(makeDropZone(i));
    } else if (phase === 'placed' && placedAtIndex === i) {
      timelineEl.appendChild(makePendingCard(false, true));
    } else if (phase === 'wrong' && placedAtIndex === i) {
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
    game.phase = 'placed';
    render();
  });

  return el;
}

function makeTimelineCard(card) {
  const el = document.createElement('div');
  el.className = 'timeline-card ' + (card.isReference ? 'ref-card' : 'placed-card');

  const yearEl = document.createElement('div');
  yearEl.className = 'tc-year';
  yearEl.textContent = card.year;
  el.appendChild(yearEl);

  if (card.isReference) {
    const labelEl = document.createElement('div');
    labelEl.className = 'tc-label';
    labelEl.textContent = 'REF';
    el.appendChild(labelEl);
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
    el.addEventListener('dragstart', (e) => {
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', 'card');
      el.classList.add('dragging');
    });
    el.addEventListener('dragend', () => el.classList.remove('dragging'));
  }

  return el;
}

function updateUI() {
  const { phase } = game;
  const hasSong = game.currentTrack !== null;

  currentCard.classList.toggle('hidden', phase !== 'placing');
  currentCard.draggable = phase === 'placing';

  songControls.classList.toggle('hidden', !hasSong || phase === 'wrong');
  btnReveal.disabled = phase !== 'placed';

  btnNewSong.classList.toggle('hidden', phase !== 'started');

  scoreDisplay.classList.toggle('hidden', phase === 'idle');
  winScreen.classList.toggle('hidden', phase !== 'won');
  deviceSelector.classList.toggle('hidden', phase !== 'idle');

  wildcardDisplay.classList.toggle('hidden', phase === 'idle');

  btnSkip.classList.toggle('hidden', !hasSong || phase === 'wrong');
  btnSkip.disabled = game.wildcards < 1;
  btnSkip.title = game.wildcards < 1 ? 'No wildcards available' : 'Skip this song and get a new one (uses 1 wildcard)';

  btnAddWildcard.classList.toggle('hidden', !game.showAddWildcard || phase === 'won');
}

// ─── Helpers ───────────────────────────────────────────────────────────────

async function loadDevices() {
  try {
    const res = await fetch('/api/devices');
    const devices = await res.json();
    const select = document.getElementById('device-select');
    const current = select.value;
    select.innerHTML = '<option value="">Select a device…</option>';
    devices.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.device_id;
      opt.textContent = d.name + (d.is_active ? ' ✓' : '');
      if (d.device_id === current) opt.selected = true;
      select.appendChild(opt);
    });
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

document.getElementById('device-select').addEventListener('change', async e => {
  const deviceId = e.target.value;
  document.getElementById('btn-start').disabled = !deviceId;
  if (!deviceId) return;
  try {
    await fetch(`/api/device/${deviceId}`, { method: 'PUT' });
  } catch {
    showError('Could not select device.');
    document.getElementById('btn-start').disabled = true;
  }
});

document.getElementById('btn-refresh-devices').addEventListener('click', loadDevices);

loadDevices();
