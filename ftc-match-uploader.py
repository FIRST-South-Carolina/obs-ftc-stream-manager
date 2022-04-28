try:
    import obspython as obs
except ImportError:
    obs = None

if obs is None:
    # upload video from parameters
    import datetime
    import http.client
    import json
    import os
    import os.path
    import random
    import sys
    import time
    import urllib.error
    import urllib.request

    import httplib2

    import google.oauth2.credentials

    import google_auth_oauthlib.flow

    import googleapiclient.discovery
    import googleapiclient.errors
    import googleapiclient.http


    oauth_client = {
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
        'redirect_uris': ['urn:ietf:wg:oauth:2.0:oob', 'http://localhost'],
    }


    def get_youtube_api(project_id, client_id, client_secret):
        try:
            credentials = google.oauth2.credentials.Credentials.from_authorized_user_file(os.path.join(os.path.dirname(__file__), 'ftc-match-uploader-token.json'))
        except FileNotFoundError:
            client_config = {
                'installed': {
                    **oauth_client,
                    'project_id': project_id,
                    'client_id': client_id,
                    'client_secret': client_secret,
                }
            }
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_config(client_config, ['https://www.googleapis.com/auth/youtubepartner'])
            credentials = flow.run_local_server()
            with open(os.path.join(os.path.dirname(__file__), 'ftc-match-uploader-token.json'), 'w') as token:
                token.write(credentials.to_json())

        return googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)


    def refresh_credentials(google_project_id, google_client_id, google_client_secret):
        print(f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Refreshing credentials', file=sys.stderr)

        get_youtube_api(google_project_id, google_client_id, google_client_secret)


    def delete_credentials(google_project_id, google_client_id, google_client_secret):
        print(f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Deleting stored credentials', file=sys.stderr)

        try:
            os.remove(os.path.join(os.path.dirname(__file__), 'ftc-match-uploader-token.json'))
        except FileNotFoundError:
            print(f'  No stored credentials to delete', file=sys.stderr)


    def upload_video(path, title, google_project_id, google_client_id, google_client_secret, description, category_id, privacy, playlist, toa_key, match):
        print(f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Uploading match video at "{path}"', file=sys.stderr)

        youtube = get_youtube_api(google_project_id, google_client_id, google_client_secret)

        print(f'  Video title: {title}', file=sys.stderr)
        print(f'  Video description:', file=sys.stderr)
        for line in description.splitlines():
            print('    ' + line, file=sys.stderr)
        print(f'  Video category: {category_id}', file=sys.stderr)
        print(f'  Video privacy: {privacy}', file=sys.stderr)

        request_body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': None,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy
            },
        }

        request = youtube.videos().insert(
            part=','.join(request_body.keys()),
            body=request_body,
            media_body=googleapiclient.http.MediaFileUpload(path, chunksize=-1, resumable=True),
        )

        tries = 1

        response = None
        while response is None:
            try:
                status, response = request.next_chunk()
            except googleapiclient.errors.HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    if tries >= 10:
                        raise RuntimeError(f'YouTube upload failed after {tries} tries with status code {e.resp.status}')

                    time.sleep(random.randint(1, 2 ** tries))
                    tries += 1
                else:
                    raise
            except (httplib2.HttpLib2Error, IOError, http.client.NotConnected, http.client.IncompleteRead, http.client.ImproperConnectionState, http.client.CannotSendRequest, http.client.CannotSendHeader, http.client.ResponseNotReady, http.client.BadStatusLine) as e:
                if tries >= 10:
                    raise RuntimeError(f'YouTube upload failed after {tries} tries with error: {e}')

                time.sleep(random.randint(1, 2 ** tries))
                tries += 1

        if 'id' not in response:
            raise RuntimeError(f'YouTube upload failed with unexpected response: {response}')

        video = response['id']
        link = 'https://youtu.be/' + video

        print(f'  YouTube ID: {video}', file=sys.stderr)
        print(f'  YouTube link: {link}', file=sys.stderr)

        if playlist:
            print(f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Adding to playlist {playlist}', file=sys.stderr)

            request_body = {
                'snippet': {
                    'playlistId': playlist,
                    'resourceId': {
                        'kind': 'youtube#video',
                        'videoId': video,
                    },
                },
            }

            request = youtube.playlistItems().insert(
                part=','.join(request_body.keys()),
                body=request_body,
            )

            try:
                response = request.execute()

                if 'id' in response:
                    print(f'  YouTube Playlist Item ID: {response["id"]}', file=sys.stderr)
                else:
                    print(f'  YouTube playlist insert failed with unexpected response: {response}', file=sys.stderr)
            except googleapiclient.errors.HttpError as e:
                print(f'  YouTube playlist insert failed with status code {e.resp.status}', file=sys.stderr)
        else:
            print(f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Not adding to a playlist', file=sys.stderr)

        if toa_key:
            print(f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Adding to The Orange Alliance match {match}', file=sys.stderr)

            toa_headers = {
                'Content-Type': 'application/json',
                'X-Application-Origin': 'OBS FTC Match Uploader',
                'X-TOA-Key': toa_key,
            }

            toa_body = {
                'match_key': match,
                'video_url': link,
            }

            toa_request = urllib.request.Request('https://theorangealliance.org/api/match/video', data=json.dumps(toa_body).encode('utf-8'), headers=toa_headers, method='PUT')

            try:
                with urllib.request.urlopen(toa_request) as toa:
                    response_code = toa.getcode()
                    response = toa.read()

                if response_code != 200:
                    print(f'  The Orange Alliance match video update failed with unexpected status code {response_code} and response: {response}', file=sys.stderr)
            except urllib.error.HTTPError as e:
                print(f'  The Orange Alliance match video update failed with status code {e.code}', file=sys.stderr)

        try:
            os.remove(path)
        except OSError:
            raise RuntimeError(f'Error removing video file: {path}')


    commands = {
        'refresh': refresh_credentials,
        'delete': delete_credentials,
        'upload': upload_video,
    }


    if len(sys.argv) != 3:
        print(f'This file is intended to be used as an OBS script. Load it up in OBS Studio and use it from there.', file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] not in commands:
        print(f'Unknown command: {sys.argv[1]}', file=sys.stderr)
        sys.exit(1)

    try:
        with open(sys.argv[2], 'r') as f:
            metadata = json.load(f)
    except (OSError, ValueError):
        print(f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Error reading metadata file: {sys.argv[2]}', file=sys.stderr)
        sys.exit(1)

    try:
        commands[sys.argv[1]](**metadata)
    except Exception:
        import traceback
        print(f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Exception occurred for command "{sys.argv[1]}":', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            os.remove(sys.argv[2])
        except OSError:
            print(f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Error removing metadata file: {sys.argv[2]}', file=sys.stderr)
            sys.exit(1)
else:
    # implement OBS-side of the plugin
    import json
    import os
    import os.path
    import subprocess
    import sys
    import tempfile
    import urllib.error
    import urllib.request


    if sys.platform == 'win32':
        python_path = os.path.join(sys.exec_prefix, 'pythonw.exe')
    else:
        python_path = os.path.join(sys.exec_prefix, 'bin', 'python3')


    settings = None
    hotkeys = {}

    output = None
    output_video_encoder = None
    output_audio_encoder = None
    action = 'none'
    children = []


    def script_description():
        return '<b>FTC Match Uploader</b><hr/>Cut and upload FTC matches to YouTube during a stream. Optionally add those videos to a playlist or add those videos to an event on The Orange Alliance.<br/><br/>Made by Lily Foster &lt;lily@lily.flowers&gt;'


    def script_load(settings_):
        global settings

        settings = settings_

        reset_match_info()

        # run child reaper every second
        obs.timer_add(check_children, 1000)

        # get saved hotkey data
        hotkey_start = obs.obs_data_get_array(settings, 'hotkey_start')
        hotkey_stop = obs.obs_data_get_array(settings, 'hotkey_stop')
        hotkey_cancel = obs.obs_data_get_array(settings, 'hotkey_cancel')

        # register hotkeys
        hotkeys['start'] = obs.obs_hotkey_register_frontend('ftc-match-uploader_start', '(FTC) Start recording a match', start_recording)
        hotkeys['stop'] = obs.obs_hotkey_register_frontend('ftc-match-uploader_stop', '(FTC) Stop recording a match and upload to YouTube', stop_recording_and_upload)
        hotkeys['cancel'] = obs.obs_hotkey_register_frontend('ftc-match-uploader_cancel', '(FTC) Stop recording a match but cancel uploading to YouTube', stop_recording_and_cancel)

        # load saved hotkey data
        obs.obs_hotkey_load(hotkeys['start'], hotkey_start)
        obs.obs_hotkey_load(hotkeys['stop'], hotkey_stop)
        obs.obs_hotkey_load(hotkeys['cancel'], hotkey_cancel)

        # release data references
        obs.obs_data_array_release(hotkey_start)
        obs.obs_data_array_release(hotkey_stop)
        obs.obs_data_array_release(hotkey_cancel)


    def script_unload():
        destroy_match_video_output()


    def script_save(settings):
        # save hotkey data
        hotkey_start = obs.obs_hotkey_save(hotkeys['start'])
        hotkey_stop = obs.obs_hotkey_save(hotkeys['stop'])
        hotkey_cancel = obs.obs_hotkey_save(hotkeys['cancel'])

        # set hotkey data
        obs.obs_data_set_array(settings, 'hotkey_start', hotkey_start)
        obs.obs_data_set_array(settings, 'hotkey_stop', hotkey_stop)
        obs.obs_data_set_array(settings, 'hotkey_cancel', hotkey_cancel)

        # release data references
        obs.obs_data_array_release(hotkey_start)
        obs.obs_data_array_release(hotkey_stop)
        obs.obs_data_array_release(hotkey_cancel)


    def script_properties():
        props = obs.obs_properties_create()

        youtube_props = obs.obs_properties_create()
        obs.obs_properties_add_group(props, 'youtube', 'YouTube', obs.OBS_GROUP_NORMAL, youtube_props)

        obs.obs_properties_add_text(youtube_props, 'event_name', 'Event Name', obs.OBS_TEXT_DEFAULT)
        obs.obs_properties_add_text(youtube_props, 'youtube_description', 'YouTube Description', obs.OBS_TEXT_MULTILINE)
        obs.obs_properties_add_text(youtube_props, 'youtube_category_id', 'YouTube Category ID', obs.OBS_TEXT_DEFAULT)
        youtube_privacy_status_prop = obs.obs_properties_add_list(youtube_props, 'youtube_privacy_status', 'YouTube Privacy Status', obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
        obs.obs_property_list_add_string(youtube_privacy_status_prop, 'Public', 'public')
        obs.obs_property_list_add_string(youtube_privacy_status_prop, 'Unlisted', 'unlisted')
        obs.obs_property_list_add_string(youtube_privacy_status_prop, 'Private', 'private')
        obs.obs_properties_add_text(youtube_props, 'youtube_playlist', 'YouTube Playlist', obs.OBS_TEXT_DEFAULT)

        scorekeeper_props = obs.obs_properties_create()
        obs.obs_properties_add_group(props, 'scorekeeper', 'Scorekeeper', obs.OBS_GROUP_NORMAL, scorekeeper_props)

        obs.obs_properties_add_text(scorekeeper_props, 'event_code', 'Event Code', obs.OBS_TEXT_DEFAULT)
        obs.obs_properties_add_text(scorekeeper_props, 'scorekeeper_api', 'Scorekeeper API', obs.OBS_TEXT_DEFAULT)

        obs.obs_properties_add_button(scorekeeper_props, 'test_scorekeeper_connection', 'Test Scorekeeper Connection', test_scorekeeper_connection)

        toa_props = obs.obs_properties_create()
        obs.obs_properties_add_group(props, 'toa', 'The Orange Alliance', obs.OBS_GROUP_NORMAL, toa_props)

        obs.obs_properties_add_text(toa_props, 'toa_key', 'TOA Key', obs.OBS_TEXT_PASSWORD)
        obs.obs_properties_add_text(toa_props, 'toa_event', 'TOA Event Code', obs.OBS_TEXT_DEFAULT)

        google_props = obs.obs_properties_create()
        obs.obs_properties_add_group(props, 'google', 'Google API', obs.OBS_GROUP_NORMAL, google_props)

        obs.obs_properties_add_text(google_props, 'google_project_id', 'Google API Project ID', obs.OBS_TEXT_DEFAULT)
        obs.obs_properties_add_text(google_props, 'google_client_id', 'Google API Client ID', obs.OBS_TEXT_DEFAULT)
        obs.obs_properties_add_text(google_props, 'google_client_secret', 'Google API Client Secret', obs.OBS_TEXT_PASSWORD)

        obs.obs_properties_add_button(google_props, 'refresh_google_authentication', 'Refresh Google Authentication', refresh_google_authentication)
        obs.obs_properties_add_button(google_props, 'delete_google_authentication', 'Delete Google Authentication', delete_google_authentication)

        recording_props = obs.obs_properties_create()
        obs.obs_properties_add_group(props, 'recording', 'Recording', obs.OBS_GROUP_NORMAL, recording_props)

        video_encoder_prop = obs.obs_properties_add_list(recording_props, 'video_encoder', 'Video Encoder (H.264)', obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
        obs.obs_property_list_add_string(video_encoder_prop, 'x264', 'obs_x264')
        if obs.obs_encoder_get_display_name('jim_nvenc'):
            obs.obs_property_list_add_string(video_encoder_prop, 'NVENC', 'jim_nvenc')
        elif obs.obs_encoder_get_display_name('ffmpeg_nvenc'):
            obs.obs_property_list_add_string(video_encoder_prop, 'NVENC', 'ffmpeg_nvenc')
        if obs.obs_encoder_get_display_name('amd_amf_h264'):
            obs.obs_property_list_add_string(video_encoder_prop, 'AMF', 'amd_amf_h264')
        if obs.obs_encoder_get_display_name('obs_qsv11'):
            obs.obs_property_list_add_string(video_encoder_prop, 'QuickSync', 'obs_qsv11')
        obs.obs_properties_add_int(recording_props, 'video_bitrate', 'Video Bitrate', 0, 24000, 50)
        audio_encoder_prop = obs.obs_properties_add_list(recording_props, 'audio_encoder', 'Audio Encoder (AAC)', obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
        obs.obs_property_list_add_string(audio_encoder_prop, 'FFmpeg', 'ffmpeg_aac')
        if obs.obs_encoder_get_display_name('mf_aac'):
            obs.obs_property_list_add_string(audio_encoder_prop, 'MediaFoundation', 'mf_aac')
        if obs.obs_encoder_get_display_name('libfdk_aac'):
            obs.obs_property_list_add_string(audio_encoder_prop, 'Fraunhofer FDK', 'libfdk_aac')
        if obs.obs_encoder_get_display_name('CoreAudio_AAC'):
            obs.obs_property_list_add_string(audio_encoder_prop, 'CoreAudio', 'CoreAudio_AAC')
        obs.obs_properties_add_int(recording_props, 'audio_bitrate', 'Audio Bitrate', 0, 2000, 1)

        match_props = obs.obs_properties_create()
        obs.obs_properties_add_group(props, 'match', 'Match (Internal Settings)', obs.OBS_GROUP_NORMAL, match_props)

        match_type_prop = obs.obs_properties_add_list(match_props, 'match_type', 'Match Type', obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
        obs.obs_property_list_add_string(match_type_prop, 'Qualification', 'qualification')
        obs.obs_property_list_add_string(match_type_prop, 'Semi-Final', 'semi-final')
        obs.obs_property_list_add_string(match_type_prop, 'Final', 'final')
        obs.obs_properties_add_int(match_props, 'match_pair', 'Match Pair', 1, 2, 1)
        obs.obs_properties_add_int(match_props, 'match_number', 'Match Number', 1, 50, 1)
        obs.obs_properties_add_int(match_props, 'match_code', 'Match Code', 1, 50, 1)

        obs.obs_properties_add_button(match_props, 'reset_match_info', 'Reset Match Info', reset_match_info)

        return props


    def script_defaults(settings):
        obs.obs_data_set_default_string(settings, 'event_name', 'FTC Test Event')
        obs.obs_data_set_default_string(settings, 'youtube_description', 'Testing FTC video cutting and uploading during a stream')
        obs.obs_data_set_default_string(settings, 'youtube_category_id', '28')
        obs.obs_data_set_default_string(settings, 'youtube_privacy_status', 'private')
        obs.obs_data_set_default_string(settings, 'youtube_playlist', '')

        obs.obs_data_set_default_string(settings, 'event_code', 'ftc_test')
        obs.obs_data_set_default_string(settings, 'scorekeeper_api', 'http://localhost/api')

        obs.obs_data_set_default_string(settings, 'toa_key', '')
        obs.obs_data_set_default_string(settings, 'toa_event', '')

        obs.obs_data_set_default_string(settings, 'google_project_id', '')
        obs.obs_data_set_default_string(settings, 'google_client_id', '')
        obs.obs_data_set_default_string(settings, 'google_client_secret', '')

        obs.obs_data_set_default_string(settings, 'video_encoder', 'obs_x264')
        obs.obs_data_set_default_int(settings, 'video_bitrate', 2500)
        obs.obs_data_set_default_string(settings, 'audio_encoder', 'ffmpeg_aac')
        obs.obs_data_set_default_int(settings, 'audio_bitrate', 192)

        obs.obs_data_set_default_string(settings, 'match_type', 'qualification')
        obs.obs_data_set_default_int(settings, 'match_pair', 1)
        obs.obs_data_set_default_int(settings, 'match_number', 1)
        obs.obs_data_set_default_int(settings, 'match_code', 1)


    def script_update(settings):
        if output:
            destroy_match_video_output()
        create_match_video_output()


    def create_match_video_output():
        global output, output_video_encoder, output_audio_encoder

        print(f'Creating match video OBS output')

        if output:
            print(f'WARNING: Match video OBS output already exists')
            print()
            return

        # create output for match video files
        output_settings = obs.obs_data_create()
        obs.obs_data_set_bool(output_settings, 'allow_overwrite', True)
        output = obs.obs_output_create('ffmpeg_muxer', 'match_file_output', output_settings, None)
        obs.obs_data_release(output_settings)
        if not output:
            print(f'ERROR: Could not create match video output')
            print()
            return

        # create output video encoder for match video files
        output_video_settings = obs.obs_data_create()
        obs.obs_data_set_string(output_video_settings, 'rate_control', 'CBR')
        obs.obs_data_set_int(output_video_settings, 'bitrate', obs.obs_data_get_int(settings, 'video_bitrate'))
        output_video_encoder = obs.obs_video_encoder_create(obs.obs_data_get_string(settings, 'video_encoder'), 'match_video_encoder', output_video_settings, None)
        obs.obs_data_release(output_video_settings)
        if not output_video_encoder:
            print(f'ERROR: Could not create match video encoder')
            destroy_match_video_output()
            return
        if not obs.obs_encoder_get_codec(output_video_encoder):
            print(f'ERROR: Invalid codec for match video encoder')
            destroy_match_video_output()
            return
        obs.obs_encoder_set_video(output_video_encoder, obs.obs_get_video())
        if not obs.obs_encoder_video(output_video_encoder):
            print(f'ERROR: Could not set video handler')
            destroy_match_video_output()
            return
        obs.obs_output_set_video_encoder(output, output_video_encoder)
        if not obs.obs_output_get_video_encoder(output):
            print(f'ERROR: Could not set video encoder to output')
            destroy_match_video_output()
            return

        # create output audio encoder for match video files
        output_audio_settings = obs.obs_data_create()
        obs.obs_data_set_string(output_audio_settings, 'rate_control', 'CBR')
        obs.obs_data_set_int(output_audio_settings, 'bitrate', obs.obs_data_get_int(settings, 'audio_bitrate'))
        output_audio_encoder = obs.obs_audio_encoder_create(obs.obs_data_get_string(settings, 'audio_encoder'), 'match_audio_encoder', output_audio_settings, 0, None)
        obs.obs_data_release(output_audio_settings)
        if not output_audio_encoder:
            print(f'ERROR: Could not create match audio encoder')
            destroy_match_video_output()
            return
        if not obs.obs_encoder_get_codec(output_audio_encoder):
            print(f'ERROR: Invalid codec for match audio encoder')
            destroy_match_video_output()
            return
        obs.obs_encoder_set_audio(output_audio_encoder, obs.obs_get_audio())
        if not obs.obs_encoder_audio(output_audio_encoder):
            print(f'ERROR: Could not set audio handler')
            destroy_match_video_output()
            return
        obs.obs_output_set_audio_encoder(output, output_audio_encoder, 0)
        if not obs.obs_output_get_audio_encoder(output, 0):
            print(f'ERROR: Could not set audio encoder to output')
            destroy_match_video_output()
            return

        # set handler for output signals
        handler = obs.obs_output_get_signal_handler(output)
        obs.signal_handler_connect(handler, 'stop', stop_recording_action)

        print()


    def destroy_match_video_output():
        global output, output_video_encoder, output_audio_encoder

        print(f'Destroying match video OBS output')

        if not output:
            print(f'WARNING: Match video OBS output does not exist')
            print()
            return

        # release output (which should then be garbage collected)
        obs.obs_output_release(output)
        output = None
        obs.obs_encoder_release(output_video_encoder)
        output_video_encoder = None
        obs.obs_encoder_release(output_audio_encoder)
        output_audio_encoder = None

        print()


    def check_children():
        reaped = []
        for child, log in children:
            if child.poll() is not None:
                reaped.append(child)

                if child.returncode != 0:
                    print(f'ERROR: Subprocess exited with code {child.returncode}: {child.args}')
                    with open(log, 'r') as logf:
                        print('\n'.join(f'  {line}' for line in logf.read().splitlines()))
                    print()
                try:
                    os.remove(log)
                except OSError:
                    print(f'WARNING: Failed to remove log file: {log}')

        if reaped:
            children[:] = ((child, log) for child, log in children if child not in reaped)


    def get_match_name():
        match_type = obs.obs_data_get_string(settings, 'match_type')
        if match_type == 'final':
            return f'Finals Match {obs.obs_data_get_int(settings, "match_number")}'
        elif match_type == 'semi-final':
            return f'Semifinals {obs.obs_data_get_int(settings, "match_pair")} Match {obs.obs_data_get_int(settings, "match_number")}'
        elif match_type == 'qualification':
            return f'Qualifications Match {obs.obs_data_get_int(settings, "match_number")}'
        else:
            return f'Match {obs.obs_data_get_int(settings, "match_number")}'


    def reset_match_info(prop=None, props=None):
        obs.obs_data_set_string(settings, 'match_type', 'qualification')
        obs.obs_data_set_int(settings, 'match_pair', 1)
        obs.obs_data_set_int(settings, 'match_number', 1)
        obs.obs_data_set_int(settings, 'match_code', 1)

        print(f'Match info reset')
        print()


    def test_scorekeeper_connection(prop=None, props=None):
        try:
            with urllib.request.urlopen(f'{obs.obs_data_get_string(settings, "scorekeeper_api")}/v1/events/{obs.obs_data_get_string(settings, "event_code")}/') as scorekeeper:
                scorekeeper_code = scorekeeper.getcode()
                event_code = json.load(scorekeeper)['eventCode']
        except urllib.error.HTTPError as e:
            scorekeeper_code = e.code
        except Exception:
            scorekeeper_code = -1

        if scorekeeper_code == 200 and event_code == obs.obs_data_get_string(settings, 'event_code'):
            print(f'Successfully connected to scorekeeper API')
        elif scorekeeper_code == 404:
            print(f'Connected to scorekeeper API but the event code was not found')
        elif scorekeeper_code >= 400:
            print(f'Connected to scorekeeper API but encountered unexpected status code {scorekeeper_code}')
        else:
            print(f'Failed to connect to scorekeeper API')

        print()


    def refresh_google_authentication(prop=None, props=None):
        print(f'Refreshing Google authentication')

        if not obs.obs_data_get_string(settings, 'google_project_id') or not obs.obs_data_get_string(settings, 'google_client_id') or not obs.obs_data_get_string(settings, 'google_client_secret'):
            print(f'ERROR: Google API Project ID, Client ID, and Client Secret are all required')
            print()
            return

        metadata_fd, metadata_path = tempfile.mkstemp(suffix='.json', text=True)

        with os.fdopen(metadata_fd, 'w') as metadata_f:
            json.dump({
                'google_project_id': obs.obs_data_get_string(settings, 'google_project_id'),
                'google_client_id': obs.obs_data_get_string(settings, 'google_client_id'),
                'google_client_secret': obs.obs_data_get_string(settings, 'google_client_secret'),
            }, metadata_f)

        print(f'  Metadata Path: {metadata_path}')

        log_fd, log_path = tempfile.mkstemp(suffix='.txt')

        print(f'  Log Path: {log_path}')

        children.append((subprocess.Popen([python_path, __file__, 'refresh', metadata_path], stdin=subprocess.DEVNULL, stdout=log_fd, stderr=subprocess.STDOUT), log_path))

        os.close(log_fd)

        print()


    def delete_google_authentication(prop=None, props=None):
        print(f'Deleting Google authentication')

        metadata_fd, metadata_path = tempfile.mkstemp(suffix='.json', text=True)

        with os.fdopen(metadata_fd, 'w') as metadata_f:
            json.dump({
                'google_project_id': obs.obs_data_get_string(settings, 'google_project_id'),
                'google_client_id': obs.obs_data_get_string(settings, 'google_client_id'),
                'google_client_secret': obs.obs_data_get_string(settings, 'google_client_secret'),
            }, metadata_f)

        print(f'  Metadata Path: {metadata_path}')

        log_fd, log_path = tempfile.mkstemp(suffix='.txt')

        print(f'  Log Path: {log_path}')

        children.append((subprocess.Popen([python_path, __file__, 'delete', metadata_path], stdin=subprocess.DEVNULL, stdout=log_fd, stderr=subprocess.STDOUT), log_path))

        os.close(log_fd)

        print()


    def stop_recording_action(calldata):
        global action

        signal_output = obs.calldata_ptr(calldata, 'output')
        code = obs.calldata_int(calldata, 'code')

        if signal_output != output:
            print(f'WARNING: Match stop recording signal called with non-match output')
            print()
            return

        output_settings = obs.obs_output_get_settings(output)
        video_path = obs.obs_data_get_string(output_settings, 'path')
        obs.obs_data_release(output_settings)

        if code != 0:  # OBS_OUTPUT_SUCCESS == 0
            print(f'ERROR: Match recording not stopped successfully')
            print()
            return

        if action == 'upload':
            print(f'Uploading recording for {get_match_name()} at "{video_path}"')

            if not obs.obs_data_get_string(settings, 'google_project_id') or not obs.obs_data_get_string(settings, 'google_client_id') or not obs.obs_data_get_string(settings, 'google_client_secret'):
                print(f'ERROR: Google API Project ID, Client ID, and Client Secret are all required')
                print()
                return

            video_title = f'{obs.obs_data_get_string(settings, "event_name")} - {get_match_name()}'

            print(f'  Video title: {video_title}')

            metadata_fd, metadata_path = tempfile.mkstemp(suffix='.json', text=True)

            with os.fdopen(metadata_fd, 'w') as metadata_f:
                json.dump({
                    'path': video_path,
                    'title': video_title,
                    'google_project_id': obs.obs_data_get_string(settings, 'google_project_id'),
                    'google_client_id': obs.obs_data_get_string(settings, 'google_client_id'),
                    'google_client_secret': obs.obs_data_get_string(settings, 'google_client_secret'),
                    'description': obs.obs_data_get_string(settings, 'youtube_description'),
                    'category_id': obs.obs_data_get_string(settings, 'youtube_category_id'),
                    'privacy': obs.obs_data_get_string(settings, 'youtube_privacy_status'),
                    'playlist': obs.obs_data_get_string(settings, 'youtube_playlist'),
                    'toa_key': obs.obs_data_get_string(settings, 'toa_key'),
                    'match': f'{obs.obs_data_get_string(settings, "toa_event")}-{"Q" if obs.obs_data_get_string(settings, "match_type") == "qualification" else "E"}{obs.obs_data_get_int(settings, "match_code"):03}-1'
                }, metadata_f)

            print(f'  Metadata Path: {metadata_path}')

            log_fd, log_path = tempfile.mkstemp(suffix='.txt')

            print(f'  Log Path: {log_path}')

            children.append((subprocess.Popen([python_path, __file__, 'upload', metadata_path], stdin=subprocess.DEVNULL, stdout=log_fd, stderr=subprocess.STDOUT), log_path))

            os.close(log_fd)

            obs.obs_data_set_int(settings, 'match_number', obs.obs_data_get_int(settings, 'match_number') + 1)
            obs.obs_data_set_int(settings, 'match_code', obs.obs_data_get_int(settings, 'match_code') + 1)

            print()
        elif action == 'cancel':
            print(f'Cancelling upload for {get_match_name()} at "{video_path}"')
            print()

        action = 'none'


    def start_recording(pressed=False):
        if pressed:
            return

        if obs.obs_output_active(output):
            print(f'WARNING: Currently recording {get_match_name()}')
            print()
            return

        match_fd, match_path = tempfile.mkstemp(suffix='.mkv')

        output_settings = obs.obs_data_create()
        obs.obs_data_set_string(output_settings, 'path', f'{match_path}')
        obs.obs_output_update(output, output_settings)
        obs.obs_data_release(output_settings)

        if not obs.obs_output_start(output):
            print(f'ERROR: Could not start match recording: {obs.obs_output_get_last_error(output) or "Unknown error"}')
            print()
            return

        if obs.obs_data_get_string(settings, 'scorekeeper_api') and obs.obs_data_get_string(settings, 'event_code'):
            try:
                with urllib.request.urlopen(f'{obs.obs_data_get_string(settings, "scorekeeper_api")}/v1/events/{obs.obs_data_get_string(settings, "event_code")}/matches/active/') as matches:
                    match_data = json.load(matches)['matches']

                if len(match_data) > 0:
                    match_name = match_data[-1]['matchName']
                    match_code = match_data[-1]['matchNumber']

                    if match_name[0] == 'Q':
                        obs.obs_data_set_string(settings, 'match_type', 'qualification')
                        obs.obs_data_set_int(settings, 'match_pair', 1)
                        obs.obs_data_set_int(settings, 'match_number', int(match_name[1:]))
                    elif match_name[0:2] == 'SF' or match_name[0] == 'F':
                        with urllib.request.urlopen(f'{obs.obs_data_get_string(settings, "scorekeeper_api")}/v1/events/{obs.obs_data_get_string(settings, "event_code")}/elim/all/') as elims:
                            match_code = len(json.load(elims)['matchList']) + 1

                        if match_name[0] == 'F':
                            obs.obs_data_set_string(settings, 'match_type', 'final')
                            obs.obs_data_set_int(settings, 'match_pair', 1)
                            obs.obs_data_set_int(settings, 'match_number', int(match_name[2:]))
                        else:
                            obs.obs_data_set_string(settings, 'match_type', 'semi-final')
                            obs.obs_data_set_int(settings, 'match_pair', int(match_name[2]))
                            obs.obs_data_set_int(settings, 'match_number', int(match_name[4:]))
                    else:
                        print(f'WARNING: Recording unknown match type "{match_name}"')
                        obs.obs_data_set_int(settings, 'match_number', match_code)

                    obs.obs_data_set_int(settings, 'match_code', match_code)
            except Exception:
                print(f'WARNING: Failed to communicate with scorekeeper')

        print(f'Recording started for {get_match_name()}')


    def stop_recording_and_upload(pressed=False):
        global action

        if pressed:
            return

        if not obs.obs_output_active(output):
            print(f'WARNING: Not currently recording a match')
            print()
            return

        action = 'upload'

        obs.obs_output_stop(output)

        print(f'Recording stopping for {get_match_name()}')


    def stop_recording_and_cancel(pressed=False):
        global action

        if pressed:
            return

        if not obs.obs_output_active(output):
            print(f'WARNING: Not currently recording a match')
            print()
            return

        action = 'cancel'

        obs.obs_output_stop(output)

        print(f'Recording stopping for {get_match_name()}')
