import discord
from discord.ext import commands
import random
import re

import elite
import elite_mapper

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
        msg += '{0} : {1} ({2}%)\n'.format('Combat', ranks['ranksVerbose']['Combat'], ranks['progress']['Combat'])
        msg += '{0} : {1} ({2}%)\n'.format('Trade', ranks['ranksVerbose']['Trade'], ranks['progress']['Trade'])
        msg += '{0} : {1} ({2}%)\n'.format('Explore', ranks['ranksVerbose']['Explore'], ranks['progress']['Explore'])
        msg += '{0} : {1} ({2}%)\n'.format('CQC', ranks['ranksVerbose']['CQC'], ranks['progress']['CQC'])
        msg += '{0} : {1} ({2}%)\n'.format('Federation', ranks['ranksVerbose']['Federation'], ranks['progress']['Federation'])
        msg += '{0} : {1} ({2}%)\n'.format('Empire', ranks['ranksVerbose']['Empire'], ranks['progress']['Empire'])
    else:
        msg = 'No ranks found for "{0}"'.format(name)
    await bot.say(msg)

@bot.command(pass_context=True)
async def materials(ctx, name: str):
    '''Gets all materials for the cmdr'''
    await bot.send_typing(ctx.message.channel)
    cmdr = get_uid(name)
    materials = elite.get_materials(cmdr)
    msg = '_{0} materials_\n'.format(name)
    if materials and materials['msgnum'] == 100:
        for mats in materials['materials']:
            #only include materials which the cmdr has at least 1 of
            if mats['qty'] > 0:
                msg += '{0} : {1}\n'.format(mats['name'], mats['qty'])
    else:
        msg = 'No materials found for "{0}"'.format(name)
    await bot.say(msg)

@bot.command(pass_context=True)
async def cargo(ctx, name: str):
    '''Gets all cargo for the cmdr'''
    await bot.send_typing(ctx.message.channel)
    cmdr = get_uid(name)
    cargo = elite.get_cargo(cmdr)
    msg = '_{0} cargo_\n'.format(name)
    cargoNum = 0
    if cargo and cargo['msgnum'] == 100:
        for item in cargo['cargo']:
            #Only include cargo which the cmdr has at least 1 of
            if item['qty'] > 0:
                msg += '{0} : {1}\n'.format(item['name'], items['qty'])
                cargoNum += 1
    else:
        msg = 'No cargo found for "{0}"'.format(name)
        #set cargoNum to -1 so we don't print below
        cargoNum = -1
    
    if cargoNum == 0:
        msg += 'No cargo!'
    await bot.say(msg)

@bot.command(pass_context=True)
async def data(ctx, name: str):
    '''Gets all encoded data for the cmdr'''
    await bot.send_typing(ctx.message.channel)
    cmdr = get_uid(name)
    encodedData = elite.get_encoded_data(cmdr)
    msg = '_{0} encoded data_\n'.format(name)
    if encodedData and encodedData['msgnum'] == 100:
        for data in encodedData['data']:
            #Only include encoded data which the cmdr has at least 1 of
            if data['qty'] > 0:
                msg += '{0} : {1}\n'.format(data['name'], data['qty'])
    else:
        msg = 'No encoded data found for "{0}"'.format(name)
    await bot.say(msg)

@bot.command(pass_context=True)
async def map(ctx):
	'''Returns a map of the requested items'''
	await bot.type()
	elite_mapper.parse_and_plot(ctx.message.content)
	with open('data/fig.png', 'rb') as f:
		await bot.upload(f)
	
@bot.command()
async def rate(name: str):
    '''Gets the jump rate, average jump distance, and ly per hour for a commander'''
    cmdr = get_uid(name)
    try:
        rate = elite.get_jump_rate(name)
        dist = elite.get_average_jump_distance(name)
        distRate = rate*dist
        msg = f'{name} jumps {rate:0.2f} times per hour at an average jump distance of {dist:0.2f} ly for a rate of {distRate:0.2f} ly per hour.'
    except:
        msg = f'Could not determine rate information for "{name}": {traceback.format_exc().splitlines()[-1]}'
    await bot.say(msg)

@bot.command()
async def target(target: str, name: str):
    '''Gets the distance and estimate of jumps and time required to travel to a target system'''
    try:
        if len(split) < 4: return 'Command requires target system and commander name!'
        cmdr = split[3]
        system = split[2]
        _, known = elite.get_cmdr(cmdr)
        if not known:
            cmdr = split[2]
            system = split[3]
            _, known = elite.get_cmdr(cmdr)
        if not known: return 'Command requires target system and commander name!'
        rate = elite.get_jump_rate(cmdr)
        avgDist = elite.get_average_jump_distance(cmdr)
        dist = elite.friendly_get_distance(cmdr, system)
        jumps = math.ceil(dist/avgDist)
        time = jumps / rate
        msg = f'"{system}" is {dist:0.2f} ly from {cmdr}. That\'s about {jumps} jumps or {time:0.2f} hours.'
    except:
        msg = f'Could not process "target" command: {traceback.format_exc().splitlines()[-1]}'
    await bot.say(msg)

def get_token():
    with open('data/token.secret', 'r') as f:
        return f.readline().strip()

bot.run(get_token())
