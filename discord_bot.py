import discord
from discord.ext import commands
import re
import traceback
import math

import elite
import elite_mapper

description = '''Elite: Dangerous connector bot.'''

token = ''
uid_regex = re.compile(r'<.*?(\d+)>')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!ed ', description=description, intents=intents)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    elite.load_data()

@bot.command(name='locate')
async def locate(ctx: commands.Context, name = None):
    """Gets the location of a commander (alt for 'location')"""
    await ctx.send(locate_handler(ctx, name))

@bot.command(name='location')
async def location(ctx: commands.Context, name = None):
    """Gets the location of a commander (alt for 'locate')"""
    await ctx.send(locate_handler(ctx, name))

def locate_handler(ctx: commands.Context, name):
    cmdr = get_uid(name or str(ctx.message.author.id))
    loc = elite.get_cmdr_system_name(cmdr)
    cmdrName, _ = elite.get_cmdr(cmdr)
    if not loc or loc == 'None':
        return '{0} could not be located'.format(name)
    return '{0} is at {1}'.format(cmdrName, loc)

def get_uid(name):
    match = uid_regex.search(name)
    if not match: return name
    return match.group(1)

@bot.command(name='register', pass_context=True)
async def register(ctx: commands.Context, cmdrName: str, key=None):
    """Links a discord username and a CMDR (and EDSM API key)"""
    user = str(ctx.message.author.id)
    elite.set_cmdr(user, cmdrName, key)
    msg = 'o7 Greetings CMDR {0}! I\'ve got you registered with "<@{1}>"=="{0}".'.format(cmdrName, user)
    if key:
        msg += ' I advise deleting your post so your API Key doesn\'t ~~get intercepted by Thargoids~~ persist in the chat logs.'
    await ctx.send(msg)

@bot.command(name='poi')
async def poi(ctx: commands.Context, poiName: str, poiLocation = None):
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
    await ctx.send(msg)

@bot.command(name='pois')
async def pois(ctx):
    """Lists all Points of Interest"""
    pois = elite.get_POIs()
    msg = 'Points of Interest:\n'
    for _, poi in sorted(pois.items()):
        msg += '{0}: {1}\n'.format(poi.name, poi.system)
    await ctx.send(msg)

@bot.command(name='distance')
async def distance(ctx: commands.Context, item1: str, item2: str):
    """Gets the distance between two items (CMDR, PoI, System)"""
    uid1 = get_uid(item1)
    uid2 = get_uid(item2)
    dist = elite.friendly_get_distance(uid1, uid2)
    dist = round(dist, 2)
    msg = '{0} is {1} LY from {2}'.format(item2, dist, item1)
    await ctx.send(msg)

@bot.command(name='info', pass_context=True)
async def info(ctx: commands.Context, system: str):
    """Gets detailed information on a system (alt for 'system')"""
    await ctx.typing()
    await ctx.send(info_handler(system))
    
@bot.command(name='system', pass_context=True)
async def system(ctx: commands.Context, system: str):
    """Gets detailed information on a system (alt for 'info')"""
    await ctx.typing()
    await ctx.send(info_handler(system))

def info_handler(system):
    return elite.get_system_info_for_display(system)

@bot.command(name='radius', pass_context=True)
async def radius(ctx: commands.Context, system: str, radius: float, minRadius = 0.0):
    """Returns systems within a radius around a system"""
    await ctx.typing()
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
    await ctx.send(msg)

@bot.command(name='balance', pass_context=True)
async def balance(ctx: commands.Context, name = None):
    '''Gets credit balance of cmdr name'''
    await ctx.typing()
    cmdr = get_uid(name or str(ctx.message.author.id))
    credits = elite.get_credits(cmdr)
    msg = '{0} '.format(name)
    if credits and credits['msgnum'] == 100:
        msg += 'has {:,} credits.'.format(credits['credits'][0]['balance'])
    else:
        msg += 'could not be found'
    await ctx.send(msg)

@bot.command(name='ranks', pass_context=True)
async def ranks(ctx: commands.Context, name = None):
    '''Gets all ranks of cmdr name'''
    await ctx.typing()
    name = get_uid(name or str(ctx.message.author.id))
    cmdr, _ = elite.get_cmdr(name)
    ranks = elite.get_ranks(cmdr)
    msg = '__{0}__\n'.format(cmdr)
    display_format = '{0} : {1} ({2}%)\n'
    if ranks and ranks['msgnum'] == 100:
        msg += display_format.format('Combat', ranks['ranksVerbose']['Combat'], ranks['progress']['Combat'])
        msg += display_format.format('Trade', ranks['ranksVerbose']['Trade'], ranks['progress']['Trade'])
        msg += display_format.format('Exploration', ranks['ranksVerbose']['Explore'], ranks['progress']['Explore'])
        msg += display_format.format('Soldier', ranks['ranksVerbose']['Soldier'], ranks['progress']['Soldier'])
        msg += display_format.format('Exobiologist', ranks['ranksVerbose']['Exobiologist'], ranks['progress']['Exobiologist'])
        msg += display_format.format('CQC', ranks['ranksVerbose']['CQC'], ranks['progress']['CQC'])
        msg += display_format.format('Federation', ranks['ranksVerbose']['Federation'], ranks['progress']['Federation'])
        msg += display_format.format('Empire', ranks['ranksVerbose']['Empire'], ranks['progress']['Empire'])
    else:
        msg = 'No ranks found for "{0}"'.format(name)
    await ctx.send(msg)

@bot.command(name='materials', pass_context=True)
async def materials(ctx: commands.Context, name = None):
    '''Gets all materials for the cmdr'''
    await ctx.typing()
    cmdr = get_uid(name or str(ctx.message.author.id))
    materials = elite.get_materials(cmdr)
    msg = '_{0} materials_\n'.format(name)
    if materials and materials['msgnum'] == 100:
        for mats in materials['materials']:
            #only include materials which the cmdr has at least 1 of
            if mats['qty'] > 0:
                msg += '{0} : {1}\n'.format(mats['name'], mats['qty'])
    else:
        msg = 'No materials found for "{0}"'.format(name)
    await ctx.send(msg)

@bot.command(name='cargo', pass_context=True)
async def cargo(ctx: commands.Context, name = None):
    '''Gets all cargo for the cmdr'''
    await ctx.typing()
    cmdr = get_uid(name or str(ctx.message.author.id))
    cargo = elite.get_cargo(cmdr)
    msg = '_{0} cargo_\n'.format(name)
    cargoNum = 0
    if cargo and cargo['msgnum'] == 100:
        for item in cargo['cargo']:
            #Only include cargo which the cmdr has at least 1 of
            if item['qty'] > 0:
                msg += '{0} : {1}\n'.format(item['name'], item['qty'])
                cargoNum += 1
    else:
        msg = 'No cargo found for "{0}"'.format(name)
        #set cargoNum to -1 so we don't print below
        cargoNum = -1
    
    if cargoNum == 0:
        msg += 'No cargo!'
    await ctx.send(msg)

@bot.command(name='data', pass_context=True)
async def data(ctx: commands.Context, name = None):
    '''Gets all encoded data for the cmdr'''
    await ctx.typing()
    cmdr = get_uid(name or str(ctx.message.author.id))
    encodedData = elite.get_encoded_data(cmdr)
    msg = '_{0} encoded data_\n'.format(name)
    if encodedData and encodedData['msgnum'] == 100:
        for data in encodedData['data']:
            #Only include encoded data which the cmdr has at least 1 of
            if data['qty'] > 0:
                msg += '{0} : {1}\n'.format(data['name'], data['qty'])
    else:
        msg = 'No encoded data found for "{0}"'.format(name)
    await ctx.send(msg)

@bot.command(name='map', pass_context=True) 
async def map(ctx):
	'''Returns a map of the requested items'''
	await ctx.typing()
	elite_mapper.parse_and_plot(ctx.message.content)
	with open('data/fig.png', 'rb') as f:
		await ctx.send(file=discord.File(f, 'fig.png'))
	
@bot.command(name='rate')
async def rate(ctx: commands.Context, name = None):
    '''Gets the jump rate, average jump distance, and ly per hour for a commander'''
    name = get_uid(name or str(ctx.message.author.id))
    try:
        cmdr, _ = elite.get_cmdr(name)
        rate = elite.get_jump_rate(cmdr)
        dist = elite.get_average_jump_distance(cmdr)
        distRate = rate*dist
        msg = f'{cmdr} jumps {rate:0.2f} times per hour at an average jump distance of {dist:0.2f} ly for a rate of {distRate:0.2f} ly per hour.'
    except:
        msg = f'Could not determine rate information for "{name}": {traceback.format_exc().splitlines()[-1]}'
    await ctx.send(msg)

@bot.command(name='target')
async def target(ctx: commands.Context, system: str, name = None):
    '''Gets the distance and estimate of jumps and time required to travel to a target system'''
    name = get_uid(name or str(ctx.message.author.id))
    try:
        cmdr, known = elite.get_cmdr(name)
        if not known: return 'Command requires target system and commander name!'
        rate = elite.get_jump_rate(cmdr)
        avgDist = elite.get_average_jump_distance(cmdr)
        dist = elite.friendly_get_distance(cmdr, system)
        jumps = math.ceil(dist/avgDist)
        time = jumps / rate
        msg = f'"{system}" is {dist:0.2f} ly from {cmdr}. That\'s about {jumps} jumps or {time:0.2f} hours.'
    except:
        msg = f'Could not process "target" command: {traceback.format_exc().splitlines()[-1]}'
    await ctx.send(msg)

def get_token():
    with open('data/token.secret', 'r') as f:
        return f.readline().strip()

bot.run(get_token())
