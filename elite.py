import math
import operator
import requests
from datetime import datetime

apiKeys = {}
cmdrNames = {}
pointsOfInterest = {}

flightLogCache = {}

debug = False

class PointOfInterest:
    def __init__(self, Name, SystemName, Coords):
        self.name = Name
        self.system = SystemName
        self.coords = Coords
        self.coords['x'] = float(self.coords['x'])
        self.coords['y'] = float(self.coords['y'])
        self.coords['z'] = float(self.coords['z'])

def get_cmdr_api_key(cmdr):
    user = get_user_for_cmdr(cmdr)
    if (user):
        return get_user_api_key(user)

def get_user_api_key(user):
    if user in apiKeys:
        return apiKeys[user]
        
def get_user_for_cmdr(cmdr):
    for user, cmd in cmdrNames.items():
        if cmd == cmdr:
            return user
    return None

def get_cmdr_for_user(user):
    if user in cmdrNames:
        return cmdrNames[user]
    return None
    
def set_api_key(user, key):
    apiKeys[user] = key
    save_data()
    
def set_cmdr(user, cmdr, key=None):
    cmdrNames[user] = cmdr
    if key:
        apiKeys[user] = key
    save_data()

def get_cmdr(potential: str):
    potential = potential.strip().strip('@<>')
    cmdr = get_cmdr_for_user(potential)
    if cmdr:
        #in this case they passed a user
        return cmdr, True
    else:
        #check if they're a cmdr we know
        known = get_user_for_cmdr(potential) != None
        return potential, known #passed a CMDR (or unregisted)

def get_cmdr_system_name(cmdr):
    system = get_cmdr_system(cmdr)
    if 'system' in system:
        return system['system']
    else:
        if 'msg' in system: return 'Error: '+system['msg']
        return 'Error: Could not get system for CMDR {0}'.format(cmdr)

def add_POI(name, system):
    coords = get_system_coordinates(system)
    if (coords):
        poi = PointOfInterest(name, system, coords)
        pointsOfInterest[name] = poi
        save_data()
        return poi
    return None

def remove_POI(name):
    poi = get_POI(name)
    if poi:
        del pointsOfInterest[poi.name]
        return True
    return False
    
def get_POI(name):
    if (name in pointsOfInterest):
        return pointsOfInterest[name]
    nameLower = name.lower()
    for n, poi in pointsOfInterest.items():
        if nameLower == n.lower():
            return poi
    return None

def get_POI_coords(name):
    poi = get_POI(name)
    if poi:
        return poi.coords
    return None

def get_POIs():
    return pointsOfInterest

def friendly_get_coords(loc):
    #check if other is POI
    poi = get_POI_coords(loc)
    if poi:
        return poi

    #check if is a cmdr
    cmdr, known = get_cmdr(loc)
    if not known:
        #Check if it's a system name then
        system = get_system_coordinates(loc)
        if system: 
            return system
            
    #try to get distance for cmdr
    cmdr_system = get_cmdr_system(cmdr, True)
    if 'coordinates' in cmdr_system:
        return cmdr_system['coordinates']
    
    #No idea what it is, sorry
    return None
    
def friendly_get_distance(a, b):
    coordA = friendly_get_coords(a)
    if coordA:
        coordB = friendly_get_coords(b)
        if coordB:
            return get_distance(coordA, coordB)
    return -1

