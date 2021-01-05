# STORAGE CLASSES


class Sport:
    def __init__(self, sport_name):
        self.sport_name = sport_name
        self.markets = []


class Market:
    def __init__(self, market_name):
        self.market_name = market_name
        self.events = []


class Event:
    def __init__(self, event_name):
        self.event_name = event_name
        self.players = []


class Player:
    def __init__(self, player_name):
        self.player_name = player_name
        self.odds = []


class OddsBySite:
    def __init__(self, site_name, odds):
        self.site_name = site_name
        self.odds = odds
        self.site_odds = (site_name, odds)


class TableRow:
    def __init__(self, sport_name, market_name, event_name, player_name, site_name, odds):
        self.row = (sport_name, market_name, event_name, player_name, site_name, odds)
        self.sport_name = sport_name
        self.market_name = market_name
        self.event_name = event_name
        self.player_name = player_name
        self.site_name = site_name
        self.odds = odds


class Table:
    def __init__(self):
        self.rows = []

