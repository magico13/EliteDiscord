import discord
from discord.ext import commands
import random
import re

import elite

description = '''Elite:Dangerous connector bot.'''

token = ''
uid_regex = re.compile(r'<.*?(\d+)>')

bot = commands.Bot(command_prefix='!ed ', description=description)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    elite.load_data()

@bot.command()
async def locate(name: str):
    """Gets the location of a commander (alt for 'location')"""
    name = get_uid(name)
    await bot.say(locate_handler(name))

@bot.command()
async def location(name: str):
    """Gets the location of a commander (alt for 'locate')"""
    await bot.say(locate_handler(name))

def locate_handler(name: str):
    cmdr = get_uid(name)
    loc = elite.get_cmdr_system_name(cmdr)
    cmdrName, _ = elite.get_cmdr(cmdr)
    if not loc or loc == 'None':
        return '{0} could not be located'.format(name)
    return '{0} is at {1}'.format(cmdrName, loc)

def get_uid(name):
    match = uid_regex.search(name)
    if not match: return name
    return match.group(1)

@bot.command(pass_context=True)
async def register(ctx, cmdrName: str, key=None):
    """Links a discord username and a CMDR (and EDSM API key)"""
    user = str(ctx.message.author.id)
    elite.set_cmdr(user, cmdrName, key)
    msg = 'o7 Greetings CMDR {0}! I\'ve got you registered with "<@{1}>"=="{0}".'.format(cmdrName, user)
    if key:
        msg += ' I advise deleting your post so your API Key doesn\'t ~~get intercepted by Thargoids~~ persist in the chat logs.'
    await bot.say(msg)

@bot.command()
async def poi(poiName: str, poiLocation = None):
    """Displays or creates/updates a Point of Interest"""
    msg = 'Could not process command :('
    if poiLocation and poiLocation != '':
        if (poiLocation == 'remove' or poiLocation == 'delete'):
            if (elite.remove_POI(poiName)):
                msg = 'Removed Point of Interest "{0}"'.format(poiName)
            else:
                msg = '"{0}" is not a known point of interest'.format(poiName)
        else:
            poi = elite.add_POI(poiName, poiLocation)
            if poi:
                msg = 'Added Point of Interest "{0}" at {1} {2}'.format(poi.name, poi.system, poi.coords)
            else:
                msg = 'Could not find system with name "{0}"'.format(poiLocation)
    else:
        poi = elite.get_POI(poiName)
        if poi:
            msg = '{0} ({1}) is located at {2}'.format(poi.name, poi.system, poi.coords)
        else:
            msg = '"{0}" is not a known point of interest'.format(poiName)
    await bot.say(msg)

@bot.command()
async def pois():
    """Lists all Points of Interest"""
    pois = elite.get_POIs()
    msg = 'Points of Interest:\n'
    for name, poi in pois.items():
        msg += '{0}: {1}\n'.format(poi.name, poi.system)
    await bot.say(msg)

@bot.command()
async def distance(item1: str, item2: str):
    """Gets the distance between two items (CMDR, PoI, System)"""
    uid1 = get_uid(item1)
    uid2 = get_uid(item2)
    dist = elite.friendly_get_distance(uid1, uid2)
    dist = round(dist, 2)
    msg = '{0} is {1} LY from {2}'.format(item2, dist, item1)
    await bot.say(msg)

@bot.command(pass_context=True)
async def info(ctx, system: str):
    """Gets detailed information on a system (alt for 'system')"""
    await bot.send_typing(ctx.message.channel)
    await bot.say(info_handler(system))
    
@bot.command(pass_context=True)
async def system(ctx, system: str):
    """Gets detailed information on a system (alt for 'info')"""
    await bot.send_typing(ctx.message.channel)
    await bot.say(info_handler(system))

def info_handler(system):
    return elite.get_system_info_for_display(system)

@bot.command(pass_context = True)
async def radius(ctx, system: str, radius: float, minRadius = 0.0):
    """Returns systems within a radius around a system"""
    await bot.send_typing(ctx.message.channel)
    coords = elite.friendly_get_coords(system)
    systems = elite.get_systems_in_radius(coords, radius, minRadius)
    if systems:
        msg = '{0} systems between {1} and {2} LY from {3}'.format(len(systems), minRadius, radius, system)
        if len(systems) > 0:
            msg += ':\n'
            limit = 50
            if len(systems) > limit:
                msg += '(closest {0} shown)\n'.format(limit)
            count = 0
            for sys in sorted(systems, key=lambda x: x['distance']):
                msg += '{0}: {1} LY\n'.format(sys['name'], sys['distance'])
                count += 1
                if count > limit: break
        else:
            msg += '\n'
    else:
        msg = 'No systems in range'
    await bot.say(msg)

@bot.command(pass_context=True)
async def balance(ctx, name: str):
    '''Gets credit balance of cmdr name'''
    await bot.send_typing(ctx.message.channel)
    cmdr = get_uid(name)
    credits = elite.get_credits(cmdr)
    msg = '{0} '.format(name)
    if credits and credits['msgnum'] == 100:
        msg += 'has {:,} credits.'.format(credits['credits'][0]['balance'])
    else:
        msg += 'could not be found'
    await bot.say(msg)

@bot.command(pass_context=True)
async def ranks(ctx, name: str):
    '''Gets all ranks of cmdr name'''
    await bot.send_typing(ctx.message.channel)
    cmdr = get_uid(name)
    ranks = elite.get_ranks(cmdr)
    msg = '__{0}__\n'.format(name)
    if ranks and ranks['msgnum'] == 100:
        msg += '{0} : {1}\n'.format('Combat', ranks['ranksVerbose']['Combat'])
        msg += '{0} : {1}\n'.format('Trade', ranks['ranksVerbose']['Trade'])
        msg += '{0} : {1}\n'.format('Explore', ranks['ranksVerbose']['Explore'])
        msg += '{0} : {1}\n'.format('CQC', ranks['ranksVerbose']['CQC'])
        msg += '{0} : {1}\n'.format('Federation', ranks['ranksVerbose']['Federation'])
        msg += '{0} : {1}\n'.format('Empire', ranks['ranksVerbose']['Empire'])
    else:
        msg += 'No ranks found'
    await bot.say(msg)

def get_token():
    with open('data/token.secret', 'r') as f:
        return f.readline().strip()

bot.run(get_token())
