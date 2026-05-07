const btnNewSong = document.getElementById("btn-new-song");
const btnReveal = document.getElementById("btn-reveal");
const btnPlay = document.getElementById("btn-play");
const card = document.getElementById("card");
const errorMsg = document.getElementById("error-msg");

let currentTrack = null;
let playState = "idle"; // "idle" | "playing" | "paused"

btnNewSong.addEventListener("click", async () => {
  btnNewSong.disabled = true;
  hideError();

  try {
    if (playState === "playing") {
      await fetch("/api/pause", { method: "POST" });
    }

    const res = await fetch("/api/song");
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      showError(data.detail ?? "Failed to load a song.");
      return;
    }
    currentTrack = await res.json();
    playState = "idle";
    btnPlay.textContent = "▶ Play";
    card.classList.remove("revealed", "hidden");
    btnPlay.classList.remove("hidden");
    btnReveal.disabled = false;
  } catch {
    showError("Could not reach the server.");
  } finally {
    btnNewSong.disabled = false;
  }
});

btnPlay.addEventListener("click", async () => {
  if (!currentTrack) return;
  hideError();

  if (playState === "idle") {
    const res = await fetch(`/api/play/${currentTrack.track_id}`, { method: "POST" });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      showError(data.detail ?? "Playback failed.");
      return;
    }
    playState = "playing";
    btnPlay.textContent = "⏸ Pause";
  } else if (playState === "playing") {
    const res = await fetch("/api/pause", { method: "POST" });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      showError(data.detail ?? "Pause failed.");
      return;
    }
    playState = "paused";
    btnPlay.textContent = "▶ Play";
  } else if (playState === "paused") {
    const res = await fetch("/api/resume", { method: "POST" });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      showError(data.detail ?? "Resume failed.");
      return;
    }
    playState = "playing";
    btnPlay.textContent = "⏸ Pause";
  }
});

btnReveal.addEventListener("click", () => {
  if (!currentTrack) return;
  document.getElementById("track-name").textContent = currentTrack.name;
  document.getElementById("track-artist").textContent = currentTrack.artist;
  document.getElementById("track-year").textContent = currentTrack.year;
  card.classList.add("revealed");
  btnReveal.disabled = true;
});

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.classList.remove("hidden");
}

function hideError() {
  errorMsg.textContent = "";
  errorMsg.classList.add("hidden");
}
