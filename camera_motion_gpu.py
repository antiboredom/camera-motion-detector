import numpy as np
import cv2 as cv
import sys
import os
import csv
import argparse
from tqdm import tqdm
from moviepy.editor import VideoFileClip


def draw_lines(frame, flow, grid=10):
    h, w, _ = frame.shape
    for y in range(0, h, grid):
        for x in range(0, w, grid):
            flowat = flow[y, x]
            pt2 = (x + int(flowat[0]), y + int(flowat[1]))
            cv.arrowedLine(frame, (x, y), pt2, (0, 255, 0), 1)


def draw_text(frame, mag, ang, zoom_in, frame_num):
    h = 0
    s = 0.4

    cv.rectangle(frame, (0, 0), (170, 80), (255, 255, 255), -1)
    cv.putText(
        frame,
        f"Zoom: {zoom_in:.3f}",
        (10, 20),
        cv.FONT_HERSHEY_TRIPLEX,
        s,
        (0, 0, 0),
    )

    h += 15
    cv.putText(
        frame,
        f"Angle: {ang:.0f}",
        (10, 20 + h),
        cv.FONT_HERSHEY_TRIPLEX,
        s,
        (0, 0, 0),
    )

    h += 15
    cv.putText(
        frame,
        f"Mag: {mag:.4f}",
        (10, 20 + h),
        cv.FONT_HERSHEY_TRIPLEX,
        s,
        (0, 0, 0),
    )

    h += 15
    cv.putText(
        frame,
        f"{frame_num}",
        (10, 20 + h),
        cv.FONT_HERSHEY_TRIPLEX,
        s,
        (0, 0, 0),
    )


def make_empty(new_w, new_h):
    empty = []
    for y in range(new_h):
        xvals = []
        for x in range(new_w):
            xvals.append([x, y])
        empty.append(xvals)

    empty = np.array(empty)
    return empty


def process(inp, show=True):
    outname = inp + ".flow.csv"

    if os.path.exists(outname):
        print("Skipping", outname)
        return False

    clip = VideoFileClip(inp)
    frames = clip.iter_frames()

    frame_num = 1

    frame1 = next(frames)

    h, w, _ = frame1.shape
    rect_w = 300
    rect_h = 300
    rect_x = int((w / 2) - (rect_w / 2))
    rect_y = int((h / 2) - (rect_h / 2))

    frame1 = frame1[rect_y : rect_y + rect_h, rect_x : rect_x + rect_w]
    prvs = cv.cvtColor(frame1, cv.COLOR_BGR2GRAY)

    w, h, _ = frame1.shape
    empty = make_empty(w, h)
    empty_dists = np.sqrt(
        np.square(empty.ravel()[::2] - (w / 2))
        + np.square(empty.ravel()[1::2] - (h / 2))
    )

    zooms = []
    angs = []
    mags = []

    data = []

    total_frames = int(clip.fps * clip.duration)
    progress_bar = tqdm(total=total_frames)

    # create optical flow instance
    gpu_flow = cv.cuda_FarnebackOpticalFlow.create(
        5,
        0.5,
        False,
        15,
        3,
        5,
        1.2,
        0,
    )

    gpu_frame = cv.cuda_GpuMat()
    gpu_prev = cv.cuda_GpuMat()

    for frame2 in frames:
        frame_num += 1
        progress_bar.update(1)

        frame2 = frame2[rect_y : rect_y + rect_h, rect_x : rect_x + rect_w]
        next_frame = cv.cvtColor(frame2, cv.COLOR_BGR2GRAY)

        gpu_frame.upload(next_frame)
        gpu_prev.upload(prvs)

        # calculate optical flow
        flow = cv.cuda_FarnebackOpticalFlow.calc(
            gpu_flow,
            gpu_prev,
            gpu_frame,
            None,
        )

        flow_x = cv.cuda_GpuMat(flow.size(), cv.CV_32FC1)
        flow_y = cv.cuda_GpuMat(flow.size(), cv.CV_32FC1)
        cv.cuda.split(flow, [flow_x, flow_y])

        mag, ang = cv.cuda.cartToPolar(flow_x, flow_y, angleInDegrees=True)

        mean_mag = np.median(mag.download())
        mean_ang = np.median(ang.download())

        flow = flow.download()

        zoom_in_factor = 0

        # get the actual pixel coords of the flow
        flow_coords = flow + empty

        xvals = flow_coords.ravel()[::2] - (w / 2)
        yvals = flow_coords.ravel()[1::2] - (h / 2)

        # calculate the distances from center points
        dists = np.sqrt(np.square(xvals) + np.square(yvals))

        dist_diff = dists >= empty_dists
        zoom_in_factor = np.count_nonzero(dist_diff) / len(dist_diff)

        if show:
            angs.append(mean_ang)
            if len(angs) > 10:
                angs.pop(0)
            mags.append(mean_mag)
            if len(mags) > 10:
                mags.pop(0)
            zooms.append(zoom_in_factor)
            if len(zooms) > 10:
                zooms.pop(0)

            draw_lines(frame2, flow, grid=10)
            draw_text(frame2, np.mean(mags), np.mean(angs), np.mean(zooms), frame_num)
            cv.imshow("frame2", frame2)
            k = cv.waitKey(30) & 0xFF
            if k == 27:
                break

        prvs = next_frame

        data.append(
            {
                "frame": frame_num,
                "mag": mean_mag,
                "ang": mean_ang,
                "zoom": zoom_in_factor,
            }
        )

    progress_bar.close()

    if show:
        cv.destroyAllWindows()

    keys = data[0].keys()
    with open(outname, "w") as outfile:
        dict_writer = csv.DictWriter(outfile, keys)
        dict_writer.writeheader()
        dict_writer.writerows(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Detect camera motion in videos.')
    parser.add_argument(
        "--preview",
        "-p",
        dest="preview",
        action="store_true",
        help="Show preview window.",
    )
    parser.add_argument('path', nargs='+', help='Path of a video or videos.')

    args = parser.parse_args()

    files = args.path
    for f in files:
        print("Processing", f)
        try:
            process(f, show=args.preview)
        except Exception as e:
            print(e)
