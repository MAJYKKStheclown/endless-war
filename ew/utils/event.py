
import random
import asyncio
import time

from ..static import cfg as ewcfg
from ..static import weapons as static_weapons
from ..static import poi as poi_static

from ..backend import core as bknd_core
from ..backend import item as bknd_item
from ..backend import worldevent as bknd_event

from . import core as ewutils
from . import frontend as fe_utils
from . import combat as cmbt_utils
from . import item as itm_utils
from . import hunting as hunt_utils
from . import stats as ewstats

from .user import EwUser
from .hunting import EwEnemy
from .frontend import EwResponseContainer
from ..backend.player import EwPlayer
from ..backend.market import EwMarket
from ..backend.item import EwItem
from ..backend.worldevent import EwWorldEvent


"""
	Database persistence object describing some discrete event. Player
	death/resurrection, item discovery, etc.
"""
class EwEvent:
	id_server = -1

	event_type = None

	id_user = None
	id_target = None

	def __init__(
		self,
		id_server = -1,
		event_type = None,
		id_user = None,
		id_target = None
	):
		self.id_server = id_server
		self.event_type = event_type
		self.id_user = id_user
		self.id_target = id_target

	"""
		Write event to the database.
	"""
	def persist(self):
		# TODO
		pass

stat_fn_map = {}
fns_initialized = False

def init_stat_function_map():
	global stat_fn_map
	stat_fn_map = {
		ewcfg.stat_slimesmined: process_slimesmined,
		ewcfg.stat_max_slimesmined: process_max_slimesmined,
		ewcfg.stat_slimesfromkills: process_slimesfromkills,
		ewcfg.stat_max_slimesfromkills: process_max_slimesfromkills,
		ewcfg.stat_kills: process_kills,
		ewcfg.stat_max_kills: process_max_kills,
		ewcfg.stat_ghostbusts: process_ghostbusts,
		ewcfg.stat_max_ghostbusts: process_max_ghostbusts,
		ewcfg.stat_poudrins_looted: process_poudrins_looted,
                ewcfg.stat_slimesfarmed: process_slimesfarmed,
                ewcfg.stat_slimesscavenged: process_slimesscavenged
	}
	global fns_initialized
	fns_initialized = True

def process_stat_change(id_server = None, id_user = None, metric = None, value = None):
	if fns_initialized == False:
		init_stat_function_map()

	fn = stat_fn_map.get(metric)

	if fn != None:
		fn(id_server = id_server, id_user = id_user, value = value)

def process_slimesmined(id_server = None, id_user = None, value = None):
	ewstats.track_maximum(id_server = id_server, id_user = id_user, metric = ewcfg.stat_max_slimesmined, value = value)

def process_max_slimesmined(id_server = None, id_user = None, value = None):
	# TODO give apropriate medal
	pass

def process_slimesfromkills(id_server = None, id_user = None, value = None):
	ewstats.track_maximum(id_server = id_server, id_user = id_user, metric = ewcfg.stat_max_slimesfromkills, value = value)

def process_max_slimesfromkills(id_server = None, id_user = None, value = None):
	# TODO give apropriate medal
	pass

def process_slimesfarmed(id_server = None, id_user = None, value = None):
	ewstats.track_maximum(id_server = id_server, id_user = id_user, metric = ewcfg.stat_max_slimesfarmed, value = value)

def process_slimesscavenged(id_server = None, id_user = None, value = None):
	ewstats.track_maximum(id_server = id_server, id_user = id_user, metric = ewcfg.stat_max_slimesscavenged, value = value)

def process_kills(id_server = None, id_user = None, value = None):
	ewstats.track_maximum(id_server = id_server, id_user = id_user, metric = ewcfg.stat_max_kills, value = value)
	ewstats.increment_stat(id_server = id_server, id_user = id_user, metric = ewcfg.stat_lifetime_kills)

def process_max_kills(id_server = None, id_user = None, value = None):
	# TODO give apropriate medal
	pass

def process_ghostbusts(id_server = None, id_user = None, value = None):
	ewstats.track_maximum(id_server = id_server, id_user = id_user, metric = ewcfg.stat_max_ghostbusts, value = value)
	ewstats.increment_stat(id_server = id_server, id_user = id_user, metric = ewcfg.stat_lifetime_ghostbusts)

def process_max_ghostbusts(id_server = None, id_user = None, value = None):
	# TODO give apropriate medal
	pass

def process_poudrins_looted(id_server = None, id_user = None, value = None):
	poudrin_amount = itm_utils.find_poudrin(id_user = id_user, id_server = id_user)

	ewstats.track_maximum(id_user = id_user, id_server = id_server, metric = ewcfg.stat_max_poudrins, value = poudrin_amount)
	ewstats.change_stat(id_user = id_user, id_server = id_server, metric = ewcfg.stat_lifetime_poudrins, n = value)

""" Damage all players in a district """
def explode(damage = 0, district_data = None, market_data = None):
	id_server = district_data.id_server
	poi = district_data.name

	if market_data == None:
		market_data = EwMarket(id_server = district_data.id_server)

	client = ewutils.get_client()
	server = client.get_guild(id_server)

	resp_cont = EwResponseContainer(id_server = id_server)
	response = ""
	channel = poi_static.id_to_poi.get(poi).channel

	life_states = [ewcfg.life_state_juvenile, ewcfg.life_state_enlisted, ewcfg.life_state_executive, ewcfg.life_state_shambler]
	users = district_data.get_players_in_district(life_states = life_states, pvp_only = True)

	enemies = district_data.get_enemies_in_district()

	# damage players
	for user in users:
		user_data = EwUser(id_user = user, id_server = id_server, data_level = 1)
		mutations = user_data.get_mutations()

		user_weapon = None
		user_weapon_item = None
		if user_data.weapon >= 0:
			user_weapon_item = EwItem(id_item = user_data.weapon)
			user_weapon = static_weapons.weapon_map.get(user_weapon_item.item_props.get("weapon_type"))

		# apply defensive mods
		slimes_damage_target = damage * cmbt_utils.damage_mod_defend(
			shootee_data = user_data,
			shootee_mutations = mutations,
			shootee_weapon = user_weapon,
			market_data = market_data
		)

		# apply sap armor
		#sap_armor = ewwep.get_sap_armor(shootee_data = user_data, sap_ignored = 0)
		#slimes_damage_target *= sap_armor
		#slimes_damage_target = int(max(0, slimes_damage_target))

		# apply fashion armor

		# disabled until held items update
		# fashion_armor = ewwep.get_fashion_armor(shootee_data = user_data)
		# slimes_damage_target *= fashion_armor
		slimes_damage_target = int(max(0, slimes_damage_target))

		player_data = EwPlayer(id_user = user_data.id_user)
		response = "{} is blown back by the explosion’s sheer force! They lose {:,} slime!!".format(player_data.display_name, slimes_damage_target)
		resp_cont.add_channel_response(channel, response)
		slimes_damage = slimes_damage_target
		if user_data.slimes < slimes_damage + user_data.bleed_storage:
			# die in the explosion
			district_data.change_slimes(n = user_data.slimes, source = ewcfg.source_killing)
			district_data.persist()
			slimes_dropped = user_data.totaldamage + user_data.slimes

			user_data.trauma = ewcfg.trauma_id_environment
			user_data.die(cause = ewcfg.cause_killing)
			#user_data.change_slimes(n = -slimes_dropped / 10, source = ewcfg.source_ghostification)
			user_data.persist()

			response = "Alas, {} was caught too close to the blast. They are consumed by the flames, and die in the explosion.".format(player_data.display_name)
			resp_cont.add_channel_response(channel, response)

			resp_cont.add_member_to_update(server.get_member(user_data.id_user))
		else:
			# survive
			slime_splatter = 0.5 * slimes_damage
			district_data.change_slimes(n = slime_splatter, source = ewcfg.source_killing)
			district_data.persist()
			slimes_damage -= slime_splatter
			user_data.bleed_storage += slimes_damage
			user_data.change_slimes(n = -slime_splatter, source = ewcfg.source_killing)
			user_data.persist()

	# damage enemies
	for enemy in enemies:
		enemy_data = EwEnemy(id_enemy = enemy, id_server = id_server)

		response = "{} is blown back by the explosion’s sheer force! They lose {:,} slime!!".format(enemy_data.display_name, damage)
		resp_cont.add_channel_response(channel, response)

		slimes_damage_target = damage
			
		# apply sap armor
		#sap_armor = ewwep.get_sap_armor(shootee_data = enemy_data, sap_ignored = 0)
		#slimes_damage_target *= sap_armor
		#slimes_damage_target = int(max(0, slimes_damage_target))

		slimes_damage = slimes_damage_target
		if enemy_data.slimes < slimes_damage + enemy_data.bleed_storage:
			# die in the explosion
			district_data.change_slimes(n = enemy_data.slimes, source = ewcfg.source_killing)
			district_data.persist()
			# slimes_dropped = enemy_data.totaldamage + enemy_data.slimes
			# explode_damage = ewutils.slime_bylevel(enemy_data.level)

			response = "Alas, {} was caught too close to the blast. They are consumed by the flames, and die in the explosion.".format(enemy_data.display_name)
			resp_cont.add_response_container(hunt_utils.drop_enemy_loot(enemy_data, district_data))
			resp_cont.add_channel_response(channel, response)

			enemy_data.life_state = ewcfg.enemy_lifestate_dead
			enemy_data.persist()

		else:
			# survive
			slime_splatter = 0.5 * slimes_damage
			district_data.change_slimes(n = slime_splatter, source = ewcfg.source_killing)
			district_data.persist()
			slimes_damage -= slime_splatter
			enemy_data.bleed_storage += slimes_damage
			enemy_data.change_slimes(n = -slime_splatter, source = ewcfg.source_killing)
			enemy_data.persist()
	return resp_cont

