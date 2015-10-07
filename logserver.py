import time
import signal
import sys
import os
import datetime
from pprint import pprint
import traceback
import json
import sqlite3
from flask import Flask
from flask import request
from flask import render_template
from flask import send_from_directory
from flask import Flask, request, flash, url_for, redirect, render_template
from flask_sqlalchemy import SQLAlchemy


in_heroku = True
logging_url = "http://localhost:5000/"
if os.environ.get('LOG_NO_HEROKU', None):
    in_heroku = False
#logging_url = "http://192.168.100.108:5001/"
db = None
initial_stream_id = 0
current_stream_id = 0

# set the project root directory as the static folder, you can set others.
app = Flask(__name__, static_url_path='')
config_path = os.environ.get('APP_CONFIG_FILE', 'config.py')
#print "loading config from ", config_path
#app.config.from_pyfile(config_path)

@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)

@app.route('/', methods=['GET'])
def index():
    global db
    if not db:
        setup_data()
    cursor = db.cursor()
    cursor.execute('select count(*) from streams');
    row = cursor.fetchone();
    total_streams = row[0]
    try:
        return render_template('index.html',
                               total_streams=total_streams)
    except:
        traceback.print_exc()
        raise

@app.route('/buttons', methods=['GET'])
def buttons():
    try:
        return render_template('buttons.html')
    except:
        traceback.print_exc()
        raise

@app.route('/status', methods=['GET'])
def status():
    return "ok"

def to_utf8(text):
    """Convert given text to UTF-8 encoding (as far as possible)."""
    if not text:
        return text

    try: # unicode or pure ascii
        return text.encode("utf8")
    except UnicodeDecodeError:
        try: # successful UTF-8 decode means it's pretty sure UTF-8 already
            text.decode("utf8")
            return text
        except UnicodeDecodeError:
            try: # get desperate; and yes, this has a western hemisphere bias
                return text.decode("cp1252").encode("utf8")
            except UnicodeDecodeError:
                pass

    return text # return unchanged, hope for the best


@app.route('/get_logging_url', methods=['GET'])
def get_url():
    global db
    if not db:
        setup_data()
    global logging_url
    local_url = request.host_url
    if "herokuapp.com" in request.host_url:
        tmp = request.host_url.split(':')
        tmp[0] = "https"
        local_url = ":".join(tmp)
    if not logging_url:
        url = local_url
    else:
        url = logging_url

    try:
        token = request.args.get('token', None)
        platform = request.args.get('platform', None)
        version = request.args.get('version', None)
        app_id = request.args.get('app_id', None)
        cursor = db.cursor()
        cursor.execute('select url from stream_director where token=?'
                   ' and platform = ? and version = ?'
                   ' and app_id = ?', [token, platform, version, app_id])
        res = cursor.fetchone()
        if res is not None and len(res) > 0:
            url = res[0]
            if url == "local":
                url = local_url
    except:
        traceback.print_exc()

    print("returning  {}".format(url))
    return json.dumps({'status': 'ok', 'url': url})

@app.route('/stream/<int:stream_id>/record', methods=['POST'])
def stream_record(stream_id):
    global db
    if not db:
        setup_data()
    try:
        data = request.form['data']
        #pprint(data)
        jdata = json.loads('\\"'.join(data.split('\\\\"')))
        pprint(jdata)
        if db:
            for record in jdata:
                record[u'log_stream_id'] = stream_id
                for field in ['timestamp', 'logger', 'level', 'message']:
                    if field not in record:
                        if field == "timestamp":
                            record[field] = 0
                        else:
                            record[field] = "unknown"
                db.cursor().execute('insert into log (stream_id, timestamp, level, logger, message) values (?,?,?,?,?)',
                                    [stream_id, record['timestamp'], record['level'],record['logger'],record['message']])
            db.commit()
    except:
        traceback.print_exc()
    return json.dumps({'status': 'ok'})

@app.route('/get_new_stream_id', methods=['GET'])
def get_stream():
    try:
        token = request.args.get('token', None)
        platform = request.args.get('platform', None)
        version = request.args.get('version', None)
        app_id = request.args.get('app_id', None)
    except:
        traceback.print_exc()
    try:
        cursor = db.cursor()
        cursor.execute('select id from last_stream limit 1');
        row = cursor.fetchone();
        if row is None:
            current_stream_id = initial_stream_id
            cursor.execute('insert into last_stream (id) values (?)', [current_stream_id,]);
        else:
            current_stream_id = int(row[0])
            current_stream_id += 1
            cursor.execute('update last_stream set id=?', [current_stream_id,]);
        cursor.execute('insert into streams '
                       '(stream_id, timestamp, token, platform, version, app_id) '
                       'values (?,?,?,?,?,?)',
                       [current_stream_id,
                        str(datetime.datetime.utcnow()),
                        token,
                        platform,
                        version,
                        app_id])
        db.commit()
        print "returning stream id", current_stream_id
    except:
        traceback.print_exc()
        raise
    return json.dumps({'id': current_stream_id})

def setup_data():
    global initial_stream_id
    global current_stream_id
    global db
    if not db:
        if in_heroku:
            db = sqlite3.connect(':memory:')
        else:
            db = sqlite3.connect('log_data.sqlite3')
    cursor = db.cursor()
    cursor.execute('create table if not exists log (stream_id default -1, timestamp, level, logger, message);');
    cursor.execute('create table if not exists last_stream (id);');
    cursor.execute('create table if not exists streams (stream_id default -1, timestamp, token, platform, version, app_id);');

    cursor.execute('create table if not exists stream_director (token, platform, version, app_id, url);');

    cursor.execute('select id from last_stream limit 1');
    row = cursor.fetchone();
    if row is None:
        current_stream_id = initial_stream_id
    else:
        current_stream_id = int(row[0])
    db.commit()


def reset_data():
    global db
    if db:
        db.close()
    db = None

def exit_gracefully(signum, frame):
    global db
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, original_sigint)

    if db:
        db.close()
    sys.exit(1)



if __name__ == '__main__':

    for index in range(1, len(sys.argv)):
        if sys.argv[index] == '--reset-data':
            reset_data()
        if sys.argv[index].startswith('--redirect='):
            logging_url = sys.argv[index].split('=')[1]

    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)
    setup_data()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
