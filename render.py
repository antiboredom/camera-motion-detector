import sys
import csv
from subprocess import check_output, call
from moviepy.editor import VideoFileClip, concatenate_videoclips


def render(clips, outname="camera_motion.mp4"):
    videos = {}
    output = []
    for start, end, filename in clips:
        if filename not in videos:
            videos[filename] = VideoFileClip(filename)
        vid = videos[filename]
        output.append(vid.subclip(start, end))
    everything = concatenate_videoclips(output)
    everything.write_videofile(outname)


def write_edl(clips, outname=None):

    if outname is not None:
        outlines = ["# mpv EDL v0"]

        for start, end, filename in clips:
            duration = end - start
            outlines.append(f"{filename},{start},{duration}")
        with open(outname, "w") as outfile:
            outfile.write("\n".join(outlines))
    else:
        edl = "edl://"
        for start, end, filename in clips:
            edl += f"{filename},length={end-start},start={start};"
        print(edl)
        call(["mpv", edl])


def f_to_s(f, fps=60):
    return f / fps


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


def get_zooms(
    vidname,
    min_zoomin=0.82,
    min_mag=5.0,
    min_zoom_time=0.1,
    pad_before=0.3,
    pad_after=0.3,
):
    csvname = vidname + ".flow.csv"

    clips = []

    fps = get_fps(vidname)

    with open(csvname, "r") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            zoomin_factor = float(row["zoom"])
            mag = float(row["mag"])
            frame = int(row["frame"])

            zooming = zoomin_factor > min_zoomin and mag > min_mag

            if not zooming:
                continue

            start = f_to_s(frame, fps) - pad_before
            end = start + pad_after + pad_before

            if len(clips) > 0:
                if clips[-1][1] > start:
                    clips[-1][1] = end
                else:
                    clips.append([start, end, vidname])
            else:
                clips.append([start, end, vidname])

    print(clips)
    clips = [c for c in clips if c[1] - c[0] >= min_zoom_time]
    return clips


def get_pans(
    vidname,
    desired_angle=180,
    angle_thresh=10,
    desired_mag=10,
    mag_thresh=10,
    min_frames=3,
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
                # and z < 0.7
                # and z > 0.4
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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Render just pans or zooms from a video."
    )

    parser.add_argument(
        "--preview",
        "-p",
        dest="preview",
        action="store_true",
        help="Show preview with mpv (if installed)",
    )

    parser.add_argument(
        "--zooms",
        "-z",
        dest="zooms",
        action="store_true",
        help="Get zooms",
    )

    parser.add_argument(
        "--zoom-thresh",
        dest="min_zoomin",
        type=float,
        default=0.92,
        help="Minimum 'zoom factor'",
    )

    parser.add_argument(
        "--pad-start",
        dest="pad_before",
        type=float,
        default=0.3,
        help="Time in seconds to add before zoom",
    )

    parser.add_argument(
        "--pad-end",
        dest="pad_after",
        type=float,
        default=0.3,
        help="Time in seconds to add after zoom",
    )

    parser.add_argument(
        "--min-mag",
        dest="min_mag",
        type=float,
        default=5.0,
        help="Minimum magnitude",
    )

    parser.add_argument(
        "--pans",
        dest="pans",
        action="store_true",
        help="Get pans",
    )

    parser.add_argument(
        "--angle",
        dest="angle",
        type=int,
        default=180,
        help="Desired pan angle",
    )

    parser.add_argument(
        "--output",
        dest="output",
        default=None,
        help="File to save supercut to",
    )

    parser.add_argument("path", nargs="+", help="Path of a video or videos.")

    args = parser.parse_args()

    for f in args.path:
        if args.zooms:
            clips = get_zooms(
                f,
                min_zoomin=args.min_zoomin,
                min_mag=args.min_mag,
                pad_before=args.pad_before,
                pad_after=args.pad_after,
            )
        elif args.pans:
            clips = get_pans(f, desired_angle=args.angle)
        else:
            clips = []

        if len(clips) > 0:
            if args.preview:
                write_edl(clips)
            if args.output is not None:
                render(clips, args.output)
        # get_pans(f)
