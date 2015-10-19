import sqlite3
import json
import sys

stream_id = 0




if len(sys.argv) > 1:
    db_name = sys.argv[1]
else:
    db_name = 'log_data.sqlite3'

db = sqlite3.connect(db_name)
cursor = db.cursor()

if len(sys.argv) > 2:
    stream_id = int(sys.argv[2])
else:
    sql = "select stream_id from last_stream"
    cursor.execute(sql)
    row =  cursor.fetchone()
    stream_id = row[0]



sql = "select count(*) from log where stream_id = {0} and logger = 'DataAPIStats'".format(stream_id)
cursor.execute(sql)
row =  cursor.fetchone()
print row
#print sql
done = False

sql = "select message from log where stream_id = {0} and logger = 'DataAPIStats' order by id limit 1".format(stream_id)

while not done:
    try:
        cursor.execute(sql)
        row =  cursor.fetchone()
        message = row[0]
        done = True
    except sqlite3.OperationalError as e:
        print "locked, retrying"
        sys.stdin.flush()

idx = message.index("(delayed from")
message = message[:idx]

qparams_idx = message.index("queryParams")
resolve_idx = message.index("resolveStartTime")
#print message[qparams_idx:resolve_idx]
message = message[:qparams_idx] + 'queryParams":{"f":"topics:ajc-mobile-app-collection","detail":"full"},"' + message[resolve_idx:]
#print message
#print "_________"

data = json.loads(message)
print json.dumps(data, indent=4)
