#!/usr/bin/env python
#
# Update a redis server cache when an evenement is trigger
# in MySQL replication log
#

from pymysqlreplication import BinLogStreamReader
from pymysqlreplication.row_event import *

mysql_settings = {'host': '127.0.0.1', 'port': 3306, 'user': 'root', 'passwd': ''}

def dateEncoder(obj):
    """Default JSON serializer."""
    import calendar, datetime

    if isinstance(obj, datetime.datetime):
        if obj.utcoffset() is not None:
            obj = obj - obj.utcoffset()
    millis = int(
        calendar.timegm(obj.timetuple()) * 1000 +
        obj.microsecond / 1000
    )
    return millis


import json
import cherrypy
class Streamer(object):
    def __init__(self):
        self.stream = BinLogStreamReader(connection_settings = mysql_settings,
                                         only_events = [DeleteRowsEvent, WriteRowsEvent, UpdateRowsEvent], blocking = True, resume_stream = True)
    
    def index(self):
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        def content():
            for binlogevent in self.stream:
                for row in binlogevent.rows:
                    if isinstance(binlogevent, DeleteRowsEvent):
                        yield json.dumps({
                          "action": "delete",
                          "type": binlogevent.table,
                          "id": row["values"]["id"]}) + "\n"
                    elif isinstance(binlogevent, UpdateRowsEvent):
                        yield json.dumps({
                          "action": "update",
                          "type": binlogevent.table,
                          "id": row["after_values"]["id"],
                          "doc": row["after_values"]},default=dateEncoder) + "\n"
                    elif isinstance(binlogevent, WriteRowsEvent):
                        yield json.dumps({
                          "action": "insert",
                          "type": binlogevent.table,
                          "id": row["values"]["id"],
                          "doc": row["values"]},default=dateEncoder) + "\n"
        return content()

    index.exposed = True
    index._cp_config = {"response.stream": True}

cherrypy.config.update({'server.socket_port': 8081}) 
cherrypy.quickstart(Streamer())
