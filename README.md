# SF_Planet_Experiments
 Starfield planet experiments (Blender addon)

An Experimental Blender addon for editing Starfield .biom files.
**Panel Location: (N menu) -> Starfield Planets.**

# How to use
At first, you need to load .biom file.

## Drawing biomes/resources
Press `Open images folder` and find an image with the same name as your .biom file, ending with `_resources` or `_biomes`, depending on what you want to edit. Then, edit it with your image editor.
> Important: Colors should be exactly the same! No in-between, use exactly the same color palette as the original image.

## Module not found error?
Open Blender's built-in text editor and insert it there (an example with Pillow module):

```python
import sys, subprocess

subprocess.run([sys.executable, "-m", "pip", "install", "Pillow"])
```

Blender will freeze for some time, that's normal. Then, enable the addon like usually.

## Notice
Biom scripts by https://github.com/PixelRick/StarfieldScripts (MIT)