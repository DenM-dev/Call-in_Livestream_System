import obspython as obs
import os
import threading
import time

class h:
    htk_copy = None  # this attribute will hold instance of Hotkey

fnameWatch = ""
callScreenSource = ""
coverImageSource = ""
audioSource1 = ""
audioSource2 = ""
holdTime = 1
delayBeforeShowingCall = 0
watcherThread = None
hkey1 = h()


########################
## 
## OBS functions
## 
########################

def find_sceneitem_context(sceneitem_name):
    yielded = False

    scenes = obs.obs_frontend_get_scenes()

    for src in scenes:
        scene = obs.obs_scene_from_source(src)
        if scene:
            sceneitem = obs.obs_scene_find_source_recursive(scene, sceneitem_name)
            try:
                yield sceneitem
                yielded = True
            finally:
                # obs.obs_sceneitem_release(sceneitem)
                pass

    if not yielded:
        yield None


########################
## 
## Hotkey class definition
## 
########################

class Hotkey:
    def __init__(self, callback, obs_settings, _id):
        self.obs_data = obs_settings
        self.hotkey_id = obs.OBS_INVALID_HOTKEY_ID
        self.hotkey_saved_key = None
        self.callback = callback
        self._id = _id

        self.load_hotkey()
        self.register_hotkey()
        self.save_hotkey()

    def register_hotkey(self):
        description = "Htk " + str(self._id)
        self.hotkey_id = obs.obs_hotkey_register_frontend(
            "htk_id" + str(self._id), description, self.callback
        )
        obs.obs_hotkey_load(self.hotkey_id, self.hotkey_saved_key)

    def load_hotkey(self):
        self.hotkey_saved_key = obs.obs_data_get_array(
            self.obs_data, "htk_id" + str(self._id)
        )
        obs.obs_data_array_release(self.hotkey_saved_key)

    def save_hotkey(self):
        self.hotkey_saved_key = obs.obs_hotkey_save(self.hotkey_id)
        obs.obs_data_set_array(
            self.obs_data, "htk_id" + str(self._id), self.hotkey_saved_key
        )
        obs.obs_data_array_release(self.hotkey_saved_key)


########################
## 
## File Watcher class definition
## 
## Show the Call Screen when the pfp is created, and hide it
## when the pfp is deleted.
## The pfp is created by the discord bot
########################

class FileWatcherThread(threading.Thread):
    def __init__(self, file_path, callback):
        super().__init__()
        self.file_path = file_path
        self.callback = callback
        self.running = True

    def run(self):
        # Get the initial state of the file
        initial_exists = os.path.exists(self.file_path)

        while self.running:
            current_exists = os.path.exists(self.file_path)

            if current_exists != initial_exists:
                initial_exists = current_exists
                self.callback(self.file_path, current_exists)

            time.sleep(1)  # Adjust the interval as needed

    def stop(self):
        self.running = False


def file_change_callback(file_path, exists):
    global delayBeforeShowingCall

    if exists:
        print(f"File '{file_path}' was created.")

        ## Put a small delay to allow text to be displayed before we show the call
        time.sleep(delayBeforeShowingCall)
    else:
        print(f"File '{file_path}' was deleted.")
    
    for sceneitem in find_sceneitem_context(callScreenSource):
        obs.obs_sceneitem_set_visible(sceneitem, exists)


########################
## 
## Script methods
## 
## Defines the script's behavior on load, update, and so on
########################

def script_description():
    return """Dump Button"""


