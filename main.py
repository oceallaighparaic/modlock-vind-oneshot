import modlock
from modlock import Connection, Player, AbilityOptions


HERO = "hero_hornet"

G_CONNECTING: list[modlock.PlayerJoinedEvent] = [] # List of players who have joined, but are still connecting
G_LOADING: list[modlock.PlayerJoinedEvent] = [] # List of players who have connected, but are still loading

_G_LAST_USED_ABIL: dict[tuple[int,str], float] = {} # Dict of steam_id: (start_cd, abil name)
G_CUSTOM_CD: dict[str, tuple[float,float]] = { # abil name: (cd, recharge cd)
    "citadel_ability_hornet_snipe": (0.0,1e9),
    "citadel_ability_hornet_leap": (10.0,0.0)
}


#region START EVENTS
@modlock.on_start
def start(args: list[str]) -> None:
    modlock.log(f"Mod started with args: {args}")
    modlock.set_team_seating(True) # disable choose team screen
    modlock.set_free_for_all(True) 

@modlock.on_frame
def _frame_join_handler(e: modlock.FrameEvent) -> None:
    """
    1. @modlock.on_player_join
        - When they "join" (initial connection)
    2. ePlayerConnected()
        - Full connection, when Connection.ready = True
    3. ePlayerPawnLoaded()
        - Player pawn is fully loaded
    """

    # connection test
    for je in G_CONNECTING:
        if je.connection.ready:
            G_CONNECTING.remove(je)
            ePlayerConnected(je)
            G_LOADING.append(je)

    # pawn loaded test
    for je in G_LOADING:
        if je.connection.player.pawn() is not None:
            G_LOADING.remove(je)
            ePlayerPawnLoaded(je)

@modlock.on_player_join
def ePlayerJoin(e: modlock.PlayerJoinedEvent) -> None:
    """Called when the player joins initially, the first stage of joining the game."""
    modlock.log(f"{e.connection.steam_id} joined.")
    G_CONNECTING.append(e)

def ePlayerConnected(e: modlock.PlayerJoinedEvent) -> None:
    """Called when the player connects fully, the second stage of joining the game."""
    modlock.log(f"{e.connection.steam_id} connected successfully.")

def ePlayerPawnLoaded(e: modlock.PlayerJoinedEvent) -> None:
    """Called when the player loads fully, the third stage of joining the game."""
    modlock.log(f"{e.connection.steam_id} loaded successfully.")
    fPlayerSetup(e.connection)
    if (pawn := e.connection.player.pawn()) is not None:
        for a in G_CUSTOM_CD.keys():
            _G_LAST_USED_ABIL[(e.connection.steam_id, a)] = 0.0
#endregion


@modlock.command("hello")
def testcmd(plr: Player, args: str) -> None:
    print(plr.abilities())


#region FUNCTIONALITY
@modlock.on_frame
def fSnipeCDCheck(e: modlock.FrameEvent) -> None:
    for c in modlock.players():
        for a in c.player.abilities():
            if a.name in tuple(G_CUSTOM_CD.keys()):
                if a.cooldown_start != _G_LAST_USED_ABIL[(c.steam_id, a.name)]:
                    print(a.name, end="")

                    # refresh cd timer
                    _G_LAST_USED_ABIL[(c.steam_id, a.name)] = a.cooldown_start

                    # change cds
                    cd: float = G_CUSTOM_CD[a.name][0]
                    rechcd: float = G_CUSTOM_CD[a.name][1]
                    print(f" {cd=} {rechcd=}")
                    c.player.set_ability(AbilityOptions(ability=a.name, cooldown_end=(a.cooldown_start+cd), recharge_end=(a.cooldown_start+rechcd), charges=a.charges))

@modlock.on_damage
def fSnipeCheck(e: modlock.DamageEvent) -> None:
    if (shooter := get_connection_by_entity(e.attacker)) is None: return
    if (a := get_ability_by_name(shooter.player, "citadel_ability_hornet_snipe")) is None: return
    
    
    if a.entity == e.ability:
        shooter.player.announce("Nice shot!", "")
        shooter.player.set_ability(AbilityOptions(ability=a.name, recharge_end=0))

@modlock.on_damaged
def fSnipeDead(e: modlock.DamagedEvent) -> None:
    if (shooter := get_connection_by_entity(e.attacker)) is None: return
    if (victim := get_connection_by_entity(e.victim)) is None: return
    if (a := get_ability_by_name(shooter.player, "citadel_ability_hornet_snipe")) is None: return

    if a.entity == e.ability:
        victim.player.kill()

def fPlayerSetup(c: Connection) -> None:
    plr: Player = c.player

    plr.chat("Get ready to snipe!")
    if (pawn := plr.pawn()) is not None:
        plr.select_hero(HERO, pawn.team)

        plr.set_ability(AbilityOptions(ability='citadel_ability_hornet_chain', upgrades=0))
        plr.block_input(modlock.Buttons.ABILITY1)
        plr.set_ability(AbilityOptions(ability='citadel_ability_hornet_sting', upgrades=0))
        plr.block_input(modlock.Buttons.ABILITY3)

        plr.set_ability(AbilityOptions(ability='citadel_ability_hornet_snipe', upgrades=3, charges=1, cooldown_end=0.1, recharge_end=10000000, max_charges=1))
    else: print(f"{c.steam_id} did not load pawn correctly.")
#endregion


#region HELPERS
def get_connection_by_id(id: int) -> Connection|None:
    plr_cons: list[Connection] = modlock.players()

    # bin search, ordered connections
    l, r = 0, len(plr_cons)-1
    while l<=r:
        mid: int = (l+r)//2

        if plr_cons[mid].player.slot == id:
            return plr_cons[mid]

        # adjust
        if id < plr_cons[mid].player.slot: r = mid-1
        else: l = mid+1
    return None

def get_ability_by_name(plr: Player, name: str) -> modlock.Ability|None:
    for a in plr.abilities():
        if a.name == name:
            return a
    return None

def get_connection_by_entity(entity: int) -> Connection|None:
    for c in modlock.players():
        plr: Player = c.player
        if (pawn := plr.pawn()) is not None and pawn.entity == entity:
            return c
    return None
def get_player_by_entity(entity: int) -> Player|None:
    if (c := get_connection_by_entity(entity)) is not None:
        return c.player
    return None
#endregion