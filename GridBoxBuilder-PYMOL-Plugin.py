from pymol.cgo import *
import threading
import time
import math
import re
from pymol.Qt import QtWidgets,QtCore
from pymol import cmd, gui
from chempy import cpv
##############################################################################################################
##                                                                                                          ##
##   ██    ██ ███████ ███████ ██████      ███████ ███████ ████████ ████████ ██ ███    ██  ██████  ███████   ##
##   ██    ██ ██      ██      ██   ██     ██      ██         ██       ██    ██ ████   ██ ██       ██        ##
##   ██    ██ ███████ █████   ██████      ███████ █████      ██       ██    ██ ██ ██  ██ ██   ███ ███████   ##
##   ██    ██      ██ ██      ██   ██          ██ ██         ██       ██    ██ ██  ██ ██ ██    ██      ██   ##
##    ██████  ███████ ███████ ██   ██     ███████ ███████    ██       ██    ██ ██   ████  ██████  ███████   ##
##                                                                                                          ##
##############################################################################################################
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
AXCOLORS={
    "x":{
        "RGB":(1,0,0),
        "str":"red",
        "background":"#ff4d4d",
        "main_color":"#cc0000",
    },
    "y":{
        "RGB":(0,1,0),
        "str":"green",
        "background":"#4dff88",
        "main_color":"#00aa44",
    },
    "z":{
        "RGB":(0,0,1),
        "str":"blue",
        "background":"#4da6ff",
        "main_color":"#0055cc",
    }
}
##############################################################################################################
##                                                                                                          ##
##                                   ██    ██ ████████ ██ ██      ███████                                   ##
##                                   ██    ██    ██    ██ ██      ██                                        ##
##                                   ██    ██    ██    ██ ██      ███████                                   ##
##                                   ██    ██    ██    ██ ██           ██                                   ##
##                                    ██████     ██    ██ ███████ ███████                                   ##
##                                                                                                          ##
##############################################################################################################
_running=False
updating_ui=False
BOX_UI={}
current_angles={'x':0.0,'y':0.0,'z':0.0}
previousangles=current_angles.copy()
def round_up(x,decimals=0):
    factor=10**decimals
    if x<0:
        return -math.ceil(-x*factor)/factor
    else:
        return math.ceil(x*factor)/factor
def quad(a,b,c,d,color):
    return[
        COLOR,*color,
        VERTEX,*a,VERTEX,*b,VERTEX,*c,
        VERTEX,*a,VERTEX,*c,VERTEX,*d
    ]
def parse_vina_params(text):
    required=[
        "center_x","center_y","center_z",
        "size_x",  "size_y",  "size_z"
    ]
    params={k:float(v)for k,v in re.compile(r"(size_[xyz]|center_[xyz])\s*=\s*([-+]?\d*\.?\d+)").findall(text)}
    missing=[k for k in required if k not in params]
    if missing:
        raise ValueError(f"Missing parameters: {missing}")
    return params
##############################################################################################################
##                                                                                                          ##
##    ██    ██ ██ ███████ ██     ██ ██████   ██████  ██████  ████████      █████  ██   ██ ███████ ███████   ##
##    ██    ██ ██ ██      ██     ██ ██   ██ ██    ██ ██   ██    ██        ██   ██  ██ ██  ██      ██        ##
##    ██    ██ ██ █████   ██  █  ██ ██████  ██    ██ ██████     ██        ███████   ███   █████   ███████   ##
##     ██  ██  ██ ██      ██ ███ ██ ██      ██    ██ ██   ██    ██        ██   ██  ██ ██  ██           ██   ##
##      ████   ██ ███████  ███ ███  ██       ██████  ██   ██    ██        ██   ██ ██   ██ ███████ ███████   ##
##                                                                                                          ##
##                    This section was adapted from https://pymolwiki.org/index.php/Axes                    ##
##                   It is fully optional in regards to the functionality of this plugin.                   ##
##############################################################################################################
class PutCenterCallback(object):
    prev_v=None
    def __init__(self,name,corner=0):
        self.name=name
        self.corner=corner
        self.cb_name=cmd.get_unused_name('_cb')
    def load(self):
        cmd.load_callback(self,self.cb_name)
    def __call__(self):
        if self.name not in cmd.get_names('objects'):
            try:
                cmd.delete(self.cb_name)
            except:
                pass
            return
        v=cmd.get_view()
        if v==self.prev_v:
            return
        self.prev_v=v
        t=v[12:15]
        if self.corner:
            vp=cmd.get_viewport()
            R_mc=[v[0:3],v[3:6],v[6:9]]
            off_c=[.15*v[11]*vp[0]/vp[1],.15*v[11],.0]
            if self.corner in[2,3]:
                off_c[0]*=-1
            if self.corner in[3,4]:
                off_c[1]*=-1
            off_m=cpv.transform(R_mc,off_c)
            t=cpv.add(t,off_m)
        z=-v[11]/30.0
        m=[z,0,0,0,0,z,0,0,0,0,z,0,t[0]/z,t[1]/z,t[2]/z,1]
        cmd.set_object_ttt(self.name,m)
