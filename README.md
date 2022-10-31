# OBS FTC Stream Manager

FTC Stream Manager is an [OBS Studio](https://obsproject.com/) script for [FIRST Tech Challenge](https://www.firstinspires.org/robotics/ftc) events that can automatically switch OBS scenes based on match events from the FTCLive scoring system, automatically or by hotkey start and stop match recordings, automatically determine the match being recorded from the FTCLive scoring system, name and upload the match video to YouTube on completion, optionally associate that video with a YouTube playlist (e.g. an event playlist), and optionally associate that match video with a match in [The Orange Alliance](https://theorangealliance.org/).

Keep the OBS "Script Log" open to see output from events, hotkeys, and settings buttons.


## OBS Scripting Setup

The FTC Stream Manager script requires [OBS Studio](https://obsproject.com/) and Python 3.6+. OBS Studio supports current Python versions now on Windows, so grab the latest stable "Windows installer (64-bit)" build available at [python.org](https://www.python.org/downloads/windows/) (currently [3.11.0](https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe)). From the OBS Studio software, select "Tools" from the menu bar and "Scripts" from the menu, go to the "Python Settings" tab, and select the base prefix for Python 3.6+. For Windows, the base prefix will be `%LOCALAPPDATA%\Programs\Python\Python311` (for Python 3.11). To load one of the scripts below, go back to the "Scripts" tab and click the "+" in the lower-left and navigate to the appropriate script file.


## FTC Stream Manager Setup

To set up FTC Stream Manager for subsequent use (as in this only needs to be done once per system), the `google-api-python-client`, `google-auth-oauthlib`, and `websockets` Python packages must be installed. To install them in Windows, open a PowerShell or CMD command prompt and run the command `%LOCALAPPDATA%\Programs\Python\Python311\Scripts\pip.exe install -U google-api-python-client google-auth-oauthlib websockets` (for Python 3.11).


## OBS Profile Setup

Load `ftc-stream-manager.py` into OBS Studio. Go to the OBS settings by selecting "File" from the menu bar and "Settings" from the menu. Go to the "Hotkeys" section and assign hotkeys for the actions that start with "(FTC)" by selecting the box to the right of the action description and pressing the desired key combination. These will be saved for later when this script is loaded again.

The hotkey for "Start recording a match" should be pressed when a match is about to begin and the match video should start. I recommend doing this right before randomization so that can be captured in the video. The hotkey for "Stop recording a match and upload to YouTube" should be pressed when a match is complete. I recommend doing this right after the final scores are announced so that can be captured in the video. The hotkey for "Stop recording a match but cancel uploading to YouTube" should be used if a recording needs to be aborted, if for example the match is aborted or randomization needs to happen again. If the recording is aborted, the portion that was recorded is still saved to the hard drive but it will not be uploaded.


## Usage

Load `ftc-stream-manager.py` into OBS Studio (if not already loaded). In the script configuration section, add details for the following:

* Event Name - current event name to use when naming videos
* YouTube Description - description for the uploaded videos
* YouTube Category ID - numeric ID of the desired YouTube category for the video; default is 28 which is "Science & Technology" but 27 is "Education" if that is preferred
* YouTube Privacy Status - whether to set the video as public or not; default is "Private" but this should be "Public" or "Unlisted" during actual events
* YouTube Playlist (optional) - the playlist ID to put the uploaded video into

* Event Code - event code in FTCLive to pull active match from; only used if connection to scorekeeper is successful
* Scorekeeper API - base URL to FTCLive API; default is "http://localhost/api" which will generally only need to be changed if the FTCLive software is running on another machine
* Scorekeeper WS - address to the `MatchEventStream` API endpoint for the scorekeeper; default is "ws://localhost/api/v2/stream/" which will generally only need to be changed if the FTCLive software is running on another machine

* TOA Key (optional) - key for The Orange Alliance API which has access to set match videos for the current event (generally event admin or enough permission to do DataSync will work)
* TOA Event Code (optional) - event code in The Orange Alliance for the current event

* Google API Project ID - project ID to authenticate to Google APIs (generated from Google Cloud Platform Console for your organization)
* Google API Client ID - client ID to authenticate to Google APIs (generated from Google Cloud Platform Console for your organization)
* Google API Client Secret - client secret to authenticate to Google APIs (generated from Google Cloud Platform Console for your organization)

* Automatic Switcher and Recording Handler - whether the automatic scene switcher and recording handler is enabled
* Override Non-Match Scenes - whether the scene switcher will switch from non-match-related scenes when receiving a match event
* Match Post Time to Match Wait - time after a match score is posted before the scene is switched to match wait scene (-1 to disable)

* Match Load - scene name to show when a match is loaded
* Match Start - scene name to show when a match is started
* Match Abort - scene name to show when a match is aborted
* Match Commit - scene name to show when a match score is committed
* Match Post - scene name to show when a match score is posted
* Match Wait - scene name to show after a specified timer after a match score is posted

Assuming connection to the scorekeeper is successful, the match type, pair, number, and code data will be automatically populated. Do not change those settings if intending to use this with the FTCLive scoring software.

Test connection to the scorekeeper (if it is running) by scrolling to the end of the configuration and pressing "Test Scorekeeper Connection". If a Google account was previously logged in but you wish to login to a different account, press "Delete Google Authentication".

**Every time after loading this script**, ensure app tokens to access the YouTube account are available and valid with "Refresh Google Authentication" (this will get a new set of tokens if not logged in with an account previously or the previous tokens are deleted or unavailable).
