// Game state
const game = {
  phase: 'idle', // 'idle' | 'started' | 'placing' | 'placed' | 'wrong' | 'won'
  timeline: [],  // Array<{year, name, artist, track_id, isReference}>
  currentTrack: null,
  placedAtIndex: null,
  playState: 'idle', // 'idle' | 'playing' | 'paused'
  score: 0,
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
const errorMsg = document.getElementById('error-msg');

// START
document.getElementById('btn-start').addEventListener('click', async () => {
  hideError();
  try {
    const [refRes, scoreRes] = await Promise.all([
      fetch('/api/reference-year'),
      fetch('/api/score/reset', { method: 'POST' }),
    ]);
    if (!refRes.ok || !scoreRes.ok) { showError('Failed to start game.'); return; }
    const { year } = await refRes.json();
    const { score } = await scoreRes.json();

    game.phase = 'started';
    game.score = score;
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

    const { score, won } = await fetch('/api/score/add', { method: 'POST' }).then(r => r.json());
    game.score = score;

    if (won) {
      if (game.playState === 'playing') {
        await fetch('/api/pause', { method: 'POST' }).catch(() => {});
        game.playState = 'idle';
      }
      game.phase = 'won';
    } else {
      game.phase = 'started';
    }
    render();
  } else {
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
  game.playState = 'idle';
  btnPlayPause.textContent = '▶ PLAY';
  gameScreen.classList.add('hidden');
  document.getElementById('win-screen').classList.add('hidden');
  startScreen.classList.remove('hidden');
  document.getElementById('device-selector').classList.remove('hidden');
  const selectedDevice = document.getElementById('device-select').value;
  document.getElementById('btn-start').disabled = !selectedDevice;
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
  updateUI();
}

function renderScore() {
  const el = document.getElementById('score-display');
  el.innerHTML = '';
  for (let i = 1; i <= 4; i++) {
    const pip = document.createElement('span');
    pip.className = 'score-pip' + (i <= game.score ? ' filled' : '');
    el.appendChild(pip);
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

  if (card.isReference) {
    el.innerHTML = `<div class="tc-year">${card.year}</div><div class="tc-label">REF</div>`;
  } else {
    el.innerHTML = `
      <div class="tc-year">${card.year}</div>
      <div class="tc-name">${card.name}</div>
      <div class="tc-artist">${card.artist}</div>`;
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

  document.getElementById('score-display').classList.toggle('hidden', phase === 'idle');
  document.getElementById('win-screen').classList.toggle('hidden', phase !== 'won');
  document.getElementById('device-selector').classList.toggle('hidden', phase !== 'idle');
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
