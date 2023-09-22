# comp.py
This script was originally written for VS R53 and Python 3.9. It's been tested on VS R63 and Python 3.11.

### Prerequisites:
1. [Install Vapoursynth](https://github.com/vapoursynth/vapoursynth/releases)

2. Install python dependencies:
 ```bash
 pip install pathlib anitopy pyperclip requests requests_toolbelt natsort vstools rich colorama
 ```

3. Install Vapoursynth plugin dependencies:
 ```bash
 vsrepo install imwri lsmas sub
 ```
  - Alternatively, install the following to your usual Vapoursynth plugins folder:
    - https://github.com/AkarinVS/L-SMASH-Works/releases/latest
    - https://github.com/vapoursynth/subtext/releases/latest
    - https://github.com/vapoursynth/vs-imwri/releases/latest
    - Note: plugins folder is typically found in `%AppData%\Roaming\VapourSynth\plugins64` or `C:\Program Files\VapourSynth\plugins`
  
4. Optional: If using [ffmpeg](https://ffmpeg.org/download.html), it must be installed and in PATH.

### How to use:
- Drop comp.py into a folder with the video files you want to compare.
- (Optional) Rename your files to have typical `[Group] Show - Ep.mkv` naming, since the script will try to parse the group and show name.
  - e.g. `[JPBD] Youjo Senki - 01.m2ts`; `[Vodes] Youjo Senki - 01.mkv`.
- Change variables below.
- Run comp.py.
