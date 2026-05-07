const btnNewSong = document.getElementById("btn-new-song");
const btnReveal = document.getElementById("btn-reveal");
const btnPlay = document.getElementById("btn-play");
const card = document.getElementById("card");
const errorMsg = document.getElementById("error-msg");

let currentTrack = null;

btnNewSong.addEventListener("click", async () => {
  btnNewSong.disabled = true;
  hideError();

  try {
    const res = await fetch("/api/song");
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      showError(data.detail ?? "Failed to load a song.");
      return;
    }
    currentTrack = await res.json();
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

  const res = await fetch(`/api/play/${currentTrack.track_id}`, { method: "POST" });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    showError(data.detail ?? "Playback failed.");
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
