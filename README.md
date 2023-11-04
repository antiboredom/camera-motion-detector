# Camera Motion Detection

This project uses optical flow to determine camera motion (pans and zooms).

NOTE: I'm not great at CV stuff so please excuse the probably not-ideal way of doing things here. And big thanks to Golan Levin and Alexander Porter for helping me figure it out...

## Usage

`detect.py` will analyze a video frame by frame and record a `csv` file containing average camera motion angle, magnitude and "zoom factor." Zoomy-ness is determined by what percentage of pixels appear to be moving *away* from the center of the image.

To run:

```
python detect.py somevideo.mp4
```

If you have CUDA you can run the GPU optimized version with:

```
python detect.py somevideo.mp4 --gpu
```

You can also preview the analysis with:

```
python detect.py somevideo.mp4 --preview
```

### Rendering out different camera motions

You can make use of the generated `csv` file in a few different ways. I've also included a `render.py` script that attempts to extract zooming and panning shots (your mileage may vary with it!).

To save out all the zoom shots:

```
python render.py somevideo.mp4 --zooms --output zooms.mp4
```

If you have mpv installed you can also preview this without rendering a new file:


```
python render.py somevideo.mp4 --zooms --preview
```

For panning shots, specify the desired panning angle like so:

```
python render.py somevideo.mp4 --pans --angle 180
```


## Installation


### CPU

Install the requirements with:

```
pip install -r requirements.txt
```

You're done!


### GPU

If you've got an nvidia card you can use the GPU version which is significantly faster. You need opencv with cuda which you can either compile yourself or use a [docker image](https://github.com/Fizmath/Docker-opencv-GPU).