def script_properties():
    settings = obs.obs_properties_create()

    hold_time = obs.obs_properties_add_float(settings,"holdTime","Delay Time (sec):", 0, 60, 0.1)
    imageSourceList = obs.obs_properties_add_list(settings, "coverImage", "Cover", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    audioSourceList1 = obs.obs_properties_add_list(settings, "audioInput1", "Audio Source 1", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    audioSourceList2 = obs.obs_properties_add_list(settings, "audioInput2", "Audio Source 2", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    fname_watch = obs.obs_properties_add_list(settings, "fnameWatch", "Caller Profile Picture", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    call_delay = obs.obs_properties_add_float(settings,"delayBeforeShowingCall","Delay before Call Transition (sec):", 0, 60, 0.1)
    callScreenSourceList = obs.obs_properties_add_list(settings, "callScreenSource", "Call Scene Group", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)

    sources = obs.obs_enum_sources()
    if (sources):
        for source in sources:
            source_id = obs.obs_source_get_unversioned_id(source)
            # print(source, " ---- ", source_id)

            if source_id in ["coreaudio_input_capture", "wasapi_input_capture", "pulse_input_capture", "wasapi_process_output_capture"]:
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(audioSourceList1, name, name)
                obs.obs_property_list_add_string(audioSourceList2, name, name)

            elif source_id in ["image_source", "ffmpeg_source", "color_source", "browser_source", "window_capture", "xcomposite_input", "monitor_capture", "display_capture", "xshm_input", "dshow_input", "game_capture", "scene", "group"]:
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(imageSourceList, name, name)
                obs.obs_property_list_add_string(callScreenSourceList, name, name)
    obs.source_list_release(sources)
    
    return settings


def script_load(settings):
    ## Set up hotkeys
    ## https://github.com/obsproject/obs-studio/blob/master/libobs/obs-hotkeys.h
    hkey1.htk_copy = Hotkey(cb_enable_dump, settings, "Dump Button")
    print("Script loaded")


def script_update(settings):
    global coverImageSource, holdTime, audioSource1, audioSource2, fnameWatch, callScreenSource, watcherThread, delayBeforeShowingCall

    # Update global variables
    holdTime = obs.obs_data_get_double(settings, "holdTime")
    coverImageSource = obs.obs_data_get_string(settings, "coverImage")
    audioSource1 = obs.obs_data_get_string(settings, "audioInput1")
    audioSource2 = obs.obs_data_get_string(settings, "audioInput2")
    fnameWatch = obs.obs_data_get_string(settings, "fnameWatch")
    callScreenSource = obs.obs_data_get_string(settings, "callScreenSource")
    delayBeforeShowingCall = obs.obs_data_get_double(settings, "delayBeforeShowingCall")

    print(f"""Hold Time: {holdTime}
Cover Image: {coverImageSource}
Audio 1: {audioSource1}
Audio 2: {audioSource2}
Path to Caller Profile Picture: {fnameWatch}
Delay before transition to call: {delayBeforeShowingCall}
Call Screen Source: {callScreenSource}""")
    
    if watcherThread:
        watcherThread.stop()
    
    watcherThread = FileWatcherThread(fnameWatch, file_change_callback)
    watcherThread.start()


def script_save(settings):
    hkey1.htk_copy.save_hotkey()
                

########################
## 
## Dump button methods
## 
## Show and hide the elements that cover the screen/mute the audio
########################


def cb_enable_dump(is_button_down):
    global coverImageSource, holdTime, audioSource1, audioSource2
    print(f"Triggered. Button down: {is_button_down}")

    ## When the button is pressed, immediately show the cover image
    if is_button_down:
        for sceneitem in find_sceneitem_context(coverImageSource):
            obs.obs_sceneitem_set_visible(sceneitem, True)
        
        source1 = obs.obs_get_source_by_name(audioSource1)
        if source1:
            obs.obs_source_set_muted(source1, True)
        
        source2 = obs.obs_get_source_by_name(audioSource2)
        if source2:
            obs.obs_source_set_muted(source2, True)
    
    # If the button is released, hide the image after a delay
    else:
        obs.timer_add(remove_cover, int(holdTime * 1000))


def remove_cover():
    global coverImageSource

    obs.remove_current_callback()

    for sceneitem in find_sceneitem_context(coverImageSource):
        obs.obs_sceneitem_set_visible(sceneitem, False)
    
    source1 = obs.obs_get_source_by_name(audioSource1)
    if source1:
        obs.obs_source_set_muted(source1, False)
    
    source2 = obs.obs_get_source_by_name(audioSource2)
    if source2:
        obs.obs_source_set_muted(source2, False)