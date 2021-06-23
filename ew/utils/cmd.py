import asyncio
import random
import time

from ew.backend import item as bknd_item
from ew.backend.item import EwItem
from ew.backend.status import EwStatusEffect
from ew.static import cfg as ewcfg
from ew.static import hue as hue_static
from ew.static import poi as poi_static
from ew.static import status as se_static
from ew.static import weapons as static_weapons
from ew.utils import core as ewutils
from ew.utils import frontend as fe_utils
from ew.utils import stats as ewstats
from ew.utils.combat import EwUser
from ew.utils.slimeoid import EwSlimeoid

""" wrapper for discord members """  # Doesn't really sound like a cmd related class


class EwId:
    user = -1
    guild = -1
    display_name = ""
    admin = False

    def __init__(self, user, guild, display_name, admin):
        self.user = user
        self.guild = guild
        self.display_name = display_name
        self.admin = admin

    def __repr__(self):  # print() support
        return "<EwId - {}>".format(self.display_name)


""" class to send general data about an interaction to a command """


class EwCmd:
    cmd = ""
    tokens = []
    tokens_count = 0
    message = None
    client = None
    mentions = []
    mentions_count = 0
    guild = None

    # EwId system
    client_id = None
    author_id = None
    mention_ids = []

    def __init__(
            self,
            tokens = [],
            message = None,
            client = None,
            mentions = [],
            guild = None,
            admin = False,
    ):
        self.tokens = tokens
        self.message = message
        self.client = client
        self.guild = guild

        if len(tokens) >= 1:
            self.tokens_count = len(tokens)
            self.cmd = tokens[0]

        # Endless War's EwId
        self.client_id = EwId(client.user.id, self.guild.id, client.user.name, admin=admin)
        # Author's EwId
        self.author_id = EwId(message.author.id, self.guild.id, message.author.display_name, admin=admin)
        # List of mentions' EwIds
        self.mention_ids = []
        for user in mentions:
            self.mention_ids.append(EwId(user.id, self.guild.id, user.display_name, user.guild_permissions.administrator))
        # print(EwId(user.id, user.guild.id, user.display_name, user.guild_permissions.administrator))

        # remove mentions to us for commands that dont yet handle Endless War mentions with EwIds
        self.mentions = list(filter(lambda user: user.id != client.user.id, mentions))
        self.mentions_count = len(self.mentions)


def gen_data_text(
        id_user = None,
        id_server = None,
        display_name = None,
        channel_name = None
):
    user_data = EwUser(
        id_user=id_user,
        id_server=id_server,
        data_level=2
    )
    slimeoid = EwSlimeoid(id_user=id_user, id_server=id_server)

    cosmetics = bknd_item.inventory(
        id_user=user_data.id_user,
        id_server=user_data.id_server,
        item_type_filter=ewcfg.it_cosmetic
    )
    adorned_cosmetics = []
    for cosmetic in cosmetics:
        cos = EwItem(id_item=cosmetic.get('id_item'))
        if cos.item_props['adorned'] == 'true':
            hue = hue_static.hue_map.get(cos.item_props.get('hue'))
            adorned_cosmetics.append((hue.str_name + " " if hue != None else "") + cosmetic.get('name'))

    if user_data.life_state == ewcfg.life_state_grandfoe:
        poi = poi_static.id_to_poi.get(user_data.poi)
        if poi != None:
            response = "{} is {} {}.".format(display_name, poi.str_in, poi.str_name)
        else:
            response = "You can't discern anything useful about {}.".format(display_name)

    else:

        # return somebody's score
        race_suffix = race_prefix = ""
        if user_data.race == ewcfg.races["humanoid"]:
            race_prefix = "lame-ass "
        elif user_data.race == ewcfg.races["amphibian"]:
            race_prefix = "slippery "
            race_suffix = "amphibious "
        elif user_data.race == ewcfg.races["food"]:
            race_suffix = "edible "
        elif user_data.race == ewcfg.races["skeleton"]:
            race_suffix = "skele"
        elif user_data.race == ewcfg.races["robot"]:
            race_prefix = "silicon-based "
            race_suffix = "robo"
        elif user_data.race == ewcfg.races["furry"]:
            race_prefix = "furry "
        elif user_data.race == ewcfg.races["scalie"]:
            race_prefix = "scaly "
        elif user_data.race == ewcfg.races["slime-derived"]:
            race_prefix = "goopy "
        elif user_data.race == ewcfg.races["critter"]:
            race_prefix = "small "
        elif user_data.race == ewcfg.races["monster"]:
            race_prefix = "monstrous "
        elif user_data.race == ewcfg.races["avian"]:
            race_prefix = "feathery "
        elif user_data.race == ewcfg.races["insectoid"]:
            race_prefix = "chitinny "
        elif user_data.race == ewcfg.races["other"]:
            race_prefix = "peculiar "
        elif user_data.race != "":
            race_prefix = "mouthbreathing "

        if user_data.life_state == ewcfg.life_state_corpse:
            response = "{} is a {}level {} {}deadboi.".format(display_name, race_prefix, user_data.slimelevel, race_suffix)
        elif user_data.life_state == ewcfg.life_state_shambler:
            response = "{} is a {}level {} {}shambler.".format(display_name, race_prefix, user_data.slimelevel, race_suffix)
        else:
            response = "{} is a {}level {} {}slimeboi.".format(display_name, race_prefix, user_data.slimelevel, race_suffix)
            if user_data.degradation < 20:
                pass
            elif user_data.degradation < 40:
                response += " Their bodily integrity is starting to slip."
            elif user_data.degradation < 60:
                response += " Their face seems to be melting and they periodically have to put it back in place."
            elif user_data.degradation < 80:
                response += " They are walking a bit funny, because their legs are getting mushy."
            elif user_data.degradation < 100:
                response += " Their limbs keep falling off. It's really annoying."
            else:
                response += " They almost look like a shambler already."

        coinbounty = int(user_data.bounty / ewcfg.slimecoin_exchangerate)

        weapon_item = EwItem(id_item=user_data.weapon)
        weapon = static_weapons.weapon_map.get(weapon_item.item_props.get("weapon_type"))

        if weapon != None:
            response += " {} {}{}.".format(
                ewcfg.str_weapon_married if user_data.weaponmarried == True else ewcfg.str_weapon_wielding, (
                    "" if len(weapon_item.item_props.get("weapon_name")) == 0 else "{}, ".format(
                        weapon_item.item_props.get("weapon_name"))), weapon.str_weapon)
            if user_data.weaponskill >= 5:
                response += " {}".format(weapon.str_weaponmaster.format(rank=(user_data.weaponskill - 4)))

        sidearm_item = EwItem(id_item=user_data.sidearm)
        sidearm = static_weapons.weapon_map.get(sidearm_item.item_props.get("weapon_type"))

        if sidearm != None:
            response += " They have sidearmed {}{}.".format((
                "" if len(sidearm_item.item_props.get("weapon_name")) == 0 else "{}, ".format(
                    sidearm_item.item_props.get("weapon_name"))), sidearm.str_weapon)

        trauma = se_static.trauma_map.get(user_data.trauma)

        if trauma != None:
            response += " {}".format(trauma.str_trauma)

        response_block = ""

        user_kills = ewstats.get_stat(user=user_data, metric=ewcfg.stat_kills)

        enemy_kills = ewstats.get_stat(user=user_data, metric=ewcfg.stat_pve_kills)

        if user_kills > 0 and enemy_kills > 0:
            response_block += "They have {:,} confirmed kills, and {:,} confirmed hunts. ".format(user_kills,
                                                                                                  enemy_kills)
        elif user_kills > 0:
            response_block += "They have {:,} confirmed kills. ".format(user_kills)
        elif enemy_kills > 0:
            response_block += "They have {:,} confirmed hunts. ".format(enemy_kills)

        if coinbounty != 0:
            response_block += "SlimeCorp offers a bounty of {:,} SlimeCoin for their death. ".format(coinbounty)

        if len(adorned_cosmetics) > 0:
            response_block += "They have a {} adorned. ".format(ewutils.formatNiceList(adorned_cosmetics, 'and'))

            if user_data.freshness < ewcfg.freshnesslevel_1:
                response_block += "Their outfit is starting to look pretty fresh, but They’ve got a long way to go if they wanna be NLACakaNM’s next top model. "
            elif user_data.freshness < ewcfg.freshnesslevel_2:
                response_block += "Their outfit is low-key on point, not gonna lie. They’re goin’ places, kid. "
            elif user_data.freshness < ewcfg.freshnesslevel_3:
                response_block += "Their outfit is lookin’ fresh as hell, goddamn! They shop so much they can probably speak Italian. "
            elif user_data.freshness < ewcfg.freshnesslevel_4:
                response_block += "Their outfit is straight up **GOALS!** Like, honestly. I’m being, like, totally sincere right now. Their Instragrime has attracted a small following. "
            else:
                response_block += "Holy shit! Their outfit is downright, positively, without a doubt, 100% **ON FLEEK!!** They’ve blown up on Instragrime, and they’ve got modeling gigs with fashion labels all across the city. "

        statuses = user_data.getStatusEffects()

        for status in statuses:
            status_effect = EwStatusEffect(id_status=status, user_data=user_data)
            if status_effect.time_expire > time.time() or status_effect.time_expire == -1:
                status_flavor = se_static.status_effects_def_map.get(status)

                severity = ""
                try:
                    value_int = int(status_effect.value)
                    if value_int < 3:
                        severity = "lightly injured."
                    elif value_int < 7:
                        severity = "battered and bruised."
                    elif value_int < 11:
                        severity = "severely damaged."
                    else:
                        severity = "completely fucked up, holy shit!"
                except:
                    pass

                format_status = {'severity': severity}

                if status_flavor is not None:
                    response_block += status_flavor.str_describe.format_map(format_status) + " "

        if (slimeoid.life_state == ewcfg.slimeoid_state_active) and (user_data.life_state != ewcfg.life_state_corpse):
            response_block += "They are accompanied by {}, a {}-foot-tall Slimeoid. ".format(slimeoid.name, str(slimeoid.level))

        # if user_data.swear_jar >= 500:
        # 	response_block += "They're going to The Underworld for the things they've said."
        # elif user_data.swear_jar >= 100:
        # 	response_block += "They swear like a sailor!"
        # elif user_data.swear_jar >= 50:
        # 	response_block += "They have quite a profane vocabulary."
        # elif user_data.swear_jar >= 10:
        # 	response_block += "They've said some naughty things in the past."
        # elif user_data.swear_jar >= 5:
        # 	response_block += "They've cussed a handful of times here and there."
        # elif user_data.swear_jar > 0:
        # 	response_block += "They've sworn only a few times."
        # else:
        # 	response_block += "Their mouth is clean as a whistle."

        if len(response_block) > 0:
            response += "\n" + response_block

    return response


""" Send an initial message you intend to edit later while processing the command. Returns handle to the message. """


async def start(cmd = None, message = '...', channel = None, client = None):
    if cmd != None:
        channel = cmd.message.channel
        client = cmd.client

    if client != None and channel != None:
        return await fe_utils.send_message(client, channel, message)

    return None


# Used when you have a secret command you only want seen under certain conditions.
async def fake_failed_command(cmd):
    client = ewutils.get_client()
    randint = random.randint(1, 3)
    msg_mistake = "ENDLESS WAR is growing frustrated."
    if randint == 2:
        msg_mistake = "ENDLESS WAR denies you his favor."
    elif randint == 3:
        msg_mistake = "ENDLESS WAR pays you no mind."

    msg = await fe_utils.send_message(client, cmd.message.channel, msg_mistake)
    await asyncio.sleep(2)
    try:
        await msg.delete()
        pass
    except:
        pass
