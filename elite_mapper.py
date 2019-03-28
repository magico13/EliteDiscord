import traceback
from mpl_toolkits.mplot3d import Axes3D
import matplotlib
import matplotlib.pyplot as plt


import elite

def normalize_coords(coords):
    sagA = {'x':25.21875, 'y':-20.90625, 'z':25899.96875}
    return {'x':(coords['x'] - sagA['x'])/1000, 'y':(coords['y'] - sagA['y'])/1000, 'z':(coords['z'] - sagA['z'])/1000}

def plot_systems(a0, a1, a2, includeList=None, label=False):
    if includeList and len(includeList) == 0: return #empty list, don't plot anything
    #if list is None, plot all POIs
    d3 = a0 and not a1
    xList = []
    yList = []
    zList = []
    nameList = []
    
    for name in includeList:
        coords = elite.friendly_get_coords(name)
        normalized = normalize_coords(coords)
        xList.append(normalized['x'])
        yList.append(normalized['y'])
        zList.append(normalized['z'])
        nameList.append(name)
    
    if not d3:
        a0.plot(xList, zList, 'y*', zorder=1)
        a1.plot(yList, zList, 'y*', zorder=1)
        a2.plot(xList, yList, 'y*', zorder=1)
    else:
        a0.plot(xList, zList, yList, 'y*', zorder=1)

    if label and not d3:
        for i, name in enumerate(nameList):
            annotate(a0, name, xList[i], zList[i])
            annotate(a1, name, yList[i], zList[i])
            annotate(a2, name, xList[i], yList[i])

def plot_route(cmdr, color, a0, a1, a2, label=False):
    d3 = a0 and not a1
    xList = []
    yList = []
    zList = []
    names = elite.extract_system_names_from_flight_log(elite.get_cmdr_flight_log(cmdr))
    infos = elite.get_coordinates_of_systems(names)
    for name in names:
        for info in infos:
            if info['name'] == name:
                normalized = normalize_coords(info['coords'])
                xList.append(normalized['x'])
                yList.append(normalized['y'])
                zList.append(normalized['z'])
                break
    if not d3:
        a0.plot(xList, zList, 'o-', color=color, markersize=2, zorder=2)
        a1.plot(yList, zList, 'o-', color=color, markersize=2, zorder=2)
        a2.plot(xList, yList, 'o-', color=color, markersize=2, zorder=2)
        if label:
            annotate(a0, cmdr, xList[0], zList[0])
            annotate(a1, cmdr, yList[0], zList[0])
            annotate(a2, cmdr, xList[0], yList[0])
    else:
        a0.plot(xList, zList, yList, 'o-', color=color, markersize=2, zorder=2)

def limit_and_label(a0, a1, a2, fullGalaxy=True):
    plot_lim = 45
    plot_limH = 3
    if fullGalaxy:
        a0.set_xlim(-plot_lim, plot_lim)
        a0.set_ylim(-plot_lim, plot_lim)
    a0.set_xlabel('X')
    a0.set_ylabel('Z', rotation=0)
    if a0 and not a1:
        #3d
        if fullGalaxy: a0.set_zlim(-plot_limH, plot_limH)
        a0.set_zlabel('H')
    else:
        if fullGalaxy:
            a1.set_xlim(plot_limH, -plot_limH)
            a1.set_ylim(-plot_lim, plot_lim)
            a2.set_xlim(-plot_lim, plot_lim)
            a2.set_ylim(-plot_limH, plot_limH)
        else:
            a1.invert_xaxis()#set_ylim(a1.get_ylim()[::-1])
        a1.set_xlabel('H')
        a1.set_ylabel('Z', rotation=0)
        a2.set_xlabel('X')
        a2.set_ylabel('H', rotation=0)

        a0.set_facecolor('k')
        a1.set_facecolor('k')
        a2.set_facecolor('k')
        
def annotate(ax, txt, pointx, pointy):
    ax.annotate(txt, (pointx, pointy), xytext=(5, -3), textcoords='offset points', color='w')

def remove_top_right_lines(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

def create_plot(items, zoomed=False, threeD=False, labels=False):
    cmdrs, systems = parse_items_list(items)
    f, _ = plt.subplots()
    if threeD:
        a0 = f.add_subplot(111, projection='3d')
        a1 = None
        a2 = None
    else:
        f.set_facecolor('k')
        params = {"ytick.color" : "w",
            "xtick.color" : "w",
            "axes.labelcolor" : "w",
            "axes.edgecolor" : "w"}
        plt.rcParams.update(params)
        a0 = plt.subplot2grid((4,4), (0,0), rowspan=3, colspan=3)
        a1 = plt.subplot2grid((4,4), (0,3), rowspan=3)
        a2 = plt.subplot2grid((4,4), (3,0), colspan=3)
        remove_top_right_lines(a0)
        remove_top_right_lines(a1)
        remove_top_right_lines(a2)

    limit_and_label(a0, a1, a2, not zoomed)

    plot_systems(a0, a1, a2, systems, labels)
    for cmdr in cmdrs:
        plot_route(cmdr, None, a0, a1, a2, labels)

    plt.tight_layout()
    plt.savefig('data/fig.png', facecolor='k', dpi=600)

def parse_items_list(items):
    cmdrs = []
    systems = []
    for item in items:
        item = item.strip()
        _, known = elite.get_cmdr(item)
        if known: #is a known commander
            cmdrs.append(item)
        else: #might be a poi, system, or an unknown cmdr
            poi = elite.get_POI_coords(item)
            if poi:
                systems.append(item)
                continue
            #not a stored point of interest, maybe a system?
            system = elite.get_system_coordinates(item)
            if system:
                systems.append(item)
            else: #not a known system, guess it's a commander
                system = elite.get_cmdr_system(item)
                if system: cmdrs.append(item)
                    #unknown, just skip it
    return cmdrs, systems

def parse_and_plot(command): #!ed map mmarvin, DWStation, Sol, Beagle Point zoomed label 3d
    split = command.split()
    zoom = False
    label = False
    d3 = False
    if 'zoomed' in split:
        zoom = True
        split.remove('zoomed')
    if 'label' in split:
        label = True
        split.remove('label')
    if '3d' in split:
        d3 = True
        split.remove('3d')
    split.remove('!ed')
    split.remove('map')
    #everything else is a system or commander
    items = ' '.join(split)
    split = items.split(',') #these are separated with commas
    create_plot(split, zoom, d3, label)
    return True