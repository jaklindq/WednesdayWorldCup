"""Playoff module"""
import logging
import re
from lib.game import PlayoffGame


class Playoff:
    """Playoff class

    Attributes:
        _log (Logger): Logger
        rounds (list): List of playoff rounds
    """

    def __init__(self):
        """Init playoff"""
        self._log = logging.getLogger(self.__class__.__name__)
        self.rounds = list()

    def sort(self):
        """Sort rounds based on order"""
        self.rounds.sort(key=lambda round_: round_.order, reverse=True)

    def evaluate(self, groups):
        """Evaluate playoff

        Sorted rounds required!

        Args:
            groups (dict): Dictionary of group_id (str): Group
        """

        first_round = self.rounds[0]
        first_round.fill_games_first_round(groups)
        previous_round = first_round
        for round_ in self.rounds[1:]:
            round_.fill_games(previous_round)
            if round_.order > 3:
                previous_round = round_

    def print(self):
        print('Playoff')
        for round_ in self.rounds:
            round_.print()


class Round:
    """Round class

    Attributes:
        _log (Logger): Logger
        id (str): ID from data source
        order (int): Power of two, showing final distance. (Number of teams in round)
        name (str): Name of round (displayed)
        parent (Round or None): None if first round
        games (dict): Dictionary of game_id (int): PlayoffGame
    """
    def __init__(self, id_):
        """Init round"""
        self._log = logging.getLogger(self.__class__.__name__)
        self.id = str()
        self.order = self.get_order(id_)
        self.name = str()
        self.parent = None
        self.games = dict()
        self.set_round_name()

    def set_round_name(self):
        """Transform order to real name

        TODO: Fix namning propagation from meta settings
        """

        if self.order > 8 and self.order % 2 == 0:
            self.name = str(self.order//2) + '-delsfinal'
        elif self.order == 8:
            self.name = 'Kvartsfinal'
        elif self.order == 4:
            self.name = 'Semifinal'
        elif self.order == 3:
            self.name = 'Bronsmatch'
        elif self.order == 2:
            self.name = 'Final'
        else:
            self._log.warning("Wrong round type: Order = {}, ID = {}"
                              .format(self.order, self.id))

    def get_order(self, round_id):
        """Get order from round name in JSON data

        Unnecessary to recompile regex but nice isolation for new data sources

        Args:
            round_id (str): Name of round in JSON data,
                e.g. round_2_loser equals bronze game ==> order 3
        """

        pattern = re.compile(r'[a-z_]+(\d+)([a-z_]*)')
        match = pattern.match(round_id)
        order = None
        special = None
        if match:
            try:
                order = int(match.group(1))
                special = match.group(2)
            except IndexError:
                self._log.error('Incorrect match from ID: {}'.format(order))
        else:
            self._log.error('Could not find order in ID: {}'.format(order))

        if order == 2 and special:
            order = 3

        return order

    def set_parent_round(self, round_):
        """Set parent round

        Rounds are hierarchical and you can quasi-recursively order them. TODO: Validate

        round_ (Round)
        """

        self.parent = round_

    def add_game(self, game):
        """Add game to playoff

        Args:
            game (PlayoffGame)
        """
        if isinstance(game, PlayoffGame):
            self.games[game.id] = game
        else:
            self._log.error('Not a playoff game: {}'.format(game.__str__))

    def fill_games_first_round(self, groups):
        """Fill games based on group results

        Args:
            groups (dict): Dictionary with group_id (str): Group
        """

        for game in self.games.values():
            home_type, home_group_key = self._get_parent_json(game.home_parent)
            away_type, away_group_key = self._get_parent_json(game.away_parent)
            group = groups.get(home_group_key)
            if group and group.finished:
                if home_type == 'winner':
                    game.home_team = group.winner
                elif home_type == 'runner':
                    game.home_team = group.runner_up
                else:
                    self._log.error('Wrong parent string')

            group = groups.get(away_group_key)
            if group and group.finished:
                if away_type == 'winner':
                    game.away_team = group.winner
                elif away_type == 'runner':
                    game.away_team = group.runner_up
                else:
                    self._log.error('Wrong parent string')

    def fill_games(self, parent_round):
        """Fill games for non-first rounds

        Args:
            parent_round (Round)
        """

        for game in self.games.values():
            parent_home_game = parent_round.games.get(game.home_parent)
            if parent_home_game and parent_home_game.finished:
                if self.order == 3:
                    game.home_team = parent_home_game.get_loser()
                else:
                    game.home_team = parent_home_game.get_winner()

            parent_away_game = parent_round.games.get(game.away_parent)
            if parent_away_game and parent_away_game.finished:
                if self.order == 3:
                    game.away_team = parent_away_game.get_loser()
                else:
                    game.away_team = parent_away_game.get_winner()

    def _get_parent_json(self, string):
        """Get parent group information

        Determine from which group a first round playoff game will pick its teams.
        Unnecessary to recompile regex but nice isolation for new data sources

        Args:
            string (str): JSON data, eg. string = 'winner_b'

        Returns:
            type_ (str): 'winner' or 'runner_up'
            group (str): Group ID (in upper case), e.g. 'C'

        """
        pattern = re.compile(r'([a-z]+)_([a-z])')

        match = pattern.match(string)
        type_, group_id = None, None
        if match:
            try:
                type_ = match.group(1)
                group_id = match.group(2).upper()  # Inconsistent group naming fix
            except IndexError:
                self._log.error('Incorrect match from string: {}'.format(string))
        else:
            self._log.error('Could not find match in string: {}'.format(string))

        return type_, group_id

    def print(self):
        print(self.name)
        print('-------')
        for game in self.games.values():
            print(game)
        print('-------')
