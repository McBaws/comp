# comp.py
This script was originally written for VS R53 and Python 3.9. It's been tested on VS R63 and Python 3.11.

### Prerequisites:
1. [Install Python](https://www.python.org/downloads/)

2. [Install Vapoursynth](https://github.com/vapoursynth/vapoursynth/releases)

3. Install python dependencies:
 ```powershell
 pip install pathlib anitopy pyperclip requests requests_toolbelt natsort vstools rich colorama
 ```

4. Install Vapoursynth plugin dependencies:
 ```powershell
 vsrepo install imwri lsmas sub
 ```
  - Alternatively, install the following to your usual Vapoursynth plugins folder:
    - https://github.com/AkarinVS/L-SMASH-Works/releases/latest
    - https://github.com/vapoursynth/subtext/releases/latest
    - https://github.com/vapoursynth/vs-imwri/releases/latest
    - Note: plugins folder is typically found in `%AppData%\Roaming\VapourSynth\plugins64` or `C:\Program Files\VapourSynth\plugins`
  
5. Optional: If using [ffmpeg](https://ffmpeg.org/download.html), it must be installed and in PATH.

### How to use:
- Drop comp.py into a folder with the video files you want to compare.
- (Optional) Rename your files to have typical `[Group] Show - Ep.mkv` naming, since the script will try to parse the group and show name.
  - e.g. `Youjo Senki 1.m2ts` --> `[JPBD] Youjo Senki - 01.m2ts`.
- Change variables below.
- Run comp.py.
