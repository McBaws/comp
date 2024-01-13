# comp.py
This script was originally written for VS R53 and Python 3.9, and has been tested on VS R65 and Python 3.11.

### Prerequisites:
1. [Install Python](https://www.python.org/downloads/)

2. [Install Vapoursynth](https://github.com/vapoursynth/vapoursynth/releases)

3. Install Python dependencies:
 ```powershell
 pip install pathlib anitopy pyperclip requests requests_toolbelt natsort vstools rich colorama
 ```

4. Install Vapoursynth plugin dependencies:
 ```powershell
 vsrepo install fpng lsmas sub
 ```
  - Alternatively, install the following to your usual Vapoursynth plugins folder:
    - https://github.com/Mikewando/vsfpng
    - https://github.com/AkarinVS/L-SMASH-Works/releases/latest
    - https://github.com/vapoursynth/subtext/releases/latest
    - Note: plugins folder is typically found in `%AppData%\Roaming\VapourSynth\plugins64` or `C:\Program Files\VapourSynth\plugins`
  
5. Optional: If using [FFmpeg](https://ffmpeg.org/download.html), it must be installed and in PATH.

### How to use:
- Put `comp.py` into the same folder where the video files you want to compare are located.
- (Optional) Rename your files to have typical `[Group] Show - Ep.mkv` naming if they don't, since the script will try to parse the group and show name.
  - e.g. `Youjo Senki 1.m2ts` --> `[JPBD] Youjo Senki - 01.m2ts`.
- Adjust the variables in the script accordingly.
- Run the script by double-clicking it or by running `py comp.py` in your terminal.