async def activate_trap_items(district, id_server, id_user):
	# Return if --> User has 0 credence, there are no traps, or if the trap setter is the one who entered the district.
	#print("TRAP FUNCTION")
	trap_was_dud = False
	
	user_data = EwUser(id_user=id_user, id_server=id_server)
	# if user_data.credence == 0:
	# 	#print('no credence')
	# 	return
	
	if user_data.life_state == ewcfg.life_state_corpse:
		#print('get out ghosts reeeee!')
		return
	
	try:
		conn_info = bknd_core.databaseConnect()
		conn = conn_info.get('conn')
		cursor = conn.cursor()

		district_channel_name = poi_static.id_to_poi.get(district).channel

		client = ewutils.get_client()

		server = client.get_guild(id_server)
		
		member = server.get_member(id_user)

		district_channel = fe_utils.get_channel(server=server, channel_name=district_channel_name)
		
		searched_id = district + '_trap'
		
		cursor.execute("SELECT id_item, id_user FROM items WHERE id_user = %s AND id_server = %s".format(
			id_item = ewcfg.col_id_item,
			id_user = ewcfg.col_id_user
		), (
			searched_id,
			id_server,
		))

		traps = cursor.fetchall()
		
		if len(traps) == 0:
			#print('no traps')
			return
		
		trap_used = traps[0]
		
		trap_id_item = trap_used[0]
		#trap_id_user = trap_used[1]
		
		trap_item_data = EwItem(id_item=trap_id_item)
		
		trap_chance = int(trap_item_data.item_props.get('trap_chance'))
		trap_user_id = trap_item_data.item_props.get('trap_user_id')
		
		if int(trap_user_id) == user_data.id_user:
			#print('trap same user id')
			return
		
		if random.randrange(101) < trap_chance:
			# Trap was triggered!
			pranker_data = EwUser(id_user=int(trap_user_id), id_server=id_server)
			pranked_data = user_data

			response = trap_item_data.item_props.get('prank_desc')

			side_effect = trap_item_data.item_props.get('side_effect')

			if side_effect != None:
				response += await itm_utils.perform_prank_item_side_effect(side_effect, member=member)
			
			#calculate_gambit_exchange(pranker_data, pranked_data, trap_item_data, trap_used=True)
		else:
			# Trap was a dud.
			trap_was_dud = True
			response = "Close call! You were just about to eat shit and fall right into someone's {}, but luckily, it was a dud.".format(trap_item_data.item_props.get('item_name'))
		
		bknd_item.item_delete(trap_id_item)
		
	finally:
		# Clean up the database handles.
		cursor.close()
		bknd_core.databaseClose(conn_info)
	await fe_utils.send_message(client, district_channel, fe_utils.formatMessage(member, response))
	
	# if not trap_was_dud:
	# 	client = ewutils.get_client()
	# 	server = client.get_server(id_server)
	# 
	# 	prank_feed_channel = get_channel(server, 'prank-feed')
	# 
	# 	response += "\n`-------------------------`"
	# 	await send_message(client, prank_feed_channel, formatMessage(member, response))


async def event_tick_loop(id_server):
	# initialise void connections
	void_connections = bknd_event.get_void_connection_pois(id_server)
	void_poi = poi_static.id_to_poi.get(ewcfg.poi_id_thevoid)
	for connection_poi in void_connections:
		# add the existing connections as neighbors for the void
		void_poi.neighbors[connection_poi] = ewcfg.travel_time_district
	for _ in range(3 - len(void_connections)):
		# create any missing connections
		bknd_event.create_void_connection(id_server)
	ewutils.logMsg("initialised void connections, current links are: {}".format(tuple(void_poi.neighbors.keys())))

	interval = ewcfg.event_tick_length
	while not ewutils.TERMINATE:
		await asyncio.sleep(interval)
		await event_tick(id_server)


async def event_tick(id_server):
	time_now = int(time.time())
	resp_cont = EwResponseContainer(id_server=id_server)
	try:
		data = bknd_core.execute_sql_query(
			"SELECT {id_event} FROM world_events WHERE {time_expir} <= %s AND {time_expir} > 0 AND id_server = %s".format(
				id_event=ewcfg.col_id_event,
				time_expir=ewcfg.col_time_expir,
			), (
				time_now,
				id_server,
			))

		for row in data:
			try:
				event_data = EwWorldEvent(id_event=row[0])
				event_def = poi_static.event_type_to_def.get(event_data.event_type)

				response = event_def.str_event_end if event_def else ""
				if event_data.event_type == ewcfg.event_type_minecollapse:
					user_data = EwUser(id_user=event_data.event_props.get('id_user'), id_server=id_server)
					mutations = user_data.get_mutations()
					if user_data.poi == event_data.event_props.get('poi'):

						player_data = EwPlayer(id_user=user_data.id_user)
						response = "*{}*: You have lost an arm and a leg in a mining accident. Tis but a scratch.".format(
							player_data.display_name)

						if random.randrange(4) == 0:
							response = "*{}*: Big John arrives just in time to save you from your mining accident!\nhttps://cdn.discordapp.com/attachments/431275470902788107/743629505876197416/mine2.jpg".format(
								player_data.display_name)
						else:

							if ewcfg.mutation_id_lightminer in mutations:
								response = "*{}*: You instinctively jump out of the way of the collapsing shaft, not a scratch on you. Whew, really gets your blood pumping.".format(
									player_data.display_name)
							else:
								user_data.change_slimes(n=-(user_data.slimes * 0.5))
								user_data.persist()


				# check if any void connections have expired, if so pop it and create a new one
				elif event_data.event_type == ewcfg.event_type_voidconnection:
					void_poi = poi_static.id_to_poi.get(ewcfg.poi_id_thevoid)
					void_poi.neighbors.pop(event_data.event_props.get('poi'), "")
					bknd_event.create_void_connection(id_server)

				if len(response) > 0:
					poi = event_data.event_props.get('poi')
					channel = event_data.event_props.get('channel')
					if channel != None:

						# in shambaquarium the event happens in the user's DMs
						if event_data.event_type == ewcfg.event_type_shambaquarium:
							client = ewutils.get_client()
							channel = client.get_guild(id_server).get_member(int(channel))

						resp_cont.add_channel_response(channel, response)
					elif poi != None:
						poi_def = poi_static.id_to_poi.get(poi)
						if poi_def != None:
							resp_cont.add_channel_response(poi_def.channel, response)

					else:
						for ch in ewcfg.hideout_channels:
							resp_cont.add_channel_response(ch, response)

				bknd_event.delete_world_event(event_data.id_event)
			except:
				ewutils.logMsg("Error in event tick for server {}".format(id_server))

		await resp_cont.post()

	except:
		ewutils.logMsg("Error in event tick for server {}".format(id_server))
