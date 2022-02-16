# FTC Match Uploader

FTC Match Uploader is an [OBS Studio](https://obsproject.com) script for [FIRST Tech Challenge](https://www.firstinspires.org/robotics/ftc) events that provides hotkeys for starting and stopping match recordings, automatically determining the match being recorded from the FTCLive scoring system, naming and uploading the match video to YouTube on completion, optionally associating that video with a YouTube playlist (e.g. an event playlist), and optionally associating that match video with a match in [The Orange Alliance](https://theorangealliance.org/).

Keep the OBS "Script Log" open to see output from hotkeys and settings buttons.


## OBS Scripting Setup

The FTC Match Uploader script requires [OBS Studio](https://obsproject.com/) and Python 3.6+. OBS Studio only supports Python 3.6 on Windows currently and the latest Windows installer available is [Python 3.6.8](https://www.python.org/ftp/python/3.6.8/python-3.6.8-amd64.exe). From the OBS Studio software, select "Tools" from the menu bar and "Scripts" from the menu, go to the "Python Settings" tab, and select the base prefix for Python 3.6+. For Windows, the base prefix will be `%LOCALAPPDATA%\Programs\Python\Python36`. To load one of the scripts below, go back to the "Scripts" tab and click the "+" in the lower-left and navigate to the appropriate script file.


## FTC Match Uploader Setup

To set up FTC Match Uploader for subsequent use (as in this only needs to be done once per system), the `google-api-python-client` and `google-auth-oauthlib` Python packages must be installed. To install them in Windows, open a PowerShell or CMD command prompt and run the command `%LOCALAPPDATA%\Programs\Python\Python36\Scripts\pip.exe install -U google-api-python-client google-auth-oauthlib`.


## OBS Profile Setup

Load `ftc-match-uploader.py` into OBS Studio. Go to the OBS settings by selecting "File" from the menu bar and "Settings" from the menu. Go to the "Hotkeys" section and assign hotkeys for the actions that start with "(FTC)" by selecting the box to the right of the action description and pressing the desired key combination. These will be saved for later when this script is loaded again.

The hotkey for "Start recording a match" should be pressed when a match is about to begin and the match video should start. I recommend doing this right before randomization so that can be captured in the video. The hotkey for "Stop recording a match and upload to YouTube" should be pressed when a match is complete. I recommend doing this right after the final scores are announced so that can be captured in the video. The hotkey for "Stop recording a match but cancel uploading to YouTube" should be used if a recording needs to be aborted, if for example the match is aborted or randomization needs to happen again. If the recording is aborted, the portion that was recorded is still saved to the hard drive but it will not be uploaded.


## Usage

Load `ftc-match-uploader.py` into OBS Studio (if not already loaded). In the script configuration section, add details for the following:

* Event Name - current event name to use when naming videos
* YouTube Description - description for the uploaded videos
* YouTube Category ID - numeric ID of the desired YouTube category for the video; default is 28 which is "Science & Technology" but 27 is "Education" if that is preferred
* YouTube Privacy Status - whether to set the video as public or not; default is "Private" but this should be "Public" or "Unlisted" during actual events
* YouTube Playlist (optional) - the playlist ID to put the uploaded video into
* Event Code - event code in FTCLive to pull active match from; only used if connection to scorekeeper is successful
* Scorekeeper API - base URL to FTCLive API; default is "http://localhost/api" which will generally only need to be changed if the FTCLive software is running on another machine
* TOA Key (optional) - key for The Orange Alliance API which has access to set match videos for the current event (generally event admin or enough permission to do DataSync will work)
* TOA Event Code (optional) - event code in The Orange Alliance for the current event
* Google API Project ID - project ID to authenticate to Google APIs (generated from Google Cloud Platform Console for your organization)
* Google API Client ID - client ID to authenticate to Google APIs (generated from Google Cloud Platform Console for your organization)
* Google API Client Secret - client secret to authenticate to Google APIs (generated from Google Cloud Platform Console for your organization)

Assuming connection to the scorekeeper is successful, the match type, pair, number, and code data will be automatically populated. Do not change those settings if intending to use this with the FTCLive scoring software.

Test connection to the scorekeeper (if it is running) by scrolling to the end of the configuration and pressing "Test Scorekeeper Connection". If a Google account was previously logged in but you wish to login to a different account, press "Delete Google Authentication".

**Every time after loading this script**, ensure app tokens to access the YouTube account are available and valid with "Refresh Google Authentication" (this will get a new set of tokens if not logged in with an account previously or the previous tokens are deleted or unavailable).
