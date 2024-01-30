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
import string
import time

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


#########################################################
############## start of repeaterTest code ###############
#########################################################


rtPath='repeaterTest'
if not os.path.isdir(rtPath):
    rtPath='.'

repeaters=[
	'ALDER HILL',
	'ALTA SIERRA',
	'BABBITT',
	'BANNER',
	'BOREAL',
	'BOWMAN',
	'CASCADE SHRS',
	'CHERRY HILL',
	'DEADMAN FLAT',
	'DONNER',
	'EDWARDS XING',
	'GROUSE RIDGE',
	'KENTKY RIDGE',
	'LOP',
	'LWW',
	'MT ROSE',
	'OREGON',
	'OWL CREEK',
	'PILOT PEAK',
	'PURDON',
	'ROLLINS LK',
	'SIERRABUTTES',
	'SIGNAL',
	'WOLF MTN'
]
locations=[
	# 'Milton Reservoir',
	# 'Shingle Falls',
	'Bridgeport covered bridge',
	# 'Emerald Pools',
	'Penner Lake',
	# 'South Yuba Primitive Camp',
	'Buckeye Rd at Chalk Bluff Rd',
	# 'Lake Sterling',
	# 'Dog Bar Rd at South Fork Wolf Creek',
	'Peter Grubb Hut',
	'Prosser Boat Ramp',
	# 'Sagehen CG',
	# 'Boyington Mill CG',
	'Pacific Crest Trail at Meadow Lake Road'
]
letters=list(string.ascii_uppercase)[0:len(repeaters)]

def readSolutionDicts():
	global solutionDicts
	with open(os.path.join(rtPath,'solutionDict_partOne20240124085012.json'),'r') as f:
		# logging.info(' reading partOne soltions...')
		solutionDicts['partOne']=json.load(f)
	with open(os.path.join(rtPath,'solutionDict_partTwo.json'),'r') as f:
		# logging.info(' reading partTwo soltions...')
		solutionDicts['partTwo']=json.load(f)
		# validate the file, to check for typos or repeated entries
		categories=['required','optional','unlikely']
		for loc in solutionDicts['partTwo'].keys():
			if sorted(solutionDicts['partTwo'][loc].keys())!=sorted(categories):
				logging.info('ERROR during read of partTwo solutions: not all of the neccesary categories are in the file for '+str(loc))
			for category in categories:
				rep=solutionDicts['partTwo'][loc][category]
				for r in rep:
					if r not in repeaters:
						logging.info('ERROR during read of partTwo solutions: '+str(loc)+': '+str(category)+': '+str(r)+' is not a valid repeater!')
					for otherCategory in [c for c in categories if c!=category]:
						if r in solutionDicts['partTwo'][loc][otherCategory]:
							logging.info('ERROR during read of partTwo solutions: '+str(loc)+': '+str(category)+': '+str(r)+' is also listed in '+str(otherCategory)+'!')

# print a list of strings as a simple human-readable list:
# ['A','B','C'] --> A,B,C
def strp(theList,spaces=True):
	s=str(theList)
	s=s.replace("'","")
	s=s.replace('[','')
	s=s.replace(']','')
	if not spaces:
		s=s.replace(', ',',')
	return s

def sendEmail(from_email,to_emails,subject,html_content):
	msg=Mail(
		from_email=from_email,
		to_emails=to_emails,
		subject=subject,
		html_content=html_content
	)
	try:
		sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)
		response = sendgrid_client.send(msg)
		logging.info('mailer response status code: '+str(response.status_code))
		logging.info('mailer response body: '+str(response.body))
		logging.info('mailer response headers: '+str(response.headers))
	except Exception as e:
		logging.info('ERROR: email not sent; mailer exception: '+str(e))
		return False
	logging.info('  email sent')
	return True

def gradeResponse(mapID='2000',responseDict={}):
	global solutionDicts
	logging.info('gradeResponse called for mapID='+str(mapID))
	if not responseDict:
		with open(os.path.join(rtPath,'response.json'),'r') as f:
			responseDict=json.load(f)
		logging.info('responseDict read from file:')
	logging.info(json.dumps(responseDict,indent=3))
	scoreDict={}
	scorePct={}
	gradedText=''

	sarID=responseDict['SARNumber']

	gradedFileName='repeaterTest_graded_'+str(mapID)+'.txt'

	###########
	# PART ONE
	###########
	scoreDict['partOne']=0
	solutionDict=solutionDicts['partOne'].get(mapID,None)
	if not solutionDict:
		logging.info('ERROR: specified mapID '+str(mapID)+' has no corresponding entry in solutionDicts')
		return
	partOne=responseDict.get('partOne',None)
	if not partOne:
		gradedText+='\nERROR: partOne not found in response data'
		logging.info('ERROR: partOne not found in response data')
		return

	# it looks like JotForm may have significantly changed the structure of their InputTable responses
	#  sometime in January 2024 (or, it could be operator confusion...)
	
	# old:
	# response={...,"partOne": "{\"0\":{\"0\":\"A\",\"1\":false,\"2\":false,...
	#  a dict of dicts, one per row, each one having an entry for each repeater,
	#  where the selected repeater number is True and all others are False

	# new:
	# resonse={...,"partOne": [{"4": "E"}, {"13": "N"}, {"1": "B"}, {"16": "Q"}, ["A"], {"21": "V"}, ...
	#  an ordered list of dicts, with index corresonding to row number (zero-based); each dict
	#   has just one key:val pair, col# (string) : colName;
	#  except, there appears to be a bug: column zero comes out as a list containing only the col name, not a dict.

	# # decode then deserialize, to turn this into valid json:
	# # "partOne": "{\"0\":{\"0\":\"A\",\"1\":false,\"2\":false,
	# # https://stackoverflow.com/a/42452833/3577105
	# partOne=json.loads(partOne.encode().decode('unicode-escape'))
	logging.info('partOne:')
	logging.info(json.dumps(partOne,indent=3))

	partOneResponseDict={}
	# 1-24-24: at this point, partOne should be a list of dicts, each with a single key (the column number);
	#  if so, replace keys (column numbers) with repeater names based on list index
	if partOne.__class__.__name__=='list':
		out={}
		for n in range(len(partOne)):
			e=partOne[n]
			if e.__class__.__name__=='list' and len(e)==1:
				letter=e[0]
			else:
				letter=list(partOne[n].values())[0]
			out[letter]=repeaters[n]
		partOneResponseDict=out
		
	# logging.info('partOne after processing:')
	# logging.info(json.dumps(partOne,indent=3))

	# for rowNum in partOne.keys():
	# 	letter=[v for v in partOne[rowNum].values() if v][0]
	# 	partOneResponseDict[letter]=repeaters[int(rowNum)]
	
	logging.info('partOneResponseDict:')
	logging.info(json.dumps(partOneResponseDict,indent=3))

	# # responseDict: keys = repeater names, values = guessed letter
	# # invert these for use during the grading, which iterates over letters
	# responseDict2={v:k for k,v in responseDict.items()}
	solutionDict2={v:k for k,v in solutionDict.items()}

	gradedText+='\nNCSSAR Repeater Test - Results for SAR'+str(sarID)+'  Map ID '+str(mapID)
	gradedText+='\n==================================='
	gradedText+='\nPart One - match map letters to repeater names'
	gradedText+='\n-----------------------------------'
	for letter in letters:
		correctRepeater=solutionDict2[letter]
		guessedRepeater=partOneResponseDict[letter]
		if guessedRepeater==correctRepeater:
			gradedText+='\n  CORRECT: '+letter+' = '+correctRepeater
			scoreDict['partOne']+=1
		else:
			gradedText+='\nINCORRECT: '+letter+' = '+correctRepeater+'  (you guessed '+guessedRepeater+')'
	gradedText+='\n-----------------------------------'
	score=scoreDict['partOne']
	pct=round(float(score/len(repeaters)*100))
	scorePct['partOne']=pct
	gradedText+='\nPart One Score: '+str(pct)+'%  ('+str(score)+' of '+str(len(repeaters))+')'

	###########
	# PART TWO
	###########
	scoreDict['partTwo']=0
	solutionDict=solutionDicts['partTwo']
	partTwo=responseDict.get('partTwo',None)
	if not partTwo:
		gradedText+='\nERROR: partTwo not found in response data'
		logging.info('ERROR: partTwo not found in response data')
		return
	# # decode then deserialize, to turn this into valid json:
	# # "partOne": "{\"0\":{\"0\":\"A\",\"1\":false,\"2\":false,
	# # https://stackoverflow.com/a/42452833/3577105
	# partTwo=json.loads(partTwo.encode().decode('unicode-escape'))
	# print('partTwo:')
	# print(json.dumps(partTwo,indent=3))

	partTwoResponseDict={}

	# 1-24-24: partTwo val is a list of lists

	for n in range(len(partTwo)):
		partTwoResponseDict[locations[n]]=partTwo[n]

	# for rowNum in partTwo.keys():
	# 	repeaterResponses=[v for v in partTwo[rowNum].values() if v]
	# 	partTwoResponseDict[locations[int(rowNum)]]=repeaterResponses
	
	logging.info('partTwoResponseDict:')
	logging.info(json.dumps(partTwoResponseDict,indent=3))

	# # responseDict: keys = repeater names, values = guessed letter
	# # invert these for use during the grading, which iterates over letters
	# responseDict2={v:k for k,v in responseDict.items()}
	# solutionDict2={v:k for k,v in solutionDict.items()}

	gradedText+='\n\n==================================='
	gradedText+='\nPart Two - repeaters likely to work at listed locations'
	gradedText+='\n-----------------------------------'
	# maxPossibleScore=0
	targetScore=0
	for location in locations:
		requiredRepeaters=solutionDict[location]['required']
		optionalRepeaters=solutionDict[location]['optional']
		unlikelyRepeaters=solutionDict[location]['unlikely']
		guessedRepeaters=partTwoResponseDict[location]
		requiredRepeatersGuessed=[]
		optionalRepeatersGuessed=[]
		unlikelyRepeatersGuessed=[]
		for repeater in guessedRepeaters:
			if repeater in requiredRepeaters:
				requiredRepeatersGuessed.append(repeater)
			elif repeater in optionalRepeaters:
				optionalRepeatersGuessed.append(repeater)
			elif repeater in unlikelyRepeaters:
				unlikelyRepeatersGuessed.append(repeater)
		gradedText+='\n\n'+location+':  you selected '+strp(guessedRepeaters)
		# print('\n'+location+':     requiredRepeatersGuessed: '+strp(requiredRepeatersGuessed),file=outfile)
		# print('\n'+location+':     optionalRepeatersGuessed: '+strp(optionalRepeatersGuessed),file=outfile)
		# print('\n'+location+':     unlikelyRepeatersGuessed: '+strp(unlikelyRepeatersGuessed),file=outfile)
		if len(requiredRepeatersGuessed)==len(requiredRepeaters):
			gradedText+='\n    CORRECT: Your selections included all of the most likely repeaters ('+strp(requiredRepeaters)+')'
			scoreDict['partTwo']+=10
		elif len(requiredRepeatersGuessed)==len(requiredRepeaters)-1:
			gradedText+='\n    PARTIAL: Your selections included all but one of the most likely repeaters ('+strp(requiredRepeaters)+')'
			scoreDict['partTwo']+=6
		else:
			gradedText+='\n  INCORRECT: Your selections did not include all of the most likely repeaters ('+strp(requiredRepeaters)+')'
		olen=len(optionalRepeatersGuessed)
		if olen>0:
			gradedText+='\n      BONUS: You selected '+str(olen)+' of the other possible repeaters ('+strp(optionalRepeaters)+')'
			scoreDict['partTwo']+=(olen*2)
		ulen=len(unlikelyRepeatersGuessed)
		if ulen>0:
			gradedText+='\n  DEDUCTION: You selected '+str(ulen)+' of the highly-unlikely repeaters ('+strp(unlikelyRepeaters)+')'
			scoreDict['partTwo']-=ulen
		# maxPossibleScore+=10+olen
		targetScore+=10
	gradedText+='\n-----------------------------------'
	score=scoreDict['partTwo']
	# pct=round(float(score/maxPossibleScore*100))
	pct=round(float(score/targetScore*100))
	scorePct['partTwo']=pct
	# print('Part Two Score: '+str(pct)+'%  (your score: '+str(score)+'   maximum possible: '+str(maxPossibleScore)+')',file=outfile)
	gradedText+='\nPart Two Score: '+str(pct)+'%  (your score: '+str(score)+'   target score: '+str(targetScore)+')'

	summary='SAR'+sarID+' : Map ID '+mapID+' : '+time.strftime('%a %b %d %H:%M:%S')
	grade='Part One: '+str(scorePct['partOne'])+'%    Part Two: '+str(scorePct['partTwo'])+'%'
	summary+='\n'+grade
	summary+='\n----------------------------------------'
	with open(os.path.join(rtPath,'summary.txt'),'a') as sf:
		print(summary,file=sf)

	testDict[sarID]['graded']=time.strftime('%a %b %d %Y %H:%M:%S')
	testDict[sarID]['grade']=grade
	rval=sendEmail(
		from_email='caver456@gmail.com',
		to_emails=['caver456@gmail.com',testDict[sarID]['email']],
		subject='Repeater Test graded results',
		html_content=(summary+'\n'+gradedText).replace('\n','<br>').replace(' ','&nbsp;')
		)
	if rval:
		testDict[sarID]['gradedEmailSent']=time.strftime('%a %b %d %Y %H:%M:%S')

def saveTestDict():
	logging.info('saving testDict to testDict.json')
	with open(os.path.join(rtPath,'testDict.json'),'w') as td:
		json.dump(testDict,td,indent=3)

def loadTestDict():
	global testDict
	logging.info('loading testDict from testDict.json')
	with open(os.path.join(rtPath,'testDict.json'),'r') as td:
		testDict=json.load(td)

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

testDict={}
solutionDicts={}

# repeater test - jotform webhook handler
@app.route('/api/v1/jotform_webhook',methods=['POST'])
def api_jotformWebhookHandler():
    global testDict
    global solutionDicts
    app.logger.info('jotform webhook handler called')
    d=extract_jotform_data()
    app.logger.info('extracted jotform data:'+json.dumps(d))
    mapID=str(d.get('mapID',None))
    app.logger.info('map ID:'+mapID)
    
    # rval=sendEmail(
    #     from_email='caver456@gmail.com',
    #     to_emails='caver456@gmail.com',
    #     subject='jotform response received',
    #     html_content='<strong>and easy to do anywhere, even with Python</strong>'
    # )
    # if rval:
    #     app.logger.info('email sent')

    testDict={}
    solutionDicts={}
    loadTestDict()
    readSolutionDicts()
    gradeResponse(mapID,d)
    saveTestDict()

    return '<h1>SignIn Database API</h1><p>RepeaterTest response accepted</p>'


#########################################################
############### end of repeaterTest code ################
#########################################################


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