def draw_axes(name=DEFAULT["prefix"]+'_ViewportAxes',groupname=DEFAULT["group_name"]):
    w=.06;l=.75;h=.25;d=w*1.618
    obj=[
        CYLINDER,  0,0,0, l,0,0, w,*AXCOLORS["x"]["RGB"],*AXCOLORS["x"]["RGB"],
        CYLINDER,  0,0,0, 0,l,0, w,*AXCOLORS["y"]["RGB"],*AXCOLORS["y"]["RGB"],
        CYLINDER,  0,0,0, 0,0,l, w,*AXCOLORS["z"]["RGB"],*AXCOLORS["z"]["RGB"],
        CONE,l,0,0, h+l,0,0, d,0.0,*AXCOLORS["x"]["RGB"],*AXCOLORS["x"]["RGB"],1,1,
        CONE,0,l,0, 0,h+l,0, d,0.0,*AXCOLORS["y"]["RGB"],*AXCOLORS["y"]["RGB"],1,1,
        CONE,0,0,l, 0,0,h+l, d,0.0,*AXCOLORS["z"]["RGB"],*AXCOLORS["z"]["RGB"],1,1
    ]
    PutCenterCallback(name,1).load()
    cmd.load_cgo(obj,name)
    cmd.group(groupname,name)
