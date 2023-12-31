# #############################################################################
#
#  signin_api.py - host web API code for sign-in app
#
#  sign-in is developed for Nevada County Sheriff's Search and Rescue
#    Copyright (c) 2020 Tom Grundy
#
#  http://github.com/ncssar/sign-in
#
#  Contact the author at nccaves@yahoo.com
#   Attribution, feedback, bug reports and feature requests are appreciated
#
#  REVISION HISTORY
#-----------------------------------------------------------------------------
#   DATE   | AUTHOR | VER |  NOTES
#-----------------------------------------------------------------------------
#  12-11-19   TMG     0.9   first upload to cloud
#
# #############################################################################

import flask
from flask import request, jsonify
from flask_sslify import SSLify # require https to protect api key etc.
# from flask_mail import Mail, Message
# import sqlite3
import json
import sys
import os
from pathlib import Path
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logging.basicConfig(filename='flask.log',format='%(asctime)s:%(message)s')

app = flask.Flask(__name__)
sslify=SSLify(app) # require https
app.config["DEBUG"] = True

# # sending emails in flask: https://mailtrap.io/blog/flask-email-sending/
# app.config['MAIL_SERVER']='smtp.gmail.com'
# app.config['MAIL_PORT']=587
# app.config['MAIL_USERNAME']='..............'
# app.config['MAIL_PASSWORD']='.........'
# app.config['MAIL_USE_TLS'] = True
# # app.config['MAIL_USE_SSL'] = True
# mail=Mail(app)

# see the help page for details on storing the API key as an env var:
# https://help.pythonanywhere.com/pages/environment-variables-for-web-apps/
SIGNIN_API_KEY=os.getenv("SIGNIN_API_KEY")
SENDGRID_API_KEY=os.getenv("SENDGRID_API_KEY")


# on pythonanywhere, the relative path ./sign-in should be added instead of ../sign-in
#  since the current working dir while this script is running is /home/caver456
#  even though the script is in /home/caver456/signin_api
# while it should be ok to load both, it's a lot cleaner to check for the
#  one that actually exists
p=Path('../sign-in')
if not p.exists():
    p=Path('./sign-in')
pr=str(p.resolve())
sys.path.append(pr)
app.logger.info("python search path:"+str(sys.path))

from signin_db import *
from signin_push import sdbPush


###############################
# decorator to require API key
# from https://coderwall.com/p/4qickw/require-an-api-key-for-a-route-in-flask-using-only-a-decorator
# modified to use Bearer token
from functools import wraps
from flask import request, abort

# The actual decorator function
def require_appkey(view_function):
    @wraps(view_function)
    # the new, post-decoration function. Note *args and **kwargs here.
    def decorated_function(*args, **kwargs):
        auth_header=flask.request.headers.get('Authorization')
        if auth_header: # should be 'Bearer <auth_token>'
            auth_token=auth_header.split(" ")[1]
        else:
            auth_token=''
        if auth_token and auth_token == SIGNIN_API_KEY:
        # if flask.request.args.get('key') and flask.request.args.get('key') == SIGNIN_API_KEY:
            return view_function(*args, **kwargs)
        else:
            flask.abort(401)
    return decorated_function
###############################


# from https://gist.github.com/fmaida/faee02b304b0444845703a3d130d928c - thanks to @fmaida
def extract_jotform_data():
    output = {}
    form_data = request.form.to_dict()
    if form_data.get("rawRequest"):
        for key, value in json.loads(form_data["rawRequest"]).items():
            # Removes the "q<number>_" part from the key name
            # Instead of "q5_quantity" we want "quantity" as the key
            temp = key.split("_")
            new_key = key if len(temp) == 1 else "_".join(temp[1:])
            # Saves the item with the new key in the dictionary
            output[new_key] = value
    return output

# repeater test - jotform webhook handler
@app.route('/api/v1/jotform_webhook',methods=['POST'])
def api_jotformWebhookHandler():
    app.logger.info('jotform webhook handler called')
    d=extract_jotform_data()
    app.logger.info('extracted jotform data:'+json.dumps(d))
    mapID=str(d.get('mapId',None))
    app.logger.info('map ID:'+mapID)
    # msg=Message('jotform submission',sender='MailBot',recipients=['caver456@gmail.com'])
    # msg.body='Received jotform submission: map ID='+mapID
    # mail.send(msg)
    app.logger.info('api key length:'+str(len(str(SENDGRID_API_KEY))))
    msg=Mail(
        from_email='caver456@gmail.com',
        to_emails='caver456@gmail.com',
        subject='jotform response received',
        html_content='<strong>and easy to do anywhere, even with Python</strong>'
    )
    try:
        sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)
        response = sendgrid_client.send(msg)
        app.logger.info('mailer response status code: '+str(response.status_code))
        app.logger.info('mailer response body: '+str(response.body))
        app.logger.info('mailer response headers: '+str(response.headers))
    except Exception as e:
        app.logger.info('mailer exception: '+str(e))
    app.logger.info('email sent')
    return '''<h1>SignIn Database API</h1>
<p>RepeaterTest response accepted</p>'''




# response = jsonified list of dict and response code
@app.route('/api/v1/events/new', methods=['POST'])
@require_appkey
def api_newEvent():
    app.logger.info("new called")
    if not request.json:
        app.logger.info("no json")
        return "<h1>400</h1><p>Request has no json payload.</p>", 400
    if type(request.json) is str:
        d=json.loads(request.json)
    else: #kivy UrlRequest sends the dictionary itself
        d=request.json
    r=sdbNewEvent(d)
    app.logger.info("sending response from api_newEvent:"+str(r))
    return jsonify(r)


@app.route('/', methods=['GET'])
@require_appkey
def home():
    return '''<h1>SignIn Database API</h1>
<p>API for interacting with the sign-in databases</p>'''


@app.route('/api/v1/events',methods=['GET'])
@require_appkey
def api_getEvents():
    lastEditSince=request.args.get("lastEditSince",0)
    eventStartSince=request.args.get("eventStartSince",0)
    nonFinalizedOnly=request.args.get("nonFinalizedOnly",False)
    nonFinalizedOnly=str(nonFinalizedOnly).lower()=='true' # convert to boolean
    app.logger.info("events called: lastEditSince="+str(lastEditSince)
            +" eventStartSince="+str(eventStartSince)
            +" nonFinalizedOnly="+str(nonFinalizedOnly))
    # response = jsonified list
    return jsonify(sdbGetEvents(lastEditSince,eventStartSince,nonFinalizedOnly))


@app.route('/api/v1/events/<int:eventID>', methods=['GET'])
@require_appkey
def api_getEvent(eventID):
    return jsonify(sdbGetEvent(eventID))


@app.route('/api/v1/roster',methods=['GET'])
@require_appkey
def api_getRoster():
    app.logger.info("roster called")
    return jsonify(sdbGetRoster())


@app.route('/api/v1/events/<int:eventID>/html', methods=['GET'])
@require_appkey
def api_getEventHTML(eventID):
    return getEventHTML(eventID)


# it's cleaner to let the host decide whether to add or to update;
# if ID, Agency, Name, and InEpoch match those of an existing record,
#  then update that record; otherwise, add a new record;
# PUT seems like a better fit than POST based on the HTTP docs
#  note: only store inEpoch to the nearest hunredth of a second since
#  comparison beyond 5-digits-right-of-decimal has shown truncation differences

@app.route('/api/v1/events/<int:eventID>', methods=['PUT'])
@require_appkey
def api_add_or_update(eventID):
    app.logger.info("put called for event "+str(eventID))
    if not request.json:
        app.logger.info("no json")
        return "<h1>400</h1><p>Request has no json payload.</p>", 400
    if type(request.json) is str:
        d=json.loads(request.json)
    else: #kivy UrlRequest sends the dictionary itself
        d=request.json
    return jsonify(sdbAddOrUpdate(eventID,d))



# finalize: eventID = cloud database event ID
# 1. set the event to finalized
# 2. call sdbPush: if it's not a d4h activity, sdbPush will end early but cleanly

@app.route('/api/v1/finalize/<int:eventID>',methods=['POST'])
@require_appkey
def api_finalize(eventID):
    app.logger.info("finalize called for event "+str(eventID))
    rval=sdbPush(eventID)
    if rval["statusCode"]>299:
        return rval["message"],rval["statusCode"]
    return jsonify(rval)


@app.errorhandler(404)
def page_not_found(e):
    return "<h1>404</h1><p>The resource could not be found.</p>", 404


# app.run() must be run on localhost flask and LAN flask, but not on cloud (WSGI);
#  check to see if the resolved path directory contains '/home'; this may
#  need to change when LAN server is incorporated, since really it is just checking
#  for linux vs windows
if '/home' not in pr:
    app.run()