def get_system_info_for_display(name):
    msg = ''
    systemName = name
    poi = get_POI(name) #allow passing a system or a poi
    if poi:
        systemName = poi.system
        
    systemInfo = get_system_info(systemName)
    if not systemInfo:
        return 'Could not find information for system "{0}"'.format(systemName)
    
    bodiesInfo = get_bodies_in_system(systemName)
    stationInfo = get_stations_in_system(systemName)
    fleetCarriers = get_fleet_carriers_in_system(systemName)
    trafficInfo = get_traffic_in_system(systemName)
    deathInfo = get_deaths_in_system(systemName)
    scanInfo = get_system_value(systemName)
    
    msg += 'Information for {0}:\n'.format(systemName)
    if 'information' in systemInfo and systemInfo['information']: 
        info = systemInfo['information']
        join = []
        if 'government' in info: join.append(info['government'])
        if 'allegiance' in info: join.append(info['allegiance'])
        if 'faction' in info: join.append(info['faction'])
        if 'population' in info: join.append('pop. '+str(info['population']))
        if len(join) > 0: msg += ' - '.join(join) + '\n'
    if 'primaryStar' in systemInfo and systemInfo['primaryStar']: 
        msg += 'Primary Star: {0}'.format(systemInfo['primaryStar']['type'])
        if systemInfo['primaryStar']['isScoopable']: msg += ' (scoopable)'
        msg += '\n'
    
    if 'bodies' in bodiesInfo and bodiesInfo['bodies']:
        msg += '{0} known bodies in system.\n'.format(len(bodiesInfo['bodies']))
        
    if stationInfo:
        count = len(stationInfo)
        msg += '{0} stations/settlements in system.'.format(count)
        if count > 0:
            closest = 99999999999
            closestName = ''
            for station in stationInfo:
                if station['distanceToArrival'] < closest:
                    closest = station['distanceToArrival']
                    closestName = station['name']
            msg += ' Closest is {0} ({1} ls)'.format(closestName, round(closest, 2))
            msg += '\n'
    
    if fleetCarriers:
        count = len(fleetCarriers)
        msg += f'{count} fleet carriers in system.\n'

    if 'traffic' in trafficInfo and 'deaths' in deathInfo and trafficInfo['traffic'] and deathInfo['deaths']:
        msg += '{0}/{1} CMDRs died in the system in the last 7 days.\n'.format(deathInfo['deaths']['week'], trafficInfo['traffic']['week'])
    
    if 'coords' in systemInfo and systemInfo['coords']: 
        dist = get_distance(systemInfo['coords'], {'x':0, 'y':0, 'z':0})
        dist = round(dist, 2)
        msg += 'Location: {0} LY from Sol {1}\n'.format(dist, systemInfo['coords'])

    if scanInfo:
        msg += 'Estimated value: {:,} credits ({:,} mapped)\n'.format(scanInfo['estimatedValue'], scanInfo['estimatedValueMapped'])
        if 'valuableBodies' in scanInfo and len(scanInfo['valuableBodies']) > 0:
            msg += '{0} valuable bodies:\n'.format(len(scanInfo['valuableBodies']))
            for body in scanInfo['valuableBodies']:
                msg += '{0} ({2}ls): {1:,} credits\n'.format(body['bodyName'], body['valueMax'], body['distance'])
    return msg
    
def extract_system_names_from_flight_log(flightLog):
    '''Takes in the results from a flight log call and extracts the system names from most recent to oldest'''
    names = []
    if not flightLog or 'logs' not in flightLog: return names
    for log in sorted(flightLog['logs'], key=operator.itemgetter('date'), reverse=True):
        names.append(log['system'])  # newest systems first
    return names

def get_jump_rate(cmdr, threshold = 7200):
    '''Gets the jump rate for a commander in jumps per hour'''
    logs = get_cmdr_flight_log(cmdr)
    lastDate = None
    jumps = 0
    totalTime = 0

    for log in logs['logs']:
        if lastDate: 
            timeDiff = (lastDate - datetime.strptime(log['date'], '%Y-%m-%d %H:%M:%S')).total_seconds()
            if timeDiff < threshold:
                jumps += 1
                totalTime += timeDiff
        lastDate = datetime.strptime(log['date'], '%Y-%m-%d %H:%M:%S')
    return jumps/(totalTime/3600.0)

def get_average_jump_distance(cmdr):
    '''Gets the average jump distance for the given cmdr'''
    logs = get_cmdr_flight_log(cmdr)
    names = extract_system_names_from_flight_log(logs)
    positions = get_coordinates_of_systems(names)
    lastPos = None
    jumps = 0
    totalDist = 0

    for name in names: #to keep correct order
        for pos in positions:
            if pos['name'] == name:
                if lastPos:
                    jumps += 1
                    dist = get_distance(lastPos['coords'], pos['coords'])
                    totalDist += dist
                lastPos = pos
                break
    if jumps == 0: return 0
    return totalDist / jumps

def load_data():
    apiKeys.clear()
    cmdrNames.clear()
    try:
        with open('data/ed_cmdr.csv', 'r') as f:
            for line in f:
                split = line.split(',')
                if (len(split) < 2 or len(split) > 3):
                    print('Encountered invalid data "{0}"'.format(line))
                    continue
                user = split[0].strip()
                cmdr = split[1].strip()
                cmdrNames[user] = cmdr
                if (len(split) == 3): 
                    key = split[2].strip()
                    if key and key != '':
                        apiKeys[user] = key
    except FileNotFoundError:
        print('No data file found, starting with empty data')
    print('Loaded {0} commanders and {1} api keys'.format(len(cmdrNames), len(apiKeys)))
    pointsOfInterest.clear()
    try:
        with open('data/ed_poi.csv', 'r') as f:
            for line in f:
                split = line.split(',')
                if (len(split) != 5):
                    print('Encountered invalid data "{0}"'.format(line))
                    continue
                name = split[0].strip()
                system = split[1].strip()
                x = split[2].strip()
                y = split[3].strip()
                z = split[4].strip()
                coords = {'x': x, 'y': y, 'z': z}
                poi = PointOfInterest(name, system, coords)
                pointsOfInterest[name] = poi
    except FileNotFoundError:
        print('No points of interest file found, starting with empty data')
    print('Loaded {0} points of interest.'.format(len(pointsOfInterest)))

def save_data():
    with open('data/ed_cmdr.csv', 'w') as f:
        for user, cmdr in cmdrNames.items():
            key = ''
            if user in apiKeys:
                key = apiKeys[user]
            f.write('{0}, {1}, {2}\n'.format(user, cmdr, key))
    print('Saved {0} commanders and {1} api keys'.format(len(cmdrNames), len(apiKeys)))
    with open('data/ed_poi.csv', 'w') as f:
        for _, poi in pointsOfInterest.items():
            f.write('{0}, {1}, {2}, {3}, {4}\n'
                .format(poi.name, poi.system, poi.coords['x'], poi.coords['y'], poi.coords['z']))
    print('Saved {0} points of interest'.format(len(pointsOfInterest)))
    
# Actual API calls to edsm #
def get_edsm(api, endpoint, params=None):
    url = 'https://www.edsm.net/api-'
    if api:
        url += '{0}-v1/{1}'.format(api, endpoint)
    else:
        url += 'v1/{0}'.format(endpoint)
    # if (len(params) > 0):
    #     url += '?'
    #     for p, v in params.items():
    #         if isinstance(v, list):
    #             fragment = ''
    #             for val in v:
    #                 mini = '{0}={1}'.format(p, val)
    #                 fragment += html.escape(mini) + '&'
    #             fragment = fragment[:-1]
    #         else:
    #             fragment = '{0}={1}'.format(p, v)
    #             fragment = html.escape(fragment)
    #         url += fragment + '&'
    # url = url[:-1]
    # url = url.replace(' ', '%20')
    if debug: print(url)
    response_raw = requests.get(url, params=params)
    if debug: print(response_raw)
    response = response_raw.json()
    return response

def get_edsm_with_cmdr(api, endpoint, potential, params=None):
    cmdr, _ = get_cmdr(potential)
    if debug: print('cmdr: '+cmdr)
    if not cmdr: return 'Could not find commander for user "{0}"'.format(user)
    key = get_cmdr_api_key(cmdr)
    if not params: params = {}
    params['commanderName'] = cmdr
    if (key): params['apiKey'] = key
    return get_edsm(api, endpoint, params)
    
def get_cmdr_system(cmdr, getCoords = False):
    api = 'logs'
    endpoint = 'get-position'
    params = None
    if getCoords: params = {'showCoordinates': '1' }
    system = get_edsm_with_cmdr(api, endpoint, cmdr, params)
    return system

def get_distance(coord1, coord2):
    dx = float(coord1['x']) - float(coord2['x'])
    dy = float(coord1['y']) - float(coord2['y'])
    dz = float(coord1['z']) - float(coord2['z'])
    return math.sqrt((dx*dx)+(dy*dy)+(dz*dz))
    
def distance_from_cmdr(cmdr, point2):
    cmdrSystem = get_cmdr_system(cmdr, True)
    if not cmdrSystem or not 'coordinates' in cmdrSystem:
        print('Cannot get position for CMDR {0}'.format(cmdr))
        return -1
    cmdrCoord = cmdrSystem['coordinates']
    return get_distance(cmdrCoord, point2)
    
def get_system_coordinates(systemName):
    api = None
    endpoint = 'system'
    params = {
        'systemName':systemName,
        'showCoordinates':1
    }
    system = get_edsm(api, endpoint, params)
    if 'coords' in system:
        return system['coords']
    else:
        print('Could not find coordinates for system {0}'.format(systemName))
        if 'msg' in system: print(system['msg'])
        return None

def get_coordinates_of_systems(systems):
    '''Returns a list of coordinates for the given list of system names'''
    api = None
    endpoint = 'systems'
    params = {
        'showCoordinates':1
    }
    systemResults = []
    #do this in groups of 100
    for i in range(0, len(systems), 100):
        subsystems = systems[i:i+100]
        if len(subsystems) == 1: params['systemName'] = systems[0]
        else:
            params['systemName[]'] = subsystems

        results = get_edsm(api, endpoint, params)
        if len(results) > 0:
            systemResults += results
    if len(systemResults) > 0:
        return systemResults
    else:
        print('Could not find coordinates for {0} provided systems'.format(len(systems)))
        return None
        
def get_system_info(systemName):
    api = None
    endpoint = 'system'
    params = {
        'systemName':systemName,
        'showCoordinates':1,
        'showPermit':1,
        'showInformation':1,
        'showPrimaryStar':1
    }
    system = get_edsm(api, endpoint, params)
    if system and 'name' in system:
        return system
    else:
        print('Could not find system {0}'.format(systemName))
        if 'msg' in system: print(system['msg'])
        return None
        
