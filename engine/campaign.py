"""Campaign progression: bosses, crown shards and act unlocking.

All functions are pure — they take the campaign/boss data and the list of
defeated boss ids, so progression is always derived rather than stored.
"""


def act_boss_ids(act):
    """Boss ids guarding areas within an act, in campaign order."""
    return [
        area["boss"]
        for location in act.get("locations", [])
        for area in location.get("areas", [])
        if area.get("boss")
    ]


def is_act_complete(act, defeated):
    bosses = act_boss_ids(act)
    return bool(bosses) and all(b in defeated for b in bosses)


def highest_unlocked_act(campaign, defeated):
    """Act number the player has reached (an act unlocks when the previous one is complete)."""
    unlocked = 1
    for act in campaign.get("acts", []):
        if act["number"] == unlocked and is_act_complete(act, defeated):
            unlocked += 1
    return min(unlocked, len(campaign.get("acts", [])) or 1)


def is_campaign_complete(campaign, defeated):
    acts = campaign.get("acts", [])
    return bool(acts) and all(is_act_complete(act, defeated) for act in acts)


def get_area_boss(area, bosses, defeated):
    """Boss id waiting in an area, or None if there is none / it is already defeated."""
    boss_id = area.get("boss") if area else None
    if boss_id and boss_id in bosses and boss_id not in defeated:
        return boss_id
    return None


def missing_requirements(boss, defeated):
    """Boss ids that must be defeated before this boss can be challenged."""
    return [r for r in boss.get("requires", []) if r not in defeated]


def collected_shards(bosses, defeated):
    """Names of the crown shards won so far, in the order they were claimed."""
    return [bosses[b]["shard"] for b in defeated if b in bosses and bosses[b].get("shard")]


def all_shards(bosses):
    return [b["shard"] for b in bosses.values() if b.get("shard")]


def pending_ambush(bosses, act, defeated):
    """Boss id of an ambush that should trigger now, or None.

    An ambush boss has {"ambush": {"act": N, "after_act_bosses": K}} and springs
    once K of that act's area bosses have fallen.
    """
    if not act:
        return None
    beaten_in_act = sum(1 for b in act_boss_ids(act) if b in defeated)
    for boss_id, boss in bosses.items():
        ambush = boss.get("ambush")
        if not ambush or boss_id in defeated:
            continue
        if ambush.get("act") == act.get("number") and beaten_in_act >= ambush.get("after_act_bosses", 1):
            return boss_id
    return None
