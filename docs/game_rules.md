# 🎼🎸 VinylVault — How to Play

VinylVault is a music trivia game where you build a timeline of songs by ear.
Just listen and guess where each track belongs in history!

![VinylVault Main Screen](images/main_page.png)

---

## ⚠️ Playlist warning

VinylVault uses each track's **album release year**, not the song's original release year. Tracks from **compilation albums** (greatest hits, soundtracks, etc.) will show the compilation's release year, which can be decades off from when the song was first recorded — making the game unfair.

The example below shows incorrect years caused by this:

![Compilation and versions song showing wrong Year](images/compilation_and_versions.png)

| Track | Problem | Fix |
|-------|---------|-----|
| Elvis Presley — *Suspicious Minds* | Sourced from a compilation | Add the original album version to the playlist instead |
| Beethoven — classical works | No original release year exists | No fix available — avoid Classical Music playlists |

> ⚠️ **Avoid compilation albums in your playlist.** Remastered editions are fine — they usually retain the original album year.

---

## ⚙️ Configuration

Before starting, click **CONFIG** to customise the game:

| Setting | Description | Default |
|---------|-------------|---------|
| **Device** | The Spotify device that will play the music. You can choose between all devices where you are logged in on Spotify and it is open and active. | — |
| **Playlists** | The playlists defined in `.config/.env` to consider as sources for the game. | All provided in `.config/.env` |
| **Points to win** | How many correct placements are needed to win. | 10 |
| **Players** | Number of players in this game (1–4). Adding players creates a name field for each one. | 1 |
| **Player names** | Display name for each player, shown in the game header. | Player 1, Player 2, … |

> 💡 You must select a device before START becomes available.

![VinylVault Config Menu](images/config_options.png)

---

## 🚀 Starting a game

Hit **START** and each player gets their own random reference year (anywhere from 1960 to today).
That year becomes their **anchor card** — the first card on their timeline, and their first point.

Players take turns in the order they were named in CONFIG. The current player is highlighted in the topbar.

---

## 🎧 Each turn

Click **NEW SONG** to draw a card for the current player. The song starts playing from Spotify and a face-down card appears in the staging area. You can toggle **PLAY / PAUSE** as many times as you want before committing.

![VinylVault Round Flow](images/main_game_logic.png)

> 💡 Each player has their own independent timeline. You will never get a song that is already on the current player's timeline.

---

## 🖱️ Placing your card

Drag the face-down card from the staging area and drop it between any two cards in the timeline.

Changed your mind? No problem — drag the card again to a different spot.
The **REVEAL** button only lights up once the card is somewhere in the timeline.

![VinylVault Placing a card](images/place_card.png)

---

## ✅ Revealing your answer

Click **REVEAL**. The game checks whether the song's actual release year fits the position you chose.

- 🟢 **Correct.** The card flips and stays in the timeline. The current player scores a point!
- 🔴 **Wrong.** The card shakes red and disappears. Score stays the same.

### After a correct reveal

The **+1 WILDCARD** and **NEXT TURN** buttons appear. The current player can:
1. Optionally click **+1 WILDCARD** if they (or someone else at the table) correctly named the song title **and** artist before the reveal.
2. Click **NEXT TURN** to pass to the next player.

### After a wrong reveal

- **2 or more players:** a popup announces the next player's name. Click **CONTINUE** to hand over.
- **Single player:** the turn advances automatically after 1.5 seconds.

![VinylVault Correct Card](images/correct_card_placement.png)

---

## 🃏 Wildcards

Wildcards are bonus tokens each player can earn and spend independently.

### Earning a wildcard

After a correct reveal, the **+1 WILDCARD** button is shown alongside **NEXT TURN**.
If any player at the table correctly named the song's title **and** artist before the reveal, click **+1 WILDCARD** to award one token to the current player before ending the turn.
The button disappears when NEXT TURN is clicked, so don't forget!

### Spending a wildcard

Not feeling a song? The current player can click **SKIP** to burn one wildcard and immediately draw a fresh track.
The button is right next to PLAY — no need to place the card first.
SKIP is greyed out when the current player's wildcard count is zero.

> 💡 Wildcards are per-player and carry over between turns — stock up on easy songs and spend them on the tricky ones!

---

## 🔄 Full game flow

```
         ┌─────────┐
         │  START  │
         └────┬────┘
              │  fetch one reference year per player + init players
              ▼
    ┌───────────────────────────────┐
    │  each player's timeline:      │  score = 1
    │  [own REF year]               │
    │  NEW SONG (Player 1's turn)   │
    └────────────┬──────────────────┘
                 │ click NEW SONG
                 ▼
    ┌──────────────────────────────┐
    │  song card drawn             │  (face-down, draggable)
    │  PLAY / PAUSE / SKIP         │  SKIP available if wildcards > 0
    └──────┬──────────────┬────────┘
           │              │ click SKIP (uses 1 wildcard)
           │              └──────────► draw new song
           │ drag to timeline
           ▼
    ┌──────────────────┐
    │  card placed     │  REVEAL enabled
    │  (re-drag to     │  PLAY / PAUSE still works
    │   change mind)   │
    └────────┬─────────┘
             │ click REVEAL
             ▼
         ┌───┴───┐
    ✅ correct?  ❌ wrong?
         │              │
         ▼              ▼
  card stays in    card shakes red
  timeline          and disappears
  score + 1
         │              │
         ▼              ▼
  [+1 WILDCARD?]   2+ players:
  [NEXT TURN]       wrong popup →
                    CONTINUE
                    single player:
                    auto-advance
                         │
         └──────┬─────────┘
                │  next player's turn
                ▼
         score = WIN?
          ┌────┴────┐
         YES        NO
          │          │
          ▼          ▼
   🎉 [Name] wins!  NEW SONG
   PLAY AGAIN
```

---

## 🏆 Winning

The first player to reach the **Points to win** target (default: 10) wins the game!

Their name is shown on the win screen. Hit **PLAY AGAIN** to start fresh for all players — new reference year, clean timelines.

![VinylVault Win Screen](images/win_game.png)

---

## 🧠 Tips

- 🔍 **Listen for clues** — production style, instrumentation, and vocal tone all hint at the era.
- ❓ **Re-drag before you commit** — you can move the card as many times as you want before clicking REVEAL.
- 🎶 **Keep the music going** — the song keeps playing after a correct reveal, so you can enjoy it while you line up your next pick.
- 🃏 **Call it out loud** — wildcards only land if someone names both the title *and* the artist before REVEAL. No silent victories!
- 💸 **Save wildcards for nightmares** — that one obscure B-side from 1973 is coming. You'll want the escape hatch ready.
- 👀 **Watch the chips** — the topbar shows every player's score as `current/target`. Keep an eye on who's closing in on the win!