def get_system_value(systemName):
    '''Gets the estimated scan value of the system and a list of valuable bodies'''
    api = 'system'
    endpoint = 'estimated-value'
    params = {'systemName': systemName}
    values = get_edsm(api, endpoint, params)
    if values:
        return values
    else:
        print('Could not find scan data for system {0}'.format(systemName))
        return None

def get_bodies_in_system(systemName):
    api = 'system'
    endpoint = 'bodies'
    params = {'systemName': systemName}
    bodies = get_edsm(api, endpoint, params)
    if bodies and 'bodies' in bodies:
        return bodies
    else:
        print('Could not find bodies for system {0}'.format(systemName))
        if 'msg' in bodies: print(bodies['msg'])
        return None
        
def get_stations_in_system(systemName, include_fleet_carriers=False):
    api = 'system'
    endpoint = 'stations'
    params = {'systemName': systemName}
    stations = get_edsm(api, endpoint, params)
    if stations and 'stations' in stations:
        stations_filtered = stations['stations']
        if not include_fleet_carriers:
            stations_filtered = [station for station in stations_filtered if station['type'] != 'Fleet Carrier']
        return stations_filtered
    else:
        print('Could not find stations for system {0}'.format(systemName))
        if 'msg' in stations: print(stations['msg'])
        return None

def get_fleet_carriers_in_system(systemName):
    api = 'system'
    endpoint = 'stations'
    params = {'systemName': systemName}
    stations = get_edsm(api, endpoint, params)
    if stations and 'stations' in stations:
        stations_filtered = stations['stations']
        stations_filtered = [station for station in stations_filtered if station['type'] == 'Fleet Carrier']
        return stations_filtered
    else:
        print('Could not find fleet carriers for system {0}'.format(systemName))
        if 'msg' in stations: print(stations['msg'])
        return None

def get_traffic_in_system(systemName):
    api = 'system'
    endpoint = 'traffic'
    params = {'systemName': systemName}
    traffic = get_edsm(api, endpoint, params)
    if traffic and 'traffic' in traffic:
        return traffic
    else:
        print('Could not find traffic for system {0}'.format(systemName))
        if 'msg' in traffic: print(traffic['msg'])
        return None
        
def get_deaths_in_system(systemName):
    api = 'system'
    endpoint = 'deaths'
    params = {'systemName': systemName}
    deaths = get_edsm(api, endpoint, params)
    if deaths and 'deaths' in deaths:
        return deaths
    else:
        print('Could not find deaths for system {0}'.format(systemName))
        if 'msg' in deaths: print(deaths['msg'])
        return None

def get_systems_in_radius(coords, radius, minRadius=0):
    api = None
    endpoint = 'sphere-systems'
    params = {
        'x': coords['x'],
        'y': coords['y'],
        'z': coords['z'],
        'minRadius': minRadius,
        'radius': radius
    }
    return get_edsm(api, endpoint, params)

def get_credits(cmdr):
    '''Get the last recorded credits of a user'''
    api = 'commander'
    endpoint = 'get-credits'
    return get_edsm_with_cmdr(api, endpoint, cmdr)
	
def get_ranks(cmdr):
    '''Gets all ranks for a user'''
    api = 'commander'
    endpoint = 'get-ranks'
    return get_edsm_with_cmdr(api, endpoint, cmdr)

def get_materials(cmdr):
    '''Gets materials for a user'''
    api = 'commander'
    endpoint = 'get-materials'
    return get_edsm_with_cmdr(api, endpoint, cmdr)

def get_cargo(cmdr):
    '''Gets cargo for a user'''
    api = 'commander'
    endpoint = 'get-materials'
    params = {'type':'cargo'}
    return get_edsm_with_cmdr(api, endpoint, cmdr, params)

def get_encoded_data(cmdr):
    '''Gets encoded data for a user'''
    api = 'commander'
    endpoint = 'get-materials'
    params = {'type':'data'}
    return get_edsm_with_cmdr(api, endpoint, cmdr, params)

def get_cmdr_flight_log(cmdr, startDate = None, endDate = None):
    '''Gets the flight log for a user'''
    latest = get_cmdr_system(cmdr)
    if not latest or 'system' not in latest: return None
    key = cmdr+latest['system']
    if not startDate and not endDate:
        if key in flightLogCache:
            print('Using cached flight data for user {}'.format(cmdr))
            return flightLogCache[key]
    api = 'logs'
    endpoint = 'get-logs'
    params = {'showId':'0'}
    if startDate: params['startDateTime'] = startDate
    if endDate: params['endDateTime'] = endDate
    results = get_edsm_with_cmdr(api, endpoint, cmdr, params)
    if not startDate and not endDate:
        flightLogCache[key] = results
    return results