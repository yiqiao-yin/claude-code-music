"""Render the 4x version of "avenger beginning song".

Runs the same two scripts with AVENGER_SPEED=4, which re-synthesizes the score
at 4 times the tempo — 352 BPM — with the pitch left exactly where it was
written. Every absolute time constant in the synthesis (envelopes, decay rates,
reverb taps, the fade-out) scales down by the same factor, so the piece keeps its
proportions rather than turning into mud.

This is a true tempo change. It is not a resample, which would raise the pitch by
two octaves, and not a time-stretch, which would smear the brass attacks.

Outputs, alongside the 1x set:

    ../assets/avenger_beginning_song_4x.mid / .wav / .mp3
    ../assets/avenger_beginning_song_4x_visualizer.mp4
    ../structure_4x.json

    python3 make_4x.py
"""

import os
import runpy
import sys
from pathlib import Path

os.environ["AVENGER_SPEED"] = "4"
here = Path(__file__).resolve().parent
for script in ("01_make_music.py", "02_make_video.py"):
    print("--- %s at 4x ---" % script)
    sys.argv = [str(here / script)]
    runpy.run_path(str(here / script), run_name="__main__")
