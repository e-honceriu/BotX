# Introduction

### Welcome to BotX!

This is a highly customizable Discord bot built with Python and Docker, designed for high-quality music streaming and gaming features. It includes built-in playlist functionality and integrates seamlessly with platforms like YouTube and Spotify. Additionally, it supports League of Legends integration, providing a variety of tools for users to connect and manage game lobbies, track leaderboards, having a built-in elo system for competing with your friends. 

This bot is an implementation integrated with the [BotCore](https://github.com/e-honceriu/BotX) backend, which is also a project developed by me. BotCore serves as the core infrastructure fot the bot, enabling seamless communication and funtionality between the bot and its various features.

# Features

### Music Streaming

The bot allows users to play music directly in voice channels. It supports seamless streaming from popular platforms like YouTube and Spotify, providing high-quality audio.

**Key Features**:
1. **Queue Management**: 
   - Add, remove, shuffle, or navigate through the queue.
2. **Volume Control**: 
   - Adjust the volume to suit your preferences.
3. **Music Player Control**: 
   - Loop a single track or the entire queue.
   - Stop, pause, or resume the music player.
   - Toggle the display of the songs in the queue and navigate through them.
   - Restart the player.
4. **Engagement**: 
   - Like or dislike the currently playing song.
   - Streams are recorded for later reference.
5. **Ads**:
    - Play ads between tracks, while downloading the audio files.
    - Manage ads, including categorizing them into:
     - **Opening**: Ads played at the start of the ad break.
     - **Content**: Ads played during the ad break.
     - **Closing**: Ads played before returning to the song.
6. **Customization**:
    - Enable/Disable ads
    - Change the volume level.
    - Customize the appearance of the buttons themselves.
    - Change the color scheme of the custom buttons and music player.

### League of Legends Integration

The bot integrates with League of Legends, allowing users to monitor leaderboards, manage game lobbies, all based on the Elo system directly through Discord.

**Key Features**
1. **Lobby Management**:
    - Supports multiple game types (e.g., All Mid (AM), Summoner's Rift (SR)).
    - Supports multiple drafting types (e.g., Random Draft (RD), Random Fearless Draft(RFD)).
    - Supports combinations of game types and drafting types with different ranking systems (e.g., RDAM, RFDAM, RDSR, RFDSR, SR).
    - Create ranked/unranked lobbies for all the ranking systems.
    - Connect or disconnect players to/from the lobby.
    - Start matches, automatically creating teams based on Elo ratings for balanced gameplay.
    - Allow teams to ban champions to strategize and prevent certain picks for random draft game types.
    - Generate dynamic champion pools for random draft game types.
    - Live game data tracking is supported, but the application that retrieves the data from the game and sends it to the backend is still under development.
    - Set the winner at the end of the match.
    - Stop the lobby.
2. **Leaderboards**:
    - Displays leaderboards for each ranking system, with an additional Overall leaderboard that combines all of them.
    - Leaderboards refresh automatically every hour.
    - Allows users to navigate through the leaderboards and refresh them manually.
3. **Customization**:
    - Customize the appearance of the lobby and leaderboard buttons.
    - Change the color scheme of the lobbies, leaderboards, and custom buttons.
    - Customize the icons and colors of the teams, choosing them randomly.
    - Set the channels where the leaderboards will be displayed.

### Admin Features

The bot provides several administrative features that help manage server activities and perform cleanups.

**Key Features**
1. **Purge Bot Messages**:
    - Deletes all bot messages.
2. **Purge User Messages**:
    - Deletes all messages from a specific user.
3. **Retrieve Server Log**:
    - Get the bot's logs for the server for troubleshooting and review.