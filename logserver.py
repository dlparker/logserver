import time
import signal
import sys
import os
from pprint import pprint
import traceback
import json
import sqlite3
from flask import Flask
from flask import request
from flask import render_template
from flask import send_from_directory

db = None
logging_url = http://10.10.11.225:5000/
initial_stream_id = 0
current_stream_id = 0

# set the project root directory as the static folder, you can set others.
app = Flask(__name__, static_url_path='')

@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)

@app.route('/', methods=['GET'])
def home():
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
    if not logging_url:
        if "herokuapp.com" in request.host_url:
            tmp = request.host_url.split(':')
            tmp[0] = "https"
            url = ":".join(tmp)
        else:
            url = request.host_url
    else:
        url = logging_url
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
    global db
    if not db:
        setup_data()
    try:
        cursor = db.cursor()
        cursor.execute('select id from streams limit 1');
        row = cursor.fetchone();
        if row is None:
            current_stream_id = initial_stream_id
            cursor.execute('insert into streams (id) values (?)', [current_stream_id,]);
        else:
            current_stream_id = int(row[0])
            current_stream_id += 1
            cursor.execute('update streams set id=?', [current_stream_id,]);
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
        db = sqlite3.connect(':memory:')
    cursor = db.cursor()
    cursor.execute('create table if not exists log (stream_id default -1, timestamp, level, logger, message);');
    cursor.execute('create table if not exists streams (id);');
    cursor.execute('select id from streams limit 1');
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

    do_exit = False
    try:
        if raw_input("\nReally quit? (y/n)> ").lower().startswith('y'):
            do_exit = True

    except KeyboardInterrupt:
        print("Ok ok, quitting")
        do_exit = True

    if do_exit:
        if db:
            db.close()
        sys.exit(1)

    # restore the exit gracefully handler here
    signal.signal(signal.SIGINT, exit_gracefully)


if __name__ == '__main__':

    for index in range(1, len(sys.argv)):
        if sys.argv[index] == '--reset-data':
            reset_data()
        if sys.argv[index].startswith('--redirect='):
            logging_url = sys.argv[index].split('=')[1]

    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)
    setup_data()
    app.run(host="0.0.0.0")
