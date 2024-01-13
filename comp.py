"""
I do not provide support for this unless its an actual error in the code and not related to your setup.
This script was originally written for VS R53 and Python 3.9, and has been tested on VS R65 and Python 3.11.

You'll need:
- VapourSynth (https://github.com/vapoursynth/vapoursynth/releases)
- "pip install pathlib anitopy pyperclip requests requests_toolbelt natsort vstools rich colorama" in terminal (without quotes)
- "vsrepo install fpng lsmas sub" in terminal (without quotes) or the following installed to your usual VapourSynth plugins folder:
    - https://github.com/Mikewando/vsfpng
    - https://github.com/AkarinVS/L-SMASH-Works/releases/latest
    - https://github.com/vapoursynth/subtext/releases/latest
    - Note: plugins folder is typically found in "%AppData%\Roaming\VapourSynth\plugins64" or "C:\Program Files\VapourSynth\plugins"
- Optional: If using FFmpeg, it must be installed and in PATH.

How to use:
- Drop comp.py into a folder with the video files you want to compare.
- (Recommended) Rename your files to have the typical [Group] Show - Ep.mkv naming, since the script will try to parse the group and show name.
  e.g. [JPBD] Youjo Senki - 01.m2ts; [Vodes] Youjo Senki - 01.mkv.
- Change variables below.
- Run comp.py.
"""

# Ram limit (in MB)
ram_limit = 4000

# Number of dark, bright, and high motion frames to algorithmically select.
frame_count_dark = 20
frame_count_bright = 10
frame_count_motion = 15
# Choose your own frames to export. Does not decrease the number of algorithmically selected frames.
user_frames = []
# Number of frames to choose randomly. Completely separate from frame_count_bright, frame_count_dark, and save_frames. Will change every time you run the script.
random_frames = 15

# Save the brightness data in a text file so it doesn't have to be reanalysed next time the script is run. Frames will be reanalysed if show/movie name or episode numbers change.
# Does not save user_frames or random_frames.
save_frames = True

# Print frame info on screenshots.
frame_info = True
# Upscale videos to make the clips match the highest found res.
upscale = True
# Scale all videos to one vertical resolution. Set to 0 to disable, otherwise input the desired vertical res.
single_res = 0
# Use FFmpeg as the image renderer. If false, fpng is used instead
ffmpeg = False
# Compression level. For FFmpeg, range is 0-100. For fpng, 0 is fast, 1 is slow, 2 is uncompressed.
compression = 1

# Automatically upload to slow.pics.
slowpics = True
# Flags to toggle for slowpics settings.
hentai_flag = False
public_flag = True
# TMDB ID of show or movie being comped. Should be in the format "TV_XXXXXX" or "MOVIE_XXXXXX".
tmdbID = ""
# Remove the comparison after this many days. Set to 0 to disable.
remove_after = 0
# Output slow.pics link to discord webhook. Disabled if empty.
webhook_url = r""
# Automatically open slow.pics url in default browser
browser_open = True
# Create a URL shortcut for each comparison uploaded.
url_shortcut = True
# Automatically delete the screenshot directory after uploading to slow.pics.
delete_screen_dir = True

"""
Used to trim clips, or add blank frames to the beginning of a clip.
Clips are taken in alphabetical order of the filenames.
First input can be the filename, group name, or index of the file. Second input must be an integer.

Example:
trim_dict = {0: 1000, "Vodes": 1046, 3:-50}
trim_dict_end = {"Youjo Senki - 01.mkv": 9251, 4: -12}
First clip will start at frame 1000.
Clip with group name "Vodes" will start at frame 1046.
Clip with filename "Youjo Senki - 01.mkv" will end at frame 9251.
Fourth clip will have 50 blank frames appended to its start.
Fifth clip will end 12 frames early.
"""
trim_dict = {}
trim_dict_end = {}

"""
Actively adjusts a clip's fps to a target. Useful for sources like amazon hidive, which incorrectly converts 23.976fps to 24fps.
First input can be the filename, group name, or index of the file. 
Second input must be a fraction split into a list. Numerator comes first, denominator comes second.
Second input can also be the string "set". This will make all other files, if unspecified fps, use the set file's fps.

Example:
change_fps = {0: [24, 1], 1: [24000, 1001]}
First clip will have its fps adjusted to 24
Second clip will have its fps adjusted to 23.976

Example 2:
change_fps = {0: [24, 1], "MTBB": "set"}
First clip will have its fps adjusted to 24
Every other clip will have its fps adjusted to match MTBB's
"""
change_fps = {}

"""
Specify which clip will be analyzed for frame selection algorithm.
Input can be the filename, group name, or index of the file.
By default will select the file which can be accessed the fastest.
"""
analyze_clip = ""

##### Advanced Settings #####

