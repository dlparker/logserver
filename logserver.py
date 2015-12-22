import time
import signal
import sys
import os
import datetime
from pprint import pprint
import traceback
import json
from flask import Flask
from flask import request
from flask import render_template
from flask import send_from_directory
from flask import Flask, request, flash, url_for, redirect, render_template
from flask.ext.cors import CORS
from database import db, create_model_tables



initial_stream_id = 0
current_stream_id = 0
app = Flask(__name__, static_url_path='')

CORS(app)

class LastStream(db.Model):
    __tablename__ = 'last_stream'
    id = db.Column(db.Integer, primary_key=True)
    stream_id = db.Column(db.Integer, unique=True)

    def __init__(self, stream_id):
        self.stream_id = stream_id

class Stream(db.Model):
    __tablename__ = 'streams'
    id = db.Column(db.Integer, primary_key=True)
    stream_id = db.Column(db.Integer, index=True)
    timestamp = db.Column(db.DateTime, index=True)
    token = db.Column(db.String(120), index=True)
    platform = db.Column(db.String(120), index=True)
    version = db.Column(db.String(120), index=True)
    app_id = db.Column(db.String(120), index=True)

    def __init__(self, stream_id, token, platform,
                 version, app_id, timestamp=None):
       self.stream_id = stream_id
       self.token = token
       self.platform = platform
       self.version = version
       self.app_id = app_id
       if not timestamp:
           timestamp = datetime.datetime.utcnow()
       self.timestamp = timestamp

class StreamDirector(db.Model):
    __tablename__ = 'stream_director'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(120), index=True)
    platform = db.Column(db.String(120), index=True)
    version = db.Column(db.String(120), index=True)
    app_id = db.Column(db.String(120), index=True)
    url = db.Column(db.String(4000))

    def __init__(self, token, platform, version, app_id, url):
       self.token = token
       self.platform = platform
       self.version = version
       self.app_id = app_id
       self.url = url

class LogRecord(db.Model):
    __tablename__ = 'log'
    id = db.Column(db.Integer, primary_key=True)
    sent_timestamp = db.Column(db.String(120))
    logger = db.Column(db.String(120))
    level = db.Column(db.String(30))
    message = db.Column(db.Text)
    stream_id = db.Column(db.Integer, index=True)
    local_timestamp = db.Column(db.DateTime, index=True)
    token = db.Column(db.String(120))
    platform = db.Column(db.String(120))
    version = db.Column(db.String(120))
    app_id = db.Column(db.String(120))

    def __init__(self, stream, timestamp, level, logger, message):
       self.sent_timestamp = timestamp
       self.logger = logger
       self.level = level
       self.message = message
       self.stream_id = stream.stream_id
       self.token = stream.token
       self.platform = stream.platform
       self.version = stream.version
       self.app_id = stream.app_id
       local_timestamp = datetime.datetime.utcnow()


@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)

@app.route('/', methods=['GET'])
def index():

    try:
        total_streams = Stream.query.count()
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
    try:
        return get_url_inner()
    except:
        traceback.print_exc()
        raise
def get_url_inner():
    logging_url = app.config['LOGGING_URL']
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
        q = StreamDirector.query.filter_by(token=token,
                                           platform=platform,
                                           version=version,
                                           app_id=app_id)
        if q.count() > 0:
            url = q[0].url
            if url == "local":
                url = local_url
    except:
        traceback.print_exc()

    print("returning  {}".format(url))
    return json.dumps({'status': 'ok', 'url': url})

@app.route('/stream/<int:stream_id>/record', methods=['POST'])
def stream_record(stream_id):
    try:
        data = request.form['data']
        #pprint(data)
        jdata = json.loads('\\"'.join(data.split('\\\\"')))
        pprint(jdata)
        q = Stream.query.filter_by(stream_id=stream_id)
        stream = q[0]
        for record in jdata:
            record[u'log_stream_id'] = stream_id
            for field in ['timestamp', 'logger', 'level', 'message']:
                if field not in record:
                    if field == "timestamp":
                        record[field] = 0
                    else:
                        record[field] = "unknown"
            rec = LogRecord(stream,
                            record['timestamp'],
                            record['level'],
                            record['logger'],
                            record['message'])
            db.session.add(rec)
        db.session.commit()
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
        all = LastStream.query.all()

        stream_id = 0
        if len(all) == 0:
            ls = LastStream(stream_id)
            db.session.add(ls)
        else:
            ls = all[0]
            stream_id = ls.stream_id + 1
            ls.stream_id = stream_id
        stream =  Stream(stream_id, token, platform, version, app_id)
        print stream.__dict__
        db.session.add(stream)
        db.session.commit()
        print "returning stream id", stream_id
    except:
        traceback.print_exc()
        raise
    return json.dumps({'id': stream_id})


@app.route('/admin/streams')
@app.route('/admin/streams/pg<int:page>')
def admin_streams(page=1):
    streams = Stream.query.paginate(
        page, app.config["STREAMS_PER_PAGE"]
    )
    total_streams = Stream.query.count()
    return render_template(
        'streams.html',
        streams=streams,
        total_streams=total_streams
    )

@app.route('/admin/records/<int:stream_id>')
@app.route('/admin/records/<int:stream_id>/pg<int:page>')
def admin_records(stream_id, page=1):
    records = LogRecord.query.filter_by(stream_id=stream_id).paginate(
        page, app.config["RECORDS_PER_PAGE"]
    )
    total_records = LogRecord.query.filter_by(stream_id=stream_id).count()
    return render_template(
        'records.html',
        records=records,
        stream_id=stream_id,
        total_records=total_records
    )

def exit_gracefully(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, original_sigint)

    db.session.close()
    sys.exit(1)


def create_app():
# set the project root directory as the static folder, you can set others.
    config_path = os.environ.get('APP_CONFIG_FILE', 'config.py')
    print "loading config from ", config_path
    app.config.from_pyfile(config_path)
    with app.app_context():
        db.init_app(app)
        create_model_tables()
    return app


if __name__ == '__main__':
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)
    port = int(os.environ.get("PORT", 5000))
    app = create_app()
    app.run(host='0.0.0.0', port=port)
