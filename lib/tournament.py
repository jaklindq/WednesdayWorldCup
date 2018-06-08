"""Tournament module"""
import os
import logging
from attrdict import AttrDict
from collections import OrderedDict
import urllib.request
import random
from util.io import read_json_to_attrdict
from lib.team import Team
from lib.group import Group
from lib.game import GroupGame
from lib.playoff import Playoff
from lib.playoff import Round
from lib.game import PlayoffGame


class Tournament(object):
    """Tournament class
    TODO: Separate groups class

    Attributes:
        _log (Logger): Logger
        _settings (AttrDict): Meta settings
        teams (dict): Dict of all Teams
        groups (dict): Dict of all Groups
        games (dict): Dict of all Games
        playoff (Playoff)
    """

    def __init__(self, settings):
        """Initialise tournament

        Args:
            settings (AttrDict): General settings
        """
        self._log = logging.getLogger(self.__class__.__name__)
        self._settings = settings
        self.teams = dict()
        self.groups = dict()
        self.games = dict()
        self.playoff = Playoff()

        # In case of JSON file from Github
        if settings.data.src == 'github':
            self.url = settings.data.url
            self.data_root = os.path.join(self._settings.root, self._settings.data.dir)
            self.data_file = 'data' + self._settings.data.extension
        else:
            self._log.error('No other source than Github found yet')

    def evaluate(self):
        for group in self.groups.values():
            group.evaluate()
        self.playoff.evaluate(self.groups)

    def populate(self):
        """Set current tournament state."""
        src = self._settings.data.src
        self._update_data(src)
        if src == 'github':
            self._populate_from_json()
        else:
            self._log.error('No other source than Github found yet')

    def _update_data(self, src):
        if src == 'github':
            urllib.request.urlretrieve(self.url, os.path.join(self.data_root, self.data_file))
        else:
            self._log.error('No other source than Github found yet')

    def _populate_from_json(self):
        """Ugly match up to force the Github JSON data to the class structure"""
        self._log.info("Settings teams")
        data_dict = read_json_to_attrdict(os.path.join(self.data_root, self.data_file))
        for team_data in data_dict.teams:
            team = Team()
            team.init_from_json(team_data)
            self.teams[team.id] = team

        self._log.info("Settings groups")
        data_dict = read_json_to_attrdict(os.path.join(self.data_root, self.data_file))
        for group_id in data_dict.groups:
            group_data = AttrDict(data_dict.groups[group_id])
            group = Group()
            group.init_from_json(group_data, self._settings.naming.group_prefix)
            for game_data in group_data.matches:
                game = GroupGame()
                game.init_from_json(game_data, self.teams)
                game.set_group(group)
                self.games[game.id] = game  # maybe redundant

                group.add_game(game)
                group.add_teams(game.home_team, game.away_team)

            self.groups[group.id] = group
        self._sort_groups()

        self._log.info("Settings playoff")
        for id_ in data_dict.knockout:
            round_data = AttrDict(data_dict.knockout[id_])
            round_ = Round(id_)

            for game_data in round_data.matches:
                game = PlayoffGame()
                game.init_from_json(game_data, self.teams)
                game.set_order(round_.order)
                self.games[game.id] = game
                round_.add_game(game)
            self.playoff.rounds.append(round_)
        self.playoff.sort()

    def _sort_groups(self):
        """Sort groups and group games
        Intergroup sort on group name
        Intragroup sort of group matches on date
        """
        self.groups = OrderedDict(sorted(self.groups.items(), key=lambda t: t[0]))
        for group in self.groups.values():
            group.sort()

    def generate_dummy_results(self, fix_seed=False, playoff=False):
        """TODO: Fix seed"""
        for game in self.games.values():
            if isinstance(game, GroupGame) or playoff:
                game.finished = True
                game.home_result = random.randint(0, 4)
                game.away_result = random.randint(0, 4)
                if isinstance(game, PlayoffGame) and game.home_result == game.away_result:
                    game.home_result += 1

    def print_games(self):
        prev_game_day = -1
        for game in sorted(self.games.values(), key=lambda game: game.game_day):

            if game.game_day == prev_game_day:
                game.print()
            else:
                print('\nDay: {}\t {}\n'.format(game.game_day, game.date))
                game.print()
            prev_game_day = game.game_day

    def print_groups(self):
        for _, group in self.groups.items():
            group.print()
            print('\n')

    def print_playoff(self):
        self.playoff.print()