# Random seed to use in frame selection algorithm. May change selected frames. Recommended to leave as default
random_seed = 20202020
# Filename of the text file in which the brightness data will be stored. Recommended to leave as default.
frame_filename = "generated.compframes"
# Directory in which the screenshots will be kept
screen_dirname = "screens"
# Minimum time between dark, light, and random frames, in seconds. Motion frames use a quarter of this value
screen_separation = 6
# Number of frames in each direction over which the motion data will be averaged out. So a radius of 4 would take the average of 9 frames, the frame in the middle, and 4 in each direction.
# Higher value will make it less likely scene changes get picked up as motion, but may lead to less precise results.
motion_diff_radius = 4

### Not recommended to change stuff below
import os, sys, time, textwrap, re, uuid, random, pathlib, requests, vstools, webbrowser, colorama, shutil, fractions, subprocess
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from natsort import os_sorted
import anitopy as ani
import pyperclip as pc
import vapoursynth as vs
from requests import Session
from functools import partial
from requests_toolbelt import MultipartEncoder
from typing import Any, Dict, List, Optional, BinaryIO, Union, Callable, TypeVar, Sequence, cast
RenderCallback = Callable[[int, vs.VideoFrame], None]
VideoProp = Union[int, Sequence[int],float, Sequence[float],str, Sequence[str],vs.VideoNode, Sequence[vs.VideoNode],vs.VideoFrame, Sequence[vs.VideoFrame],Callable[..., Any], Sequence[Callable[..., Any]]]
T = TypeVar("T", bound=VideoProp)
vs.core.max_cache_size = ram_limit
colorama.init()

def FrameInfo(clip: vs.VideoNode,
              title: str,
              style: str = "sans-serif,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,""0,0,0,0,100,100,0,0,1,2,0,7,10,10,10,1",
              newlines: int = 3,
              pad_info: bool = False) -> vs.VideoNode:
    """
    FrameInfo function stolen from awsmfunc, implemented by LibreSneed
    Prints the frame number, frame type and a title on the clip
    """

    def FrameProps(n: int, f: vs.VideoFrame, clip: vs.VideoNode, padding: Optional[str]) -> vs.VideoNode:
        if "_PictType" in f.props:
            info = f"Frame {n} of {clip.num_frames}\nPicture type: {f.props['_PictType'].decode()}"
        else:
            info = f"Frame {n} of {clip.num_frames}\nPicture type: N/A"

        if pad_info and padding:
            info_text = [padding + info]
        else:
            info_text = [info]

        clip = vs.core.sub.Subtitle(clip, text=info_text, style=style)

        return clip

    padding_info: Optional[str] = None

    if pad_info:
        padding_info = " " + "".join(['\n'] * newlines)
        padding_title = " " + "".join(['\n'] * (newlines + 4))
    else:
        padding_title = " " + "".join(['\n'] * newlines)

    clip = vs.core.std.FrameEval(clip, partial(FrameProps, clip=clip, padding=padding_info), prop_src=clip)
    clip = vs.core.sub.Subtitle(clip, text=[padding_title + title], style=style)

    return clip

def dedupe(clip: vs.VideoNode, framelist: list, framecount: int, diff_thr: int, selected_frames: list = [], seed: int = None, motion: bool = False):
    """
    Selects frames from a list as long as they aren't too close together.
    
    :param framelist:     Detailed list of frames that has to be cut down.
    :param framecount:    Number of frames to select.
    :param seed:          Seed for `random.sample()`.
    :param diff_thr:      Minimum distance between each frame (in seconds).
    :param motion:        If enabled, the frames will be put in an ordered list, not selected randomly.

    :return:              Deduped framelist
    """

    random.seed(seed)
    thr = round(clip.fps_num / clip.fps_den * diff_thr)
    initial_length = len(selected_frames)

    while (len(selected_frames) - initial_length) < framecount and len(framelist) > 0:
        dupe = False

        #get random frame from framelist with removal. if motion, get first frame     
        if motion:
            rand = framelist.pop(0)
        else:
            rand = framelist.pop(random.randint(0, len(framelist) - 1))

        #check if it's too close to an already selected frame
        for selected_frame in selected_frames:
            if abs(selected_frame - rand) < thr:
                dupe = True
                break

        if not dupe:
            selected_frames.append(rand)

    selected_frames.sort()
    
    return selected_frames

def lazylist(clip: vs.VideoNode, dark_frames: int = 25, light_frames: int = 15, motion_frames: int = 0, selected_frames: list = [], seed: int = random_seed,
             diff_thr: int = screen_separation, diff_radius: int = motion_diff_radius, dark_list: list = None, light_list: list = None, motion_list: list = None, 
             save_frames: bool = False, file: str = None, files: list = None, files_info: list = None):
    """
    Generates a list of frames for comparison purposes.

    :param clip:             Input clip.
    :param dark_frames:      Number of dark frames.
    :param light_frames:     Number of light frames.
    :param motion_frames:    Number of frames with high level of motion.
    :param seed:             Seed for `random.sample()`.
    :param diff_thr:         Minimum distance between each frame (in seconds).
    :param diff_thr:         Number of frames to take into account when finding high motion frames.
    :param dark_list:        Pre-existing detailed list of dark frames that needs to be sorted.
    :param light_list:       Pre-existing detailed list of light frames that needs to be sorted.
    :param motion_list:      Pre-existing detailed list of high motion frames that needs to be sorted.
    :param save_frames:      If true, returns detailed lists with every type of frame.
    :param file:             File being analyzed.
    :param files:            List of files in directory.
    :param files_info:       Information for each file in directory.

    :return:                 List of dark, light, and high motion frames.
    """

    #if no frames were requested, return empty list before running algorithm
    if dark_frames + light_frames + motion_frames == 0:
        return [], dark_list, light_list, motion_list

    dark = []
    light = []
    diff = []
    motion = []

    if dark_list is None or light_list is None or motion_list is None:

        def checkclip(n, f, clip):
            avg = f.props["PlaneStatsAverage"]

            if 0.062746 <= avg <= 0.380000:
                dark.append(n)

            elif 0.450000 <= avg <= 0.800000:
                light.append(n)

            if motion_list is None and motion_frames > 0:

                #src = mvf.Depth(clip, 5)
                gray = vstools.get_y(clip)

                gray_last = vs.core.std.BlankClip(gray)[0] + gray

                #make diff between frame and last frame, with prewitt (difference is white on black background)
                diff_clip = vs.core.std.MakeDiff(gray_last, gray)
                diff_clip = vs.core.std.Prewitt(diff_clip)

                diff_clip = diff_clip.std.PlaneStats()

                diff.append(diff_clip.get_frame(n).props["PlaneStatsAverage"])

            return clip

        s_clip = clip.std.PlaneStats()

        eval_frames = vs.core.std.FrameEval(clip, partial(checkclip, clip=s_clip), prop_src=s_clip)

        #if group name is present, display only it and color it cyan. if group name isnt present, display file name and color it yellow.
        if file is not None and files is not None and files_info is not None:
            suffix = get_suffix(file, files, files_info)
            if suffix == files_info[files.index(file)].get("file_name"):
                message = f'Analyzing video: [yellow]{suffix.strip()}'
            else:
                message = f"Analyzing video: [cyan]{suffix.strip()}"
        else:
            message = "Analyzing video"

        vstools.clip_async_render(eval_frames, progress=message)     

    else:
        dark = dark_list
        light = light_list
        diff = motion_list 

    #remove frames that are within diff_thr seconds of other frames. for dark and light, select random frames as well
    selected_frames = dedupe(clip, dark, dark_frames, diff_thr, selected_frames, seed)
    selected_frames = dedupe(clip, light, light_frames, diff_thr, selected_frames, seed)

    #find frames with most motion
    if motion_frames > 0:

        avg_diff = []

        #get average difference over diff_radius frames in each direction
        #store frame number in avg_diff as well in the form [frame, avg_diff]
        for i, d in enumerate(diff):

            if i >= (diff_radius) and i < (clip.num_frames - diff_radius):
                if isinstance(d, float):
                    surr_frames = diff[i-diff_radius:i+diff_radius+1]
                    mean = sum(surr_frames) / len(surr_frames)
                    avg_diff.append([i, mean])

        #sort avg_diff list based on the diff values, not the frame numbers
        sorted_avg_diff = sorted(avg_diff, key=lambda x: x[1], reverse=True)

        for i in range(0, len(sorted_avg_diff)):
            motion.append(sorted_avg_diff[i][0])

        #remove frames that are too close to other frames. uses lower diff_thr because high motion frames will be different from one another
        selected_frames = dedupe(clip, motion, motion_frames, round(diff_thr/4), selected_frames, seed, motion=True)

    print()

    if save_frames:
        dark_list = dark
        light_list = light
        motion_list = diff

        return selected_frames, dark_list, light_list, motion_list
    else:
        return selected_frames

def _get_slowpics_header(content_length: str, content_type: str, sess: Session) -> Dict[str, str]:
    """
    Stolen from vardefunc, fixed by Jimbo.
    """

    return {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9",
        "Access-Control-Allow-Origin": "*",
        "Content-Length": content_length,
        "Content-Type": content_type,
        "Origin": "https://slow.pics/",
        "Referer": "https://slow.pics/comparison",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "X-XSRF-TOKEN": sess.cookies.get_dict()["XSRF-TOKEN"]
    }

def get_highest_res(files: List[str]) -> int:
    """
    Finds the video source with the highest resolution from a list of files.

    :param files:    The list of files in question.

    :return:         The width, height, and filename of the highest resolution video.
    """

    height = 0
    width = 0
    filenum = -1
    for f in files:
        filenum+=1
        video = vs.core.lsmas.LWLibavSource(f)
        if height < video.height:
            height = video.height
            width = video.width
            max_res_file = filenum

    return width, height, max_res_file

def estimate_analysis_time(file, read_len: int=15):
    """
    Estimates the time it would take to analyze a video source.

    :param read_len:    How many frames to read from the video.
    """

    clip = vs.core.lsmas.LWLibavSource(file)

    #safeguard for if there arent enough frames in clip
    while clip.num_frames / 3 + 1 < read_len:
        read_len -= 1

    clip1 = clip[int(clip.num_frames / 3) : int(clip.num_frames / 3) + read_len]
    clip2 = clip[int(clip.num_frames * 2 / 3) : int(clip.num_frames * 2 / 3) + read_len]

    def checkclip(n, f, clip):
        avg = f.props["PlaneStatsAverage"]
        return clip

    start_time = time.time()
    vstools.clip_async_render(vs.core.std.FrameEval(clip1, partial(checkclip, clip=clip1.std.PlaneStats()), prop_src=clip1.std.PlaneStats()))
    elapsed_time = time.time() - start_time

    start_time = time.time()
    vstools.clip_async_render(vs.core.std.FrameEval(clip2, partial(checkclip, clip=clip2.std.PlaneStats()), prop_src=clip2.std.PlaneStats()))
    elapsed_time = (elapsed_time + time.time() - start_time)/2

    return elapsed_time

def evaluate_analyze_clip(analyze_clip, files, files_info):
    """
    Determines which file should be analyzed by lazylist.
    """

    file_analysis_default = False

    #check if analyze_clip is an int or string with just an int in it
    if (isinstance(analyze_clip, int) and analyze_clip >= 0) or (isinstance(analyze_clip, str) and analyze_clip.isdigit() and int(analyze_clip) >= 0):
        first_file = files[int(analyze_clip)]

    #check if analyze_clip is a group or file name
    elif isinstance(analyze_clip, str) and analyze_clip != "":
        matches = 0
        for dict in files_info:
            if analyze_clip == dict.get("release_group") or analyze_clip == dict.get("file_name") or analyze_clip in dict.get("file_name"):
                matches+=1
                first_file = files[files_info.index(dict)]

        #if no matches found, use default
        if matches == 0:
            print('No file matching the "analyze_clip" parameter has been found. Using default.')
            file_analysis_default = True
        if matches > 1:
            print('Too many files match the "analyze_clip" parameter. Using default.')

    #if no clip specified, use default
    else:
        file_analysis_default = True

    #default: pick file with smallest read time
    if file_analysis_default:
        print("Determining which file to analyze...\n")
        estimated_times = [estimate_analysis_time(file) for file in files]
        first_file = files[estimated_times.index(min(estimated_times))]
    
    return first_file

def init_clip(file: str, files: list, trim_dict: dict, trim_dict_end: dict, change_fps: dict = {}, 
              analyze_clip: str = None, files_info: list = None, return_file: bool = False):
    """
    Gets trimmed and fps modified clip from video file.
    """

    #evaluate analyze_clip if it hasn't been already
    if analyze_clip is not None and file is None and first_file is None:
        file = evaluate_analyze_clip(analyze_clip, files, files_info)

    findex = files.index(file)
    clip = vs.core.lsmas.LWLibavSource(file)

    if trim_dict.get(findex) is not None:

        if trim_dict.get(findex) > 0:
            clip = clip[trim_dict.get(findex):]

        elif trim_dict.get(findex) < 0:
            #append blank clip to beginning of source to "extend" it
            clip = vs.core.std.BlankClip(clip)[:(trim_dict.get(findex) * -1)] + clip
            #keep count of how many blank frames were appended
            extended = trim_dict.get(findex) * -1

    if trim_dict_end.get(findex) is not None:
            clip = clip[:trim_dict_end.get(findex)]

    if change_fps.get(findex) is not None:
        clip = vstools.change_fps(clip, fractions.Fraction(numerator=change_fps.get(findex)[0], denominator=change_fps.get(findex)[1]))

    if return_file:
        return clip, file
    else:
        return clip

def get_suffix(file: str, files: list, files_info: list):
    """
    Gets group name from file name, otherwise just returns the file name.
    """

    findex = files.index(file)
    suffix = None

    if files_info[findex].get('release_group') is not None:
        suffix = str(files_info[findex].get('release_group'))
    if suffix is None:
        suffix = files_info[findex].get("file_name")

    return suffix

def str_to_number(string: str):
    """
    Converts a string to a float or int if possible.
    """

    try:
        float(string)
        try:
            int(string)
            return int(string)
        except:
            return float(string)
    except:
        return string
    
def extend_clip(clip: vs.VideoNode, frames: list):
    """
    If a clip is shorter than the largest frame that needs to be rendered, extend it.
    """

    if clip.num_frames < frames[-1]:
        clip = clip + (vs.core.std.BlankClip(clip)[0] * (frames[-1] - clip.num_frames + 1))

    return clip


