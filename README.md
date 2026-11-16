![Header](https://github.com/SummerTypo/GridBoxBuilder/blob/main/img_header.png?raw=true)
# Grid Box Builder
Defining the correct grid box parameters is one of the most crucial requirements to ensure the smooth running of a molecular docking simulation. Grid Box Builder is a lightweight and straightforward tool designed to make the creation of such grid box intuitive, responsive, and flexible, in order to find the most optimized parameters possible.

This tool offers various methods to change the grid box’s position and dimensions, from tightly wrapping around a user-defined selection with a given padding (e.g. a binder of interest, a selection of choice residues defining a pocket…), to tweaking or even manually entering each value, to even rotating the Receptor in order to align the pocket area with the grid box’s sides and therefore better optimize the box’s size and position by maximizing the usefulness of the space available within.

**Target audience:**
- The format of the final grid box parameters is intended for **AutoDock Vina** and its forks.
- This is a single-file plugin designed for **PyMOL**. A version compatible with ChimeraX is planned in the near future.

## Installation
From PyMOL’s menu, open the `Plugin > Plugin Manager` pop-up window. From the `Install New Plugin` tab, you can choose to install from a local file (choose file `GridBoxBuilder-PYMOL-Plugin.py`, which is self-contained and self-sufficient), or Install from Repository by adding this repository’s URL.

After installing, the plugin can be activated via PyMOL’s menu `Plugin > Grid Box Builder`. This will create a default grid box within the open PyMOL session of dimensions 10&times;10&times;10 &angst;<sup>3</sup> located at the world origin, and a GUI panel will appear with various controls and information detailed below.

## Features

### The Grid Box
This plugin creates a group of CGO objects in the running session:
- The **box** `*_faces` and `*_edges`
- The **handles** `*_center` and `*_x`, `*_y`, `*_z` which can be moved manually during the **Live Editing** mode as one of the various ways to adjust the box’s size and location.
- The [`*_ViewportAxes`](#Viewport%20Axes)

The visibility of each element in this list can be toggled the same way as any other object, collectively or individually.

### The User Interface
#### Box Appearance
The opacity of the grid box’s faces can be adjusted. Do note however that opacity of CGO objects in PyMOL is finicky and relatively inconsistent; this is unfortunately an issue with PyMOL itself that this plugin cannot fix.

#### Draw From AutoDock Parameters
The user can copy and paste any string into the given text area, provided that it contains the grid box information in the format compatible with AutoDock and AutoDock Vina forks. Then, click on “Redraw Box.”

#### Wrap Around Selection
Define an object selection (e.g. a list of specific residues or the name of a selection object) and a padding (number in &angst;), then click on “Redraw Box.” The box object will be centered on the selection and have its size adjusted so as to fully contain the selection, plus the given padding.

#### Tweak Handle Positions
The size and center positions can be adjusted along the X, Y, Z axes independently.

#### Live Editing Mode
The `start_live` command induces a state in which the box handles’ positions are tied to the grid box. Using PyMOL’s `3-Button Editing` Mouse Mode, it becomes possible to move each handle individually.
While in Live Editing mode, a mask is placed on every object besides the box handles so that they can be grabbed and moved around easily without accidentally impacting the rest of your session. If you need to manually select or modify your receptor, you first need to disable Live Editing mode through the `stop_live` command. On the other hand, the **Rotate Receptor** mode is compatible with Live Editing mode and both can be used simultaneously.

#### Rotate Receptor
In order to allow precise fine-tuning, this plugin allows the user to adjust not only the grid box’s position, but also the receptor’s. If the receptor’s default orientation in the cartesian coordinates is noticeably unfavorable, this section allows the user to indicate a selection (by default, anything besides the grid box objects themselves), then use sliders to minutely adjust its orientation along the X, Y, Z axes independently.

### Current Box Coordinates
This section of the GUI shows the grid box’s coordinates in real time. It shows both the real on-screen values, and rounded up values in the format compatible with AutoDock Vina which can be copy-pasted at the click of a button.

### Viewport Axes
This optional object is drawn from the code shared in [this PyMOL Wiki article](https://pymolwiki.org/index.php/Axes). It represents a cartesian coordinate system which always stays in the bottom left corner of the viewport.

## Best Practices
- The Rotate Receptor section defines a selection which, by default, is `all and not <GridBoxPrefix>_*`. If you modify this selection, always make sure to exclude the grid box objects: **the grid box should not be rotated under any circumstances**.
- If you have rotated your receptor, make sure to export and use its new coordinates for the docking simulations so that the grid box parameters remain consistent with the receptor’s new orientation.
- Box parameters are rounded up to the nearest integer (&angst;) along each axis. Therefore, as a final check, it is advised to copy/paste the final grid box coordinates back into the “Draw Box from AutoDock Parameters” section to see how much it has grown and ensure that these parameters still fit your needs.

## Customization
If you intend to modify the default behavior of this plugin (e.g. name of the created objects, initial position and size, axes colors…), all values of interest are defined at the very top of the file `GridBoxBuilder-PYMOL-Plugin.py` within the “User Settings” section.
- First, the `DEFAULT` parameters list all the default values regarding the grid box’s objects and the GUI’s default behavior:
  - CGO objects:
    - `group_name`: Name of the group containing all the CGO objects related to the grid box
    - `prefix`: Common prefix given to the names of all CGO objects related to the grid box. This means that all these CGO objects can be selected at once using `<prefix>_*`
  - Default grid box appearance:
    - `alpha`: Default transparency value of the grid box faces (min 0, max 1)
    - `start_center`: Default position of the grid box center
    - `start_size`: Default distance of each axis handle away from the center (&angst;), therefore resulting in a grid box twice this size
  - Default GUI values:
    - `wrap_sele`: Default selection for the “Wrap Box Around Selection” section
    - `wrap_padding`: Default padding (&angst;) for the “Wrap Box Around Selection” section
    - `update_interval`: How often the Live Editing mode refreshes the grid box in response to the handles being moved (value in seconds)
    - `rotate_sele`: Default selection for the “Rotate Receptor” section, listing all objects which need to be rotated. Do make sure to **always exclude the grid box’s CGO objects from this selection**. This value is added to `DEFAULT` separately so that it can directly refresh alongside changes made to the value of `prefix`.
```python
DEFAULT={
    "group_name":"GridBox",
    "prefix":"GridBox",
    "alpha":.5,
    "start_center":(0,0,0),
    "start_size":(5,5,5),
    "wrap_sele":"organic",
    "wrap_padding":2.0,
    "update_interval":.3,
}
DEFAULT["rotate_sele"]=f"all and not {DEFAULT['prefix']}_*"
```
- Then, the variable `AXCOLORS` is purely for visual purposes: for the X, Y and Z axes, you can choose to change the default colors if you so wish.

## License
This tool is distributed under the Creative Commons license.
