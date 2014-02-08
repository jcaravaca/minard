from minard import app
from flask import render_template, jsonify, request 
from minard.orca import cmos, base
from minard.database import init_db, db_session
from minard.models import *
from threading import Thread
import os, shlex
from collections import deque
from subprocess import Popen, PIPE

home = os.environ['HOME']
tail = deque(maxlen=1000)

def tail_worker(q):
    p = Popen(shlex.split('ssh -i %s/.ssh/id_rsa_builder -t snotdaq@snoplusbuilder1 tail_log data_temp' % home), stdout=PIPE)
    i = 0
    while True:
        line = p.stdout.readline()
        tail.appendleft((i,line))
        i += 1
        if not line:
            break

tail_thread = Thread(target=tail_worker,args=(tail,))
tail_thread.start() 

init_db()

PROJECT_NAME = 'Minard'
DEBUG = True
SECRET_KEY = "=S\t3w>zKIVy0n]b1h,<%|@EHBgfRJQ;A\rLC'[\x0blPF!` ai}/4W"

app.config.from_object(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/detector')
def hero():
    return render_template('detector.html')

@app.route('/daq/<name>')
def channels(name):
    return render_template('channels.html',name=name)

@app.route('/stream')
def stream():
    return render_template('stream.html')

@app.route('/alarms')
def alarms():
    return render_template('alarms.html')

@app.route('/builder')
def builder():
    return render_template('builder.html')

@app.route('/query')
def query():
    name = request.args.get('name','',type=str)

    if name == 'tail_log':
        id = request.args.get('id',0,type=int)
        return jsonify(value=[line for i, line in tail if i > id],id=max(zip(*tail)[0]))

    if name == 'sphere':
    	latest = PMT.latest()
	id, charge_occupancy = zip(*db_session.query(PMT.id, PMT.chargeocc)\
            .filter(PMT.id == latest.id).all())
        return jsonify(id=id, values2=charge_occupancy)

    if name == 'l2_info':
        id = request.args.get('id',None,type=str)

        if id is not None:
            info = db_session.query(L2).filter(L2.id == id).one()
        else:
            info = db_session.query(L2).order_by(L2.id.desc()).first()

        return jsonify(value=dict(info))

    if name == 'nhit':
        latest = Nhit.latest()
        hist = [getattr(latest,'nhit%i' % i) for i in range(30)]
        bins = range(5,300,10)
        result = dict(zip(bins,hist))
        return jsonify(value=result)

    if name == 'pos':
        latest = Position.latest()
        hist = [getattr(latest,'pos%i' % i) for i in range(13)]
        bins = range(25,650,50)
        result = dict(zip(bins,hist))
        return jsonify(value=result)

    if name == 'events':
        value = db_session.query(L2.entry_time, L2.events).order_by(L2.entry_time.desc())[:600]
        t, y = zip(*value)
        result = {'t': [x.isoformat() for x in t], 'y': y}
        return jsonify(value=result)

    if name == 'events_passed':
        value = db_session.query(L2.entry_time, L2.passed_events).order_by(L2.entry_time.desc())[:600]
        t, y = zip(*value)
        result = {'t': [x.isoformat() for x in t], 'y': y}
        return jsonify(value=result)

    def total_seconds(td):
        """Returns the total number of seconds in the duration."""
        return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

    if name == 'delta_t':
        value = db_session.query(L2).order_by(L2.entry_time.desc())[:600]
        result = {'t': [x.entry_time.isoformat() for x in value],
                  'y': [total_seconds(x.entry_time - x.get_clock()) for x in value]}
        return jsonify(value=result)

    if name == 'cmos':
        stats = request.args.get('stats','',type=str)

        if stats == 'avg':
            obj = cmos.avg
        elif stats == 'max':
            obj = cmos.max
        else:
            obj = cmos.now

        return jsonify(value=obj)

    if name == 'base':
        stats = request.args.get('stats','',type=str)

        if stats == 'avg':
            obj = base.avg
        elif stats == 'max':
            obj = base.max
        else:
            obj = base.now

        return jsonify(value=obj)

    if name == 'alarms':
        alarms = db_session.query(Alarms)
        return jsonify(messages=[dict(x) for x in alarms])
