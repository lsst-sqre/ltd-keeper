"""Utilities for copying data from a source database to a new DB server.

Operators should use this code via the command:

   ./run.py copydb

Connection and Crossover classes are from `sqlacrossover
<https://github.com/ei-grad/sqlacrossover>`_, Copyright 2015
Andrew Grigorev. Apache license. See licenses/sqlacrossover.txt.
"""

import logging
import sqlalchemy as sa

logger = logging.getLogger(__name__)


class Connection():
    def __init__(self, url):
        self.engine = sa.create_engine(url)
        self.conn = self.engine.connect()
        self.meta = sa.MetaData()
        self.meta.reflect(self.engine)

        tables = sa.schema.sort_tables(self.meta.tables.values())
        self.tables = [i.name for i in tables]


class Crossover():

    def __init__(self, source, target, bulk):
        self.source = Connection(source)
        self.target = Connection(target)
        self.bulk = bulk

        self.insert_data = self.insert_data_simple

    def copy_data_in_transaction(self):
        with self.target.conn.begin():
            self.copy_data()

    def copy_data(self):
        if set(self.source.tables) != set(self.target.tables):
            logger.warning("Source and target database table lists are not "
                           "identical!")
        for table in self.source.tables:
            if table in self.target.tables:
                self.copy_table(table)

    def copy_table(self, table):
        offset = 0
        source_table = self.target.meta.tables[table]
        while True:
            data = list(self.source.conn.execute(
                sa.select([source_table]).offset(offset).limit(self.bulk)
            ))
            if not data:
                break
            self.insert_data(table, data)
            offset += self.bulk

    def insert_data_simple(self, table, data):
        self.target.conn.execute(self.target.meta.tables[table].insert(), data)
