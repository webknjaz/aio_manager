import asyncio
import logging

from colorama import Back, Style, Fore

from sqlalchemy import event

create_engine = None
try:
    from aiopg.sa import create_engine
except ImportError:
    pass
try:
    from aiomysql.sa import create_engine
except ImportError:
    pass

from aio_manager import Command

logger = logging.getLogger(__name__)


class SACommand(Command):
    def __init__(self, name, app, declarative_base, user, password, database, host, port, engine_creator=None):
        super().__init__(name, app)
        self.declarative_base = declarative_base
        self.user = user
        self.database = database
        self.host = host
        self.port = int(port) if port else 3307
        self.password = password
        self.create_engine = engine_creator || create_engine

        if self.create_engine is None:
            raise AssertionError(
                'create_engine must be '
                'either passed via engine_creator to class constructor '
                'or one of aiopg/aiomysql should be installed.')

    @asyncio.coroutine
    def create_engine(self):
        engine = yield from self.create_engine(user=self.user,
                                               password=self.password,
                                               database=self.database,
                                               host=self.host,
                                               port=self.port,
                                               echo=True)
        return engine


class CreateTables(SACommand):
    """
    Creates DB tables for all models
    """

    def __init__(self, *args, **kwargs):
        super().__init__('init', *args, **kwargs)

    @asyncio.coroutine
    def create_tables(self):
        def receive_after_drop(target, connection, **kw):
            print('  ' + target.name + Fore.GREEN + ' created ' + Style.RESET_ALL)

        for name, table in self.declarative_base.metadata.tables.items():
            event.listen(table, 'after_create', receive_after_drop)

        print(Fore.GREEN + 'Creating all tables' + Style.RESET_ALL)
        engine = yield from self.create_engine()
        yield from self.declarative_base.metadata.create_all(engine)

    def run(self, app, args):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.create_tables())


class DropTables(SACommand):
    """
    Drops DB tables for all models
    """
    def __init__(self, *args, **kwargs):
        super().__init__('drop_tables', *args, **kwargs)

    @asyncio.coroutine
    def drop_tables(self):
        def receive_after_drop(target, connection, **kw):
            print('  ' + target.name + Fore.RED + ' dropped ' + Style.RESET_ALL)

        for name, table in self.declarative_base.metadata.tables.items():
            event.listen(table, 'after_drop', receive_after_drop)

        print(Fore.RED + 'Dropping all tables' + Style.RESET_ALL)
        engine = yield from self.create_engine()
        yield from self.declarative_base.metadata.drop_all(engine)

    def run(self, app, args):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.drop_tables())


def configure_manager(manager, app, declarative_base, user, password, database, host, port, engine_creator=None):
    manager.add_command(CreateTables(app, declarative_base,
                                     user, password, database,
                                     host, port, engine_creator))
    manager.add_command(DropTables(app, declarative_base,
                                   user, password, database,
                                   host, port, engine_creator))
