import sys
import csv
from subprocess import check_output
from moviepy.editor import VideoFileClip, concatenate_videoclips


def f_to_s(f, fps=60):
    return f / fps


def write_edl(clips, outname):
    outlines = ["# mpv EDL v0"]

    for start, end, filename in clips:
        duration = end - start
        outlines.append(f"{filename},{start},{duration}")

    with open(outname, "w") as outfile:
        outfile.write("\n".join(outlines))


def get_fps(filename):
    args = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        "-show_entries",
        "stream=r_frame_rate",
        filename,
    ]

    fps = check_output(args).decode("utf-8")
    a, b = fps.split("/")
    fps = int(a) / int(b)
    return fps


def get_zooms(vidname, min_zoomin=0.92, min_mag=5.0, min_zoom_time=0.3):
    csvname = vidname + ".flow.csv"

    clips = []

    fps = get_fps(vidname)

    frames = []

    with open(csvname, "r") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            zoomin_factor = float(row["zoom"])
            ang = float(row["ang"])
            mag = float(row["mag"])
            frame = int(row["frame"])

            zooming = zoomin_factor > min_zoomin and mag > min_mag

            if not zooming:
                continue

            start = f_to_s(frame, fps) - 0.1
            end = start + 0.1

            if len(clips) > 0:
                if clips[-1][1] > start:
                    clips[-1][1] = end
                else:
                    clips.append([start, end, vidname])
            else:
                clips.append([start, end, vidname])

    clips = [c for c in clips if c[1] - c[0] >= min_zoom_time]
    return clips


def get_pans(
    vidname,
    desired_angle=180,
    angle_thresh=10,
    desired_mag=20,
    mag_thresh=10,
    min_frames=10,
):
    csvname = vidname + ".flow.csv"

    clips = []

    fps = get_fps(vidname)

    start = None
    end = None
    hits = 0

    max_bads = 0
    total_bads = 0

    with open(csvname, "r") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            z = float(row["zoom"])
            ang = float(row["ang"])
            mag = float(row["mag"])
            frame = int(row["frame"])

            if (
                abs(ang - desired_angle) < angle_thresh
                and abs(mag - desired_mag) < mag_thresh
                and z < 0.7
                and z > 0.4
            ):
                if start is None:
                    start = frame
                hits += 1
            else:
                total_bads += 1

                if total_bads > max_bads:
                    if start is not None and hits >= min_frames:
                        end = frame - 1
                        clips.append([f_to_s(start, fps), f_to_s(end, fps), vidname])

                    hits = 0
                    start = None
                    end = None
                    total_bads = 0
    return clips


def render(clips):
    pass


if __name__ == "__main__":

    for f in sys.argv[1:]:
        clips = get_zooms(f)
        write_edl(clips, f + ".preview.edl")
        # get_pans(f)