##############################################################################################################
##                                                                                                          ##
##      ██████  ██████   █████  ██     ██      ██████  ██████  ██ ██████      ██████   ██████  ██   ██      ##
##      ██   ██ ██   ██ ██   ██ ██     ██     ██       ██   ██ ██ ██   ██     ██   ██ ██    ██  ██ ██       ##
##      ██   ██ ██████  ███████ ██  █  ██     ██   ███ ██████  ██ ██   ██     ██████  ██    ██   ███        ##
##      ██   ██ ██   ██ ██   ██ ██ ███ ██     ██    ██ ██   ██ ██ ██   ██     ██   ██ ██    ██  ██ ██       ##
##      ██████  ██   ██ ██   ██  ███ ███       ██████  ██   ██ ██ ██████      ██████   ██████  ██   ██      ##
##                                                                                                          ##
##############################################################################################################
#  Faces & Edges
# ------------------------------------------------------------------------------------------------------------
def draw_box(min_c,max_c,face_alpha,boxname=DEFAULT["prefix"],groupname=DEFAULT["group_name"]):
    x1,y1,z1=min_c
    x2,y2,z2=max_c
    obj=[BEGIN,TRIANGLES,ALPHA,face_alpha]
    obj+=quad((x1,y1,z1),(x1,y1,z2),(x1,y2,z2),(x1,y2,z1),AXCOLORS["x"]["RGB"])
    obj+=quad((x2,y1,z1),(x2,y1,z2),(x2,y2,z2),(x2,y2,z1),AXCOLORS["x"]["RGB"])
    obj+=quad((x1,y1,z1),(x2,y1,z1),(x2,y1,z2),(x1,y1,z2),AXCOLORS["y"]["RGB"])
    obj+=quad((x1,y2,z1),(x2,y2,z1),(x2,y2,z2),(x1,y2,z2),AXCOLORS["y"]["RGB"])
    obj+=quad((x1,y1,z1),(x2,y1,z1),(x2,y2,z1),(x1,y2,z1),AXCOLORS["z"]["RGB"])
    obj+=quad((x1,y1,z2),(x2,y1,z2),(x2,y2,z2),(x1,y2,z2),AXCOLORS["z"]["RGB"])
    obj+=[END]
    obje=[LINEWIDTH,3.0,BEGIN,LINES,COLOR,1,1,1]
    v=[(x1,y1,z1),(x2,y1,z1),(x2,y2,z1),(x1,y2,z1),(x1,y1,z2),(x2,y1,z2),(x2,y2,z2),(x1,y2,z2)]
    edges=[(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    for a,b in edges:obje+=[VERTEX,*v[a],VERTEX,*v[b]]
    obje+=[END]
    cmd.delete(boxname+"_edges")
    cmd.load_cgo(obje,boxname+"_edges")
    cmd.group(groupname,boxname+"_edges")
    return obj
# ------------------------------------------------------------------------------------------------------------
#  Center & Handles
# ------------------------------------------------------------------------------------------------------------
def init_box(
    boxname=DEFAULT["prefix"],
    groupname=DEFAULT["group_name"],
    center=DEFAULT["start_center"],
    size=DEFAULT["start_size"],
    face_alpha=DEFAULT["alpha"]
):
    cx,cy,cz=center
    sx,sy,sz=size
    cmd.delete(boxname+"_*")
    cmd.pseudoatom(boxname+"_center",pos=(cx,cy,cz))
    cmd.pseudoatom(boxname+"_x",pos=(cx+sx,cy,cz))
    cmd.pseudoatom(boxname+"_y",pos=(cx,cy+sy,cz))
    cmd.pseudoatom(boxname+"_z",pos=(cx,cy,cz+sz))
    cmd.color(AXCOLORS["x"]["str"],boxname+"_x")
    cmd.color(AXCOLORS["y"]["str"],boxname+"_y")
    cmd.color(AXCOLORS["z"]["str"],boxname+"_z")
    cmd.show("nonbonded",boxname+"_*")
    cmd.set("nonbonded_size",1,boxname+"_*")
    cmd.alter_state(1,boxname+"_*",f"vdw=.5")
    cmd.alter_state(1,boxname+"_center",f"vdw=.8")
    cmd.show("dots",boxname+"_*")
    cmd.set("dot_density",3,boxname+"_*")
    cmd.group(groupname,boxname+"_*")
    cmd.set("defer_updates",0)
# ------------------------------------------------------------------------------------------------------------
#  Update Objects
# ------------------------------------------------------------------------------------------------------------
def redraw(boxname=DEFAULT["prefix"],groupname=DEFAULT["group_name"],face_alpha=DEFAULT["alpha"],min_c=None,max_c=None):
    if min_c is None or max_c is None:
        min_c,max_c=compute_box(boxname)
    cmd.delete(boxname+"_faces")
    cmd.load_cgo(draw_box(min_c,max_c,face_alpha=DEFAULT["alpha"]),boxname+"_faces")
    cmd.group(groupname,boxname+"_*")
    center=[(min_c[i]+max_c[i])/2 for i in range(3)]
    size=[max_c[i]-min_c[i]for i in range(3)]
    gridbox=[(
        f"size_x = {int(round_up(size[0]))}\n"
        f"size_y = {int(round_up(size[1]))}\n"
        f"size_z = {int(round_up(size[2]))}\n"
        "center_x = "+"{:.3f}".format(round_up(center[0],3))+"\n"
        "center_y = "+"{:.3f}".format(round_up(center[1],3))+"\n"
        "center_z = "+"{:.3f}".format(round_up(center[2],3))+"\n"
    ),(
        f"BOX SIZE X: {size[0]}\n"
        f"BOX SIZE Y: {size[1]}\n"
        f"BOX SIZE Z: {size[2]}\n"
        f"BOX CENTER X: {center[0]}\n"
        f"BOX CENTER Y: {center[1]}\n"
        f"BOX CENTER Z: {center[2]}"
    )]
    try:
        boxupdater.text_updated.emit(*gridbox)
    except:
        pass
    boxupdater.spinbox_updated.emit(*get_handlers(boxname))
##############################################################################################################
##                                                                                                          ##
##             ██      ██ ██    ██ ███████     ██    ██ ██████  ██████   █████  ████████ ███████            ##
##             ██      ██ ██    ██ ██          ██    ██ ██   ██ ██   ██ ██   ██    ██    ██                 ##
##             ██      ██ ██    ██ █████       ██    ██ ██████  ██   ██ ███████    ██    █████              ##
##             ██      ██  ██  ██  ██          ██    ██ ██      ██   ██ ██   ██    ██    ██                 ##
##             ███████ ██   ████   ███████      ██████  ██      ██████  ██   ██    ██    ███████            ##
##                                                                                                          ##
##                  This functionality allows the user to manually move the box handles and                 ##
##             have the grid box redrawn in order to adapt to their new positions in real time.             ##
##############################################################################################################
def live_update(boxname=DEFAULT["prefix"],interval=DEFAULT["update_interval"]):
    global _running
    last=None
    while _running:
        try:
            current=tuple(tuple(cmd.get_coords(boxname+"_"+p)[0])for p in["center","x","y","z"])
            if current!=last:
                last=current
                move_handlers(boxname)
                redraw(boxname)
        except:
            print("Live update error:",e)
        time.sleep(interval)
def start_live(boxname=DEFAULT["prefix"]):
    global _running
    _running=True
    t=threading.Thread(target=live_update,args=(boxname,),daemon=True)
    t.start()
    cmd.mask(f"all and not {DEFAULT['prefix']}_*")
def stop_live():
    global _running
    cmd.unmask(f"all and not {DEFAULT['prefix']}_*")
    _running=False
##############################################################################################################
##                                                                                                          ##
##         ███████ ██████  ██ ████████      ██████  ██████  ██ ██████      ██████   ██████  ██   ██         ##
##         ██      ██   ██ ██    ██        ██       ██   ██ ██ ██   ██     ██   ██ ██    ██  ██ ██          ##
##         █████   ██   ██ ██    ██        ██   ███ ██████  ██ ██   ██     ██████  ██    ██   ███           ##
##         ██      ██   ██ ██    ██        ██    ██ ██   ██ ██ ██   ██     ██   ██ ██    ██  ██ ██          ##
##         ███████ ██████  ██    ██         ██████  ██   ██ ██ ██████      ██████   ██████  ██   ██         ##
##                                                                                                          ##
##############################################################################################################
#  Helpers
# ------------------------------------------------------------------------------------------------------------
def get_handlers(boxname=DEFAULT["prefix"]):
    c =tuple(cmd.get_coords(boxname+"_center")[0])
    px=tuple(cmd.get_coords(boxname+"_x")[0])
    py=tuple(cmd.get_coords(boxname+"_y")[0])
    pz=tuple(cmd.get_coords(boxname+"_z")[0])
    return c,px,py,pz
def compute_box(boxname=DEFAULT["prefix"]):
    c,px,py,pz=get_handlers(boxname)
    dx=abs(px[0]-c[0])
    dy=abs(py[1]-c[1])
    dz=abs(pz[2]-c[2])
    return(c[0]-dx,c[1]-dy,c[2]-dz),(c[0]+dx,c[1]+dy,c[2]+dz)
def move_handlers(boxname=DEFAULT["prefix"]):
    c,px,py,pz=get_handlers(boxname)
    cmd.alter_state(1,boxname+"_x",f"(x,y,z)=({px[0]},{c[1]},{c[2]})")
    cmd.alter_state(1,boxname+"_y",f"(x,y,z)=({c[0]},{py[1]},{c[2]})")
    cmd.alter_state(1,boxname+"_z",f"(x,y,z)=({c[0]},{c[1]},{pz[2]})")
    cmd.rebuild()
# ------------------------------------------------------------------------------------------------------------
#  Grid Box Appearance
# ------------------------------------------------------------------------------------------------------------
def faces_opacity(alpha=DEFAULT["alpha"],boxname=DEFAULT["prefix"]):
    DEFAULT["alpha"]=alpha
    cmd.set("cgo_transparency",alpha,boxname+"_faces")
    redraw(boxname)
# ------------------------------------------------------------------------------------------------------------
#  Wrap Grid Box Around Selection
# ------------------------------------------------------------------------------------------------------------
def wrapsel(selection,padding,boxname=DEFAULT["prefix"]):
    (minX,minY,minZ),(maxX,maxY,maxZ)=cmd.get_extent(selection)
    new_min=[minX-padding,minY-padding,minZ-padding]
    new_max=[maxX+padding,maxY+padding,maxZ+padding]
    cx=(new_min[0]+new_max[0])/2
    cy=(new_min[1]+new_max[1])/2
    cz=(new_min[2]+new_max[2])/2
    sx=abs(new_max[0]-new_min[0])/2
    sy=abs(new_max[1]-new_min[1])/2
    sz=abs(new_max[2]-new_min[2])/2
    cmd.alter_state(1,boxname+"_center",f"(x,y,z)=({cx},{cy},{cz})")
    cmd.alter_state(1,boxname+"_x",f"(x,y,z)=({cx+sx},{cy},{cz})")
    cmd.alter_state(1,boxname+"_y",f"(x,y,z)=({cx},{cy+sy},{cz})")
    cmd.alter_state(1,boxname+"_z",f"(x,y,z)=({cx},{cy},{cz+sz})")
    cmd.rebuild()
    redraw(boxname)
    print(f"Wrapped box around '{selection}' with padding {padding} Å.")
##############################################################################################################
##                                                                                                          ##
##                     ██████  ██    ██ ██     ███████ ███████ ████████ ██    ██ ██████                     ##
##                    ██       ██    ██ ██     ██      ██         ██    ██    ██ ██   ██                    ##
##                    ██   ███ ██    ██ ██     ███████ █████      ██    ██    ██ ██████                     ##
##                    ██    ██ ██    ██ ██          ██ ██         ██    ██    ██ ██                         ##
##                     ██████   ██████  ██     ███████ ███████    ██     ██████  ██                         ##
##                                                                                                          ##
##############################################################################################################
#  GUI Appearance: Helpers
# ------------------------------------------------------------------------------------------------------------
def setQDoubleSpinStyle(qbox,axis,extra_main=""):
    qbox.setStyleSheet((
        "QDoubleSpinBox{"
            f"background:{AXCOLORS[axis]['background']};"
            f"border:1px solid {AXCOLORS[axis]['main_color']};"
            "border-radius:6px;padding:1px 1px 1px 7px;"
            f"{extra_main}"
        "}"
        "QDoubleSpinBox::up-button,QDoubleSpinBox::down-button{}"
        "QDoubleSpinBox::up-arrow,QDoubleSpinBox::down-arrow{}"
    ))
def set_textbox_height(widget,lines=7,padding=2):
    fm=widget.fontMetrics()
    widget.setMinimumHeight(fm.lineSpacing()*lines-padding)
    widget.setMaximumHeight(fm.lineSpacing()*lines-padding)
    widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Fixed)
# ------------------------------------------------------------------------------------------------------------
#  GUI Custom Widget : CollapsibleBox
# ------------------------------------------------------------------------------------------------------------
class CollapsibleBox(QtWidgets.QWidget):
    def __init__(
        self,title="",open=False,parent=None,spacing=0,
        bold=True,color="#000",background="#fafafa",border="1px solid #ccc"
    ):
        super().__init__(parent)
        self._open=open
        self.toggle_button=QtWidgets.QToolButton(text=title,checkable=True)
        self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
        self.toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        stylesheet="""
            QToolButton{
                border:none;
                padding:2px;
                qproperty-iconSize:10px;
        """
        if bold:
            stylesheet+="font-weight:600;\n"
        stylesheet+="\n}"
        self.toggle_button.setStyleSheet(stylesheet)
        self.toggle_button.clicked.connect(self.on_toggle)
        self.content_area=QtWidgets.QWidget()
        self.container=QtWidgets.QFrame()
        self.container.setObjectName("collapsibleFrame")
        self.container.setStyleSheet(
        "QFrame#collapsibleFrame{"
            f"color:{color};"
            f"border:{border};"
            "border-radius:6px;"
            f"background:{background};"
        "}")
        self.container_layout=QtWidgets.QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(3,3,3,3)
        self.container_layout.setSpacing(spacing)
        self.container_layout.addWidget(self.toggle_button)
        self.container_layout.addWidget(self.content_area)
        self.main_layout=QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.addWidget(self.container)
        self.main_layout.setSpacing(spacing)
        self.set_open(self._open)
    def on_toggle(self):
        self.set_open(self.toggle_button.isChecked())
    def set_open(self,state:bool):
        self.toggle_button.setChecked(state)
        self.toggle_button.setArrowType(QtCore.Qt.DownArrow if state else QtCore.Qt.RightArrow)
        self.content_area.setVisible(state)
    def setLayout(self,layout):
        old_layout=self.content_area.layout()
        if old_layout is not None:
            QtWidgets.QWidget().setLayout(old_layout)
        self.content_area.setLayout(layout)
# ------------------------------------------------------------------------------------------------------------
#  Auto Update GUI Text
# ------------------------------------------------------------------------------------------------------------
class BoxUpdater(QtCore.QObject):
    text_updated=QtCore.Signal(str,str)
    spinbox_updated=QtCore.Signal(tuple,tuple,tuple,tuple)
boxupdater=BoxUpdater()
##############################################################################################################
##                                                                                                          ##
##                  ██████ ██████  ███████  █████  ████████ ███████      ██████  ██    ██ ██                ##
##                 ██      ██   ██ ██      ██   ██    ██    ██          ██       ██    ██ ██                ##
##                 ██      ██████  █████   ███████    ██    █████       ██   ███ ██    ██ ██                ##
##                 ██      ██   ██ ██      ██   ██    ██    ██          ██    ██ ██    ██ ██                ##
##                  ██████ ██   ██ ███████ ██   ██    ██    ███████      ██████   ██████  ██                ##
##                                                                                                          ##
##############################################################################################################
def dockingBoxGUI(_Qtcheck,boxname=DEFAULT["prefix"]):
    # --------------------------------------------------------------------------------------------------------
    #  Create Widget
    # --------------------------------------------------------------------------------------------------------
    main_window=gui.get_qtwindow()
    dock=QtWidgets.QDockWidget("Grid Box Builder",main_window)
    dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea)
    if hasattr(gui,"_boxdock"):
        gui._boxdock.close()
    gui._boxdock=dock
    scroll=QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    widget=QtWidgets.QWidget()
    layout=QtWidgets.QVBoxLayout(widget)
    layout.setAlignment(QtCore.Qt.AlignTop)
    # --------------------------------------------------------------------------------------------------------
    #  GUI SECTION: Box Appearance
    # --------------------------------------------------------------------------------------------------------
    group=CollapsibleBox("Box Appearance",bold=False,background="""qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(75,0,130,25),
        stop:0.2 rgba(0,0,255,25),
        stop:0.4 rgba(0,255,0,25),
        stop:0.6 rgba(255,255,0,25),
        stop:0.8 rgba(255,127,0,25),
        stop:1 rgba(255,0,0,25)
    )""")
    g_layout=QtWidgets.QFormLayout()
    g_layout.setSpacing(2)
    opacity_input=QtWidgets.QDoubleSpinBox()
    opacity_input.setValue(DEFAULT["alpha"])
    opacity_input.setMinimum(0)
    opacity_input.setMaximum(1)
    opacity_input.setSingleStep(.1)
    g_layout.addRow("Opacity:",opacity_input)
    def boxstyle_action(_Qtcheck,boxname=boxname):
        try:
            faces_opacity(opacity_input.value(),boxname)
        except Exception as e:
            print("Error:",e)
    opacity_input.valueChanged.connect(boxstyle_action)
    group.setLayout(g_layout)
    layout.addWidget(group)
    # --------------------------------------------------------------------------------------------------------
    #  GUI SECTION: Draw Exact Box
    # --------------------------------------------------------------------------------------------------------
    group=CollapsibleBox("Draw Box From AutoDock Parameters")
    g_layout=QtWidgets.QFormLayout()
    g_layout.setSpacing(2)
    params_input=QtWidgets.QTextEdit()
    set_textbox_height(params_input)
    params_input.setPlaceholderText("size_x = 10\nsize_y = 10\nsize_z = 10\ncenter_x = 0\ncenter_y = 0\ncenter_z = 0")
    g_layout.addRow(params_input)
    def redraw_action(_Qtcheck,boxname=boxname):
        try:
            text=params_input.toPlainText()
            p=parse_vina_params(text)
            cx,cy,cz=p["center_x"],p["center_y"],p["center_z"]
            sx,sy,sz=p["size_x"],p["size_y"],p["size_z"]
            redraw(min_c=(cx-sx/2,cy-sy/2,cz-sz/2),max_c=(cx+sx/2,cy+sy/2,cz+sz/2),boxname=boxname)
            cmd.alter_state(1,boxname+"_center",f"(x,y,z)=({cx},{cy},{cz})")
            cmd.alter_state(1,boxname+"_x",f"(x,y,z)=({cx+sx/2},{cy},{cz})")
            cmd.alter_state(1,boxname+"_y",f"(x,y,z)=({cx},{cy+sy/2},{cz})")
            cmd.alter_state(1,boxname+"_z",f"(x,y,z)=({cx},{cy},{cz+sz/2})")
            cmd.rebuild()
            redraw(boxname)
        except Exception as e:
            print("Error:",e)
    btn_drawbox=QtWidgets.QPushButton("Redraw Box")
    btn_drawbox.clicked.connect(redraw_action)
    g_layout.addRow(btn_drawbox)
    group.setLayout(g_layout)
    layout.addWidget(group)
    # --------------------------------------------------------------------------------------------------------
    #  GUI SECTION: Box Around Selection
    # --------------------------------------------------------------------------------------------------------
    group=CollapsibleBox("Wrap Box Around Selection",open=True)
    g_layout=QtWidgets.QFormLayout()
    g_layout.setSpacing(2)
    padding_input=QtWidgets.QDoubleSpinBox()
    padding_input.setValue(DEFAULT["wrap_padding"])
    sel_input=QtWidgets.QLineEdit(DEFAULT["wrap_sele"])
    g_layout.addRow("Padding (Å):",padding_input)
    g_layout.addRow("Selection:",sel_input)
    def wrapsel_action(_Qtcheck,boxname=boxname):
        try:
            wrapsel(sel_input.text(),padding_input.value(),boxname=boxname)
        except Exception as e:
            print("Error:",e)
    btn_wrapsel=QtWidgets.QPushButton("Redraw Box")
    btn_wrapsel.clicked.connect(wrapsel_action)
    g_layout.addRow(btn_wrapsel)
    group.setLayout(g_layout)
    layout.addWidget(group)
    # --------------------------------------------------------------------------------------------------------
    #  GUI SECTION: Tweak Box Handle Positions
    # --------------------------------------------------------------------------------------------------------
    group=CollapsibleBox("Tweak Box Handle Positions",open=True)
    g_layout=QtWidgets.QFormLayout()
    cx_input=QtWidgets.QDoubleSpinBox()
    cy_input=QtWidgets.QDoubleSpinBox()
    cz_input=QtWidgets.QDoubleSpinBox()
    x_input=QtWidgets.QDoubleSpinBox()
    y_input=QtWidgets.QDoubleSpinBox()
    z_input=QtWidgets.QDoubleSpinBox()
    setQDoubleSpinStyle(cx_input,"x")
    setQDoubleSpinStyle(cy_input,"y")
    setQDoubleSpinStyle(cz_input,"z")
    setQDoubleSpinStyle(x_input,"x")
    setQDoubleSpinStyle(y_input,"y")
    setQDoubleSpinStyle(z_input,"z")
    for spin in[cx_input,cy_input,cz_input,x_input,y_input,z_input]:
        spin.setMaximum(1000.0)
        spin.setSingleStep(1)
        spin.setDecimals(1)
        spin.setValue(0)
    for spin in[x_input,y_input,z_input]:
        spin.setMinimum(1.0)
    for spin in[cx_input,cy_input,cz_input]:
        spin.setMinimum(-1000.0)
    label=QtWidgets.QLabel()
    label.setText("<b>Resize Along Axes:</b>")
    label.setTextFormat(QtCore.Qt.RichText)
    g_layout.addRow(label)
    xlabel=QtWidgets.QLabel("&harr; Size X (Å):")
    xlabel.setTextFormat(QtCore.Qt.RichText)
    xlabel.setStyleSheet(f"color:{AXCOLORS['x']['main_color']};font-weight:bold")
    g_layout.addRow(xlabel,x_input)
    ylabel=QtWidgets.QLabel("&harr; Size Y (Å):")
    ylabel.setTextFormat(QtCore.Qt.RichText)
    ylabel.setStyleSheet(f"color:{AXCOLORS['y']['main_color']};font-weight:bold")
    g_layout.addRow(ylabel,y_input)
    zlabel=QtWidgets.QLabel("&harr; Size Z (Å):")
    zlabel.setTextFormat(QtCore.Qt.RichText)
    zlabel.setStyleSheet(f"color:{AXCOLORS['z']['main_color']};font-weight:bold")
    g_layout.addRow(zlabel,z_input)
    label=QtWidgets.QLabel()
    label.setText("<b>Translate Box Center:</b>")
    label.setTextFormat(QtCore.Qt.RichText)
    g_layout.addRow(label)
    xyz_widget=QtWidgets.QWidget()
    xyz_layout=QtWidgets.QHBoxLayout(xyz_widget)
    xyz_layout.setContentsMargins(0,0,0,0)
    xyz_layout.setSpacing(3)
    xyz_layout.addWidget(QtWidgets.QLabel(" x (Å):"))
    xyz_layout.addWidget(cx_input)
    xyz_layout.addWidget(QtWidgets.QLabel(" y (Å):"))
    xyz_layout.addWidget(cy_input)
    xyz_layout.addWidget(QtWidgets.QLabel(" z (Å):"))
    xyz_layout.addWidget(cz_input)
    g_layout.addRow(xyz_widget)
    xyz_layout.addStretch()
    global BOX_UI
    BOX_UI={
        "cx":cx_input,"x":x_input,
        "cy":cy_input,"y":y_input,
        "cz":cz_input,"z":z_input,
    }
    def update_spinboxes_safe(c,px,py,pz):
        if not BOX_UI:
            return
        updating_ui=True
        try:
            for w in BOX_UI.values():
                w.blockSignals(True)
            BOX_UI["cx"].setValue(c[0])
            BOX_UI["cy"].setValue(c[1])
            BOX_UI["cz"].setValue(c[2])
            BOX_UI["x"].setValue((px[0]-c[0])*2)
            BOX_UI["y"].setValue((py[1]-c[1])*2)
            BOX_UI["z"].setValue((pz[2]-c[2])*2)
        finally:
            for w in BOX_UI.values():
                w.blockSignals(False)
            updating_ui=False
    boxupdater.spinbox_updated.connect(update_spinboxes_safe)
    def on_value_changed(_=None,boxname=boxname):
        if updating_ui:
            return
        try:
            cx,cy,cz=cx_input.value(),cy_input.value(),cz_input.value()
            cmd.alter_state(1,boxname+"_center",f"(x,y,z)=({cx},{cy},{cz})")
            cmd.alter_state(1,boxname+"_x",f"(x,y,z)=({cx+x_input.value()/2},{cy},{cz})")
            cmd.alter_state(1,boxname+"_y",f"(x,y,z)=({cx},{cy+y_input.value()/2},{cz})")
            cmd.alter_state(1,boxname+"_z",f"(x,y,z)=({cx},{cy},{cz+z_input.value()/2})")
            cmd.rebuild()
            redraw(boxname)
            reset_Receptor_GUI()
        except Exception as e:
            print("Error:",e)
    for spin in[cx_input,cy_input,cz_input,x_input,y_input,z_input]:
        spin.valueChanged.connect(on_value_changed)
    group.setLayout(g_layout)
    layout.addWidget(group)
    # --------------------------------------------------------------------------------------------------------
    #  GUI SECTION: Live Editing (doc only)
    # --------------------------------------------------------------------------------------------------------
    group=CollapsibleBox("Live Editing Box Coordinates (Tutorial)",bold=False,background="transparent")
    g_layout=QtWidgets.QVBoxLayout()
    label=QtWidgets.QLabel()
    label.setWordWrap(True)
    label.setText("""
        <b>Commands:</b><li><code>start_live</code></li><li><code>stop_live</code></li><br>
        <b>How to move box handlers:</b>
        <li>Switch to <code>Mouse Mode 3-Button Editing</code></li>
        <li><code>Shift + Middle Click + Drag</code></li>
        <li>Box dimensions only update during <code>start_live</code>.</li><br>
        <b>Tips:</b>
        <li>During <code>start_live</code>, everything except from the handlers will be masked.</li>
        <li>This mask will be temporarily disabled then reenabled while using the “Rotate Receptor” feature.</li>
        <li><code>stop_live</code> will remove the mask.</li>
    """)
    label.setTextFormat(QtCore.Qt.RichText)
    g_layout.addWidget(label)
    group.setLayout(g_layout)
    layout.addWidget(group)
    # --------------------------------------------------------------------------------------------------------
    #  GUI SECTION: Display Box Coordinates
    # --------------------------------------------------------------------------------------------------------
    group=QtWidgets.QGroupBox("Current Box Coordinates")
    group.setSizePolicy(QtWidgets.QSizePolicy.Preferred,QtWidgets.QSizePolicy.Maximum)
    g_layout=QtWidgets.QFormLayout()
    labels=QtWidgets.QHBoxLayout()
    labels.addWidget(QtWidgets.QLabel("For AutoDock Vina:"))
    labels.addWidget(QtWidgets.QLabel("Real on-screen values:"))
    g_layout.addRow(labels)
    text_display_copy=QtWidgets.QPlainTextEdit()
    text_display_copy.setReadOnly(True)
    text_display_copy.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
    text_display_copy.setStyleSheet("""QPlainTextEdit{
        background-color:#2b2b2b;
        color:#f8f8f2;
        font-family:Consolas,monospace;
        border:1px solid #555;
    }""")
    text_display_info=QtWidgets.QPlainTextEdit()
    text_display_info.setReadOnly(True)
    text_display_info.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
    text_display_info.setStyleSheet("""QPlainTextEdit{
        background-color:transparent;
        color:#000;
        font-family:Consolas,monospace;
        border:none;
    }""")
    text_row=QtWidgets.QHBoxLayout()
    text_row.addWidget(text_display_copy)
    text_row.addWidget(text_display_info)
    g_layout.addRow(text_row)
    set_textbox_height(text_display_copy)
    set_textbox_height(text_display_info,lines=8)
    g_layout.addRow(text_row)
    copy_btn=QtWidgets.QPushButton("Copy to Clipboard")
    def copy_text():
        QtWidgets.QApplication.clipboard().setText(text_display_copy.toPlainText())
    copy_btn.clicked.connect(copy_text)
    g_layout.addWidget(copy_btn)
    g_layout.addWidget(QtWidgets.QLabel("Warning: If you rotated your receptor, remember to export its new coordinates as well!"))
    group.setLayout(g_layout)
    layout.addWidget(group)
    def update_box_info(copy_txt,info_txt):
        text_display_copy.setPlainText(copy_txt)
        text_display_info.setPlainText(info_txt)
    boxupdater.text_updated.connect(update_box_info)
    ##########################################################################################################
    ## ---------------------------------------------------------------------------------------------------- ##
    ##  GUI SECTION: Rotate Receptor                                                                        ##
    ## ---------------------------------------------------------------------------------------------------- ##
    ##########################################################################################################
    group=CollapsibleBox("Rotate Receptor")
    g_layout=QtWidgets.QFormLayout()
    # --------------------------------------------------------------------------------------------------------
    #  MATH
    # --------------------------------------------------------------------------------------------------------
    original_coords={}
    def apply_rotation(boxname=boxname):
        global previousangles
        try:
            cx,cy,cz=cmd.get_coords(boxname+"_center")[0]
            selection=obj_input.text().strip()
            if not selection:
                return
            if selection not in original_coords:
                coords=cmd.get_coords(selection,state=1)
                if coords is None:
                    print("No atoms in selection",selection)
                    return
                original_coords[selection]=coords
            if _running:
                cmd.unmask(f"all and not {DEFAULT['prefix']}_*")
            cmd.origin(boxname+"_center")
            for ax in["x","y","z"]:
                if current_angles[ax]!=previousangles[ax]:
                    cmd.rotate(ax,current_angles[ax]-previousangles[ax],selection,0,1,None,[cx,cy,cz])
                    previousangles[ax]=current_angles[ax]
            if _running:
                cmd.mask(f"all and not {DEFAULT['prefix']}_*")
        except Exception as e:
            print("Rotation error:",e)
    # --------------------------------------------------------------------------------------------------------
    #  GUI
    # --------------------------------------------------------------------------------------------------------
    obj_input=QtWidgets.QLineEdit(DEFAULT["rotate_sele"])
    g_layout.addRow("Object(s):",obj_input)
    last_selection={"text":obj_input.text()}
    def on_selection_changed():
        new_text=obj_input.text().strip()
        if new_text!=last_selection["text"]:
            reset_Receptor_GUI()
            original_coords.clear()
            last_selection["text"]=new_text
            print("Rotation cache cleared")
    obj_input.editingFinished.connect(on_selection_changed)
    def make_axis_row(label_text,axis):
        container=QtWidgets.QHBoxLayout()
        slider=QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setRange(-180,180)
        slider.setValue(0)
        slider.setStyleSheet((
        "QSlider::groove:horizontal{"
            f"background:{AXCOLORS[axis]['background']};height:8px;border-radius:4px"
        "}QSlider::handle:horizontal{"
            f"background:{AXCOLORS[axis]['main_color']};width:16px;margin:-4px 0;border-radius:8px"
        "}"))
        spin=QtWidgets.QDoubleSpinBox()
        spin.setRange(-360,360)
        spin.setDecimals(2)
        spin.setSingleStep(1.0)
        spin.setValue(0)
        container.addWidget(slider)
        container.addWidget(spin)
        g_layout.addRow(label_text,container)
        return slider,spin
    slider_x,spin_x=make_axis_row("Rotate X:","x")
    slider_y,spin_y=make_axis_row("Rotate Y:","y")
    slider_z,spin_z=make_axis_row("Rotate Z:","z")
    setQDoubleSpinStyle(spin_x,"x")
    setQDoubleSpinStyle(spin_y,"y")
    setQDoubleSpinStyle(spin_z,"z")
    def connect_axis(axis,slider,spin):
        def slider_changed(value):
            current_angles[axis]=float(value)
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)
            apply_rotation()
        def spin_changed(value):
            current_angles[axis]=float(value)
            slider.blockSignals(True)
            slider.setValue(int(value))
            slider.blockSignals(False)
            apply_rotation()
        slider.valueChanged.connect(slider_changed)
        spin.valueChanged.connect(spin_changed)
    connect_axis('x',slider_x,spin_x)
    connect_axis('y',slider_y,spin_y)
    connect_axis('z',slider_z,spin_z)
    def reset_Receptor_GUI():
        current_angles.update({'x':0.0,'y':0.0,'z':0.0})
        previousangles.update({'x':0.0,'y':0.0,'z':0.0})
        for slider,spin in[(slider_x,spin_x),(slider_y,spin_y),(slider_z,spin_z)]:
            slider.blockSignals(True)
            spin.blockSignals(True)
            slider.setValue(0)
            spin.setValue(0)
            slider.blockSignals(False)
            spin.blockSignals(False)
    def reset_rotation():
        selection=obj_input.text().strip()
        if selection in original_coords:
            try:
                cmd.load_coords(original_coords[selection],selection,state=1)
            except Exception as e:
                print("Reset error:",e)
        reset_Receptor_GUI()
    btn_reset=QtWidgets.QPushButton("Reset Position")
    btn_reset.clicked.connect(reset_rotation)
    g_layout.addRow(btn_reset)
    group.setLayout(g_layout)
    layout.addWidget(group)
    # --------------------------------------------------------------------------------------------------------
    #  Finalize
    # --------------------------------------------------------------------------------------------------------
    layout.addStretch()
    scroll.setWidget(widget)
    dock.setWidget(scroll)
    main_window.addDockWidget(QtCore.Qt.RightDockWidgetArea,dock)
    QtCore.QTimer.singleShot(0,lambda:redraw(boxname))
##############################################################################################################
##                                                                                                          ##
##                                         ██ ███    ██ ██ ████████                                         ##
##                                         ██ ████   ██ ██    ██                                            ##
##                                         ██ ██ ██  ██ ██    ██                                            ##
##                                         ██ ██  ██ ██ ██    ██                                            ##
##                                         ██ ██   ████ ██    ██                                            ##
##                                                                                                          ##
##############################################################################################################
def run_gridboxbuilder():
    cmd.set("auto_zoom",0)
    init_box()
    dockingBoxGUI(True,DEFAULT["prefix"])
    cmd.extend("start_live",start_live)
    cmd.extend("stop_live",stop_live)
    QtCore.QTimer.singleShot(0,lambda:redraw(DEFAULT["prefix"]))
    draw_axes()
def __init_plugin__(app=None):
    from pymol.plugins import addmenuitemqt
    addmenuitemqt('Grid Box Builder',run_gridboxbuilder)