def run_comparison():
    #START_TIME = time.time()

    global first_file
    first_file = None
    #first file is only determined by analyze_clip if it is called 

    #find video files in the current directory, and exit if there are less than two
    files = [file for file in os.listdir('.') if file.endswith(('.mkv', '.m2ts', '.mp4', '.webm'))]
    files = os_sorted(files)
    file_count = len(files)
    if file_count < 2:
        sys.exit("Not enough video files found.")

    #use anitopy library to get dictionary of show name, episode number, episode title, release group, etc
    files_info = []
    for file in files:
        files_info.append(ani.parse(file))

    anime_title = ""
    anime_episode_number = ""
    anime_episode_title = ""

    #get anime title, episode number, and episode title
    for dict in files_info:
        if dict.get('anime_title') is not None and anime_title == "":
            anime_title = dict.get('anime_title')

        if dict.get('episode_number') is not None and anime_episode_number == "":
            anime_episode_number = dict.get('episode_number')

        if dict.get('episode_title') is not None and anime_episode_title == "":
            anime_episode_title = dict.get('episode_title')

    #what to name slow.pics collection
    if anime_title != "" and anime_episode_number != "":
        collection_name = anime_title.strip() + " - " + anime_episode_number.strip()
    elif anime_title != "":
        collection_name = anime_title.strip()
    elif anime_episode_title != "":
        collection_name = anime_episode_title.strip()
    else:
        collection_name = files_info[0].get('file_name')
        collection_name = re.sub("\[.*?\]|\(.*?\}|\{.*?\}|\.[^.]+$", "", collection_name).strip()
    
    #if anime title still isn't found, give it collection name
    if anime_title == "":
        anime_title = collection_name

    #replace group or file names in trim_dict with file index
    for d in [trim_dict, trim_dict_end, change_fps]:
        for i in list(d):
            if isinstance(i, str):
                for dict in files_info:
                    if i == dict.get("release_group") or i == dict.get("file_name") or i in dict.get("file_name"):
                        d[files_info.index(dict)] = d.pop(i)

    #detects and sets up change_fps "set" feature
    if (list(change_fps.values())).count("set") > 0:
        if (list(change_fps.values())).count("set") > 1:
            sys.exit('ERROR: More than one change_fps file using "set".')
        
        #if "set" is found, get the index of its file, get its fps, and set every other unspecified file to that fps
        findex = list(change_fps.keys())[list(change_fps.values()).index("set")]
        del change_fps[findex]
        file = files[findex]
        temp_clip = vs.core.lsmas.LWLibavSource(file)
        fps = [temp_clip.fps_num, temp_clip.fps_den]

        for i in range(0, len(files)):
            if i not in change_fps:
                change_fps[i] = fps

    #if file is already set to certain fps, remove it from change_fps
    for findex, file in enumerate(files):
        temp_clip = init_clip(file, files, trim_dict, trim_dict_end)
        if change_fps.get(findex) is not None:
            if temp_clip.fps_num / temp_clip.fps_den == change_fps.get(findex)[0] / change_fps.get(findex)[1]:
                del change_fps[findex]

    #print list of files
    print('\nFiles found: ')
    for findex, file in enumerate(files):

        #highlight group names
        groupname = files_info[findex].get("release_group")
        if groupname is not None:
            filename = file.split(groupname)
            filename = filename[0] + colorama.Fore.CYAN + groupname + colorama.Fore.YELLOW + filename[1]
        else:
            filename = files_info[findex].get("file_name")

        #output filenames
        print(colorama.Fore.YELLOW + filename + colorama.Style.RESET_ALL)

        #output which files will be trimmed
        if trim_dict.get(findex) is not None:
            if trim_dict.get(findex) >= 0:
                print(f" - Trimmed to start at frame {trim_dict.get(findex)}")
            elif trim_dict.get(findex) < 0:
                print(f" - {(trim_dict.get(findex) * -1)} frame(s) appended at start")
        if trim_dict_end.get(findex) is not None:
            if trim_dict_end.get(findex) >= 0:
                print(f" - Trimmed to end at frame {trim_dict_end.get(findex)}")
            elif trim_dict_end.get(findex) < 0:
                print(f" - Trimmed to end {trim_dict_end.get(findex) * -1} frame(s) early")
            
        if change_fps.get(findex) is not None:
            print(f" - FPS changed to {change_fps.get(findex)[0]}/{change_fps.get(findex)[1]}")
            
    print()

    #check if conflicting options are enabled
    if (upscale and single_res > 0):
        sys.exit("Can't use 'upscale' and 'single_res' functions at the same time.")

    
    
    frames = []

    #add user specified frames to list
    frames.extend(user_frames)

    #if save_frames is enabled, store generated brightness data in a text file, so they don't have to be analyzed again
    if save_frames and (frame_count_dark + frame_count_bright + frame_count_motion) > 0:
        mismatch = False
        #if frame file exists, read from it
        if os.path.exists(frame_filename) and os.stat(frame_filename).st_size > 0:

            print(f'Reading data from "{frame_filename}"...')
            with open(frame_filename) as frame_file:
                generated_frames = frame_file.readlines()

            #turn numbers into floats or ints, and get rid of newlines
            for i, v in enumerate(generated_frames):
                v = v.strip()
                generated_frames[i] = str_to_number(v)
            
            dark_list = generated_frames[generated_frames.index("dark:")+1:generated_frames.index("bright:")]
            light_list = generated_frames[generated_frames.index("bright:")+1:generated_frames.index("motion:")]
            motion_list = generated_frames[generated_frames.index("motion:")+1:]

            analyzed_file = generated_frames[generated_frames.index("analyzed_file:") + 1]
            analyzed_group = ani.parse(analyzed_file).get("release_group")
            file_trim = generated_frames[generated_frames.index("analyzed_file_trim:") + 1]
            file_trim_end = generated_frames[generated_frames.index("analyzed_file_trim:") + 2]
            file_fps_num = generated_frames[generated_frames.index("analyzed_file_fps:") + 1]
            file_fps_den = generated_frames[generated_frames.index("analyzed_file_fps:") + 2]

            #check if a file with the same group name as the analyzed file is present in our current directory
            group_found = False
            for i, dict in enumerate(files_info):
                if dict.get("release_group") is not None:
                    if dict.get("release_group").lower() == analyzed_group.lower():
                        group_found = True
                        group_file_index = files.index(dict.get("file_name"))
            
            #if file wasn't found but group name was, set file with the same group name
            if analyzed_file not in files and group_found is True:
                analyzed_file = files[group_file_index]

            #check if show name, episode number, or the release which was analyzed has changed
            if (generated_frames[generated_frames.index("show_name:") + 1] != anime_title
                or generated_frames[generated_frames.index("episode_num:") + 1] != int(anime_episode_number)
                or analyzed_file not in files):

                mismatch = True

            #check if trim for analyzed file has changed
            if mismatch == False:
                found_trim = 0
                found_trim_end = 0
                if files.index(analyzed_file) in trim_dict:
                    found_trim = trim_dict.get(files.index(analyzed_file))
                if files.index(analyzed_file) in trim_dict_end:
                    found_trim_end = trim_dict_end.get(files.index(analyzed_file))

                if (file_trim != found_trim
                    or file_trim_end != found_trim_end):
                    mismatch = True

            #check if fps of analyzed file has changed
            if mismatch == False:
                temp_clip = init_clip(analyzed_file, files, trim_dict, trim_dict_end, change_fps)
                if file_fps_num / file_fps_den != temp_clip.fps_num / temp_clip.fps_den:
                    mismatch = True


            #if mismatch is detected, re-analyze frames
            if mismatch:
                print("\nParameters have changed. Will re-analyze brightness data.\n")
                os.remove(frame_filename)

            #only spend time processing lazylist if we need to
            elif (frame_count_dark + frame_count_bright + frame_count_motion) > 0:
                clip = init_clip(files[0], files, trim_dict, trim_dict_end, change_fps, analyze_clip, files_info)
                frames.extend(lazylist(clip, frame_count_dark, frame_count_bright, frame_count_motion, frames, dark_list=dark_list, light_list=light_list, motion_list=motion_list, file=files[0], files=files, files_info=files_info))

        #if frame file does not exist or has less frames than specified, write to it
        if not os.path.exists(frame_filename) or os.stat(frame_filename).st_size == 0 or mismatch:

            #if this is the first time first_file is being called, it will be evaluated. if not, it will already be known, since it's a global variable
            first, first_file = init_clip(first_file, files, trim_dict, trim_dict_end, change_fps, analyze_clip, files_info, return_file=True)

            #get the trim
            first_trim = 0
            first_trim_end = 0
            if files.index(first_file) in trim_dict:
                first_trim = trim_dict[files.index(first_file)]
            if files.index(first_file) in trim_dict_end:
                first_trim_end = trim_dict_end[files.index(first_file)]


            frames_temp, dark_list, light_list, motion_list = lazylist(first, frame_count_dark, frame_count_bright, frame_count_motion, frames, save_frames=True, file=first_file, files=files, files_info=files_info)
            frames.extend(frames_temp)
            
            with open(frame_filename, 'w') as frame_file:

                frame_file.write(f"show_name:\n{anime_title}\nepisode_num:\n{anime_episode_number}\nanalyzed_file:\n{first_file}\nanalyzed_file_trim:\n{first_trim}\n{first_trim_end}\nanalyzed_file_fps:\n{first.fps_num}\n{first.fps_den}\ndark:\n")
                for val in dark_list:
                    frame_file.write(f"{val}\n")

                frame_file.write("bright:\n")
                for val in light_list:
                    frame_file.write(f"{val}\n")

                frame_file.write("motion:\n")
                for val in motion_list:
                    frame_file.write(f"{val}\n")

    #if save_frames isn't enabled, run lazylist
    elif (frame_count_dark + frame_count_bright + frame_count_motion) > 0:
        first, first_file = init_clip(first_file, files, trim_dict, trim_dict_end, change_fps, analyze_clip, files_info, return_file=True)
        frames.extend(lazylist(first, frame_count_dark, frame_count_bright, frame_count_motion, frames, file=first_file, files=files, files_info=files_info))

    if random_frames > 0:

        print("Getting random frames...\n")

        #get list of all frames in clip
        frame_ranges = list(range(0, init_clip(files[0], files, trim_dict, trim_dict_end, change_fps).num_frames))

        #randomly selects frames at least screen_separation seconds apart
        frame_ranges = dedupe(init_clip(files[0], files, trim_dict, trim_dict_end, change_fps), frame_ranges, random_frames, screen_separation, frames)

        frames.extend(frame_ranges)

    #remove dupes and sort
    frames = [*set(frames)]
    frames.sort()

    #if no frames selected, terminate program
    if len(frames) == 0:
        sys.exit("No frames have been selected, unable to proceed.")

    #print comma separated list of which frames have been selected
    print(f"Selected {len(frames)} frames:")
    first = True
    message = ""
    for f in frames:
        if not first:
            message+=", "
        first = False
        message+=str(f)
    print(textwrap.fill(message, os.get_terminal_size().columns), end="\n\n")



    if upscale:
        max_width, max_height, max_res_file = get_highest_res(files)

    #create screenshot directory, if one already exists delete it first
    screen_dir = pathlib.Path("./" + screen_dirname + "/")
    if os.path.isdir(screen_dir):
        shutil.rmtree(screen_dir)
    os.mkdir(screen_dir)

    #check if ffmpeg is available. if not, run script with ffmpeg disabled
    global ffmpeg
    if ffmpeg:
        try:
            subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            ffmpeg = False
            print("FFmpeg was not found. Continuing to generate screens without it.")

    print("Generating screenshots:")
    #initialize progress bar, specify information to be output
    #would use expand=True but the lazylist progress bar doesn't so i'd rather go for consistency
    with Progress(TextColumn("{task.description}"), BarColumn(), TextColumn("{task.completed}/{task.total}"), TextColumn("{task.percentage:>3.02f}%"), TimeRemainingColumn()) as progress:

        total_gen_progress = progress.add_task("[green]Total", total=len(frames) * len(files))
        file_gen_progress = progress.add_task("", total=len(frames), visible=0)

        for file in files:
            findex = files.index(file)

            clip = init_clip(file, files, trim_dict, trim_dict_end, change_fps)

            #extend clip if a frame is out of range
            clip = extend_clip(clip, frames)

            #get release group or filename of file
            suffix = get_suffix(file, files, files_info)
            #remove any characters not suited for filepath
            suffix = suffix.replace("[\\/:\"*?<>|]+", "").strip()

            if suffix == files_info[files.index(file)].get("file_name"):
                message = f'[yellow]{suffix}'
            else:
                message = f'[cyan]{suffix}'
            progress.reset(file_gen_progress, description=message, visible=1)
                
            #get matrix of clip, account for black clips added to the beginning due to negative trim
            if trim_dict.get(findex) is not None and trim_dict.get(findex) < 0:
                matrix = clip.get_frame(trim_dict.get(findex) * -1).props._Matrix
            else:
                matrix = clip.get_frame(0).props._Matrix

            #if matrix is unspecified, change it to 709
            if matrix == 2:
                matrix = 1

            #upscale depending on options selected. if none are, just convert to rgb
            if single_res > 0 and clip.height != single_res:
                #clip = clip.resize.Spline36(format=vs.RGB24, matrix_in=matrix, dither_type="error_diffusion")
                #clip = vs.core.placebo.Resample(clip, int(round(clip.width * (single_res / clip.height), 0)), single_res, filter="ewa_lanczossharp", antiring=0.6)

                clip = vs.core.resize.Spline36(clip, int(round(clip.width * (single_res / clip.height), 0)), single_res, format=vs.RGB24, matrix_in=matrix, dither_type="error_diffusion")
            elif upscale and clip.height != max_height:
                clip = vs.core.resize.Spline36(clip, int(round(clip.width * (max_height / clip.height), 0)), max_height, format=vs.RGB24, matrix_in=matrix, dither_type="error_diffusion")
            else:
                clip = clip.resize.Spline36(format=vs.RGB24, matrix_in=matrix, dither_type="error_diffusion")

            #if frame_info option selected, print frame info to screen
            if frame_info:
                clip = FrameInfo(clip, title=suffix)
            
            #generate screens
            for i, frame in enumerate(frames):

                filename = f"{screen_dir}/{frame} - {suffix}.png"

                if ffmpeg:
                    ffmpeg_line = f"ffmpeg -y -hide_banner -loglevel error -f rawvideo -video_size {clip.width}x{clip.height} -pixel_format gbrp -framerate {str(clip.fps)} -i pipe: -pred mixed -compression_level {compression} \"{filename}\""
                    try:
                        with subprocess.Popen(ffmpeg_line, stdin=subprocess.PIPE) as process:
                            #ffmpeg needs these planes to be shuffled so they are in gbrp pixel_format (the p is important, rgb24 format doesnt work)
                            clip[frame].std.ShufflePlanes([1, 2, 0], vs.RGB).output(cast(BinaryIO, process.stdin), y4m=False)
                    except:
                        None

                else:
                    vs.core.fpng.Write(clip, filename, compression=compression, overwrite=True).get_frame(frame)
                
                progress.update(total_gen_progress, advance=1)
                progress.update(file_gen_progress, advance=1)

    print()
    #print(time.time() - START_TIME)

    if slowpics:
        #time.sleep(0.5)

        browserId = str(uuid.uuid4())
        fields: Dict[str, Any] = {
            'collectionName': collection_name,
            'hentai': str(hentai_flag).lower(),
            'optimize-images': 'true',
            'browserId': browserId,
            'public': str(public_flag).lower()
        }

        if tmdbID != "":
            fields |= {'tmdbId': str(tmdbID)}
        if remove_after != "" and remove_after != 0:
            fields |= {'removeAfter': str(remove_after)}

        all_image_files = os_sorted([f for f in os.listdir(screen_dir) if f.endswith('.png')])

        #check if all image files are present before uploading. if not, wait a bit and check again. if still not, exit program
        if len(all_image_files) < len(frames) * len(files):
            time.sleep(5)
            all_image_files = os_sorted([f for f in os.listdir(screen_dir) if f.endswith('.png')])

            if len(all_image_files) < len(frames) * len(files):
                sys.exit(f'ERROR: Number of screenshots in "{screen_dirname}" folder does not match expected value.')
        
        for x in range(0, len(frames)):
            #current_comp is list of image files for this frame
            current_comp = [f for f in all_image_files if f.startswith(str(frames[x]) + " - ")]

            #add field for comparison name. after every comparison name there needs to be as many image names as there are comped video files
            fields[f'comparisons[{x}].name'] = str(frames[x])
            
            #iterate over the image files for this frame
            for imageName in current_comp:
                i = current_comp.index(imageName)
                image = pathlib.Path(f"{screen_dir}/{imageName}")
                fields[f'comparisons[{x}].imageNames[{i}]'] = os.path.basename(image.name).split(' - ', 1)[1].replace(".png", "")

                #this would upload the images all at once, but that wouldnt let us get progress
                #fields[f'comparisons[{x}].images[{i}].file'] = (image.name.split(' - ', 1)[1].replace(".png", ""), image.read_bytes(), 'image/png')

        with Session() as sess:
            sess.get('https://slow.pics/comparison')

            files = MultipartEncoder(fields, str(uuid.uuid4()))

            comp_req = sess.post(
                'https://slow.pics/upload/comparison', data=files.to_string(),
                headers=_get_slowpics_header(str(files.len), files.content_type, sess)
            )

            comp_response = comp_req.json()

            collection = comp_response["collectionUuid"]
            key = comp_response["key"]

            with Progress(TextColumn("{task.description}"), BarColumn(), TextColumn("{task.completed}/{task.total}"), TextColumn("{task.percentage:>3.02f}%"), TimeRemainingColumn()) as progress:
                upload_progress = progress.add_task("[bright_magenta]Uploading to Slowpoke Pics", total=len(all_image_files))

                for index, image_section in enumerate(comp_response["images"]):
                    base = index * file_count
                    for image_index, image_id in enumerate(image_section):

                        upload_info = {
                            "collectionUuid": collection,
                            "imageUuid": image_id,
                            "file": (all_image_files[base + image_index], pathlib.Path(f"{screen_dir}/{all_image_files[base + image_index]}").read_bytes(), 'image/png'),
                            'browserId': browserId,
                        }
                        upload_info = MultipartEncoder(upload_info, str(uuid.uuid4()))
                        upload_response = sess.post(
                            'https://slow.pics/upload/image', data=upload_info.to_string(),
                            headers=_get_slowpics_header(str(upload_info.len), upload_info.content_type, sess)
                        )

                        progress.update(upload_progress, advance=1)

                        assert upload_response.status_code == 200, "Status code not 200"
                        assert upload_response.content.decode() == "OK", "Content not OK"

        slowpics_url = f'https://slow.pics/c/{key}'
        print(f'\nSlowpoke Pics url: {slowpics_url}', end='')
        pc.copy(slowpics_url)

        if browser_open:
            webbrowser.open(slowpics_url)

        if webhook_url:
            data = {"content": slowpics_url}
            if requests.post(webhook_url, data).status_code < 300:
                print('Posted to webhook.')
            else:
                print('Failed to post on webhook!')

        if url_shortcut:
            #datetime.datetime.now().strftime("%Y.%m.%d") + " - " + 
            shortcut_path = os.path.join("Comparisons", collection_name + " - " + key + ".url")

            if not os.path.exists(os.path.dirname(shortcut_path)):
                os.mkdir(os.path.dirname(shortcut_path))

            with open(shortcut_path, "w", encoding='utf-8') as shortcut:
                shortcut.write(f'[InternetShortcut]\nURL={slowpics_url}')

        if delete_screen_dir and os.path.isdir(screen_dir):
            shutil.rmtree(screen_dir)

        time.sleep(3)

run_comparison()
