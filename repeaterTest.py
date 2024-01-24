# repeaterTest.py

# repeater test workflow:
# 1 - create a set of unique randomized answer sets (repeater-name / letter-of-the-alphabet pairings)
#      buildSolutionDict()
# 2 - create a corresponding PDF for each one - with the repeater labeled with said letter
#      makePDFs()
# 3 - create the SAR-number-to-mapID pairings
# 4 - distribute the PDFs to SAR members
# 5 - create an online form where folks can submit their guesses
#      jotform
# 6 - automatically grade the guesses and respond to the members with their results
#      gradeResponse(mapID)

# data structures
# ---------------
# testDict - keeps track of each member's repeater test progress and status
#     this 
#   key: SAR number
#   value: dictionary
#      key: email (from D4H)
#      key: mapID - integer assigned by assignTests
#      key: assignmentSent - timestamp that assignment email was sent to the member
#      key: guessesReceived - timestamp that webhook handler was run
#      key: guesses - json of member guesses from webhook handler
#      key: gradeMessage - full text generated by gradeResponse
#      key: gradeSent - timestamp that graded email was sent to the member

# solutionDicts - dict of dicts containing the solutions to part one and part two

# guessesDict - from the webhook handler - compared against that member's solutionsDict by gradeResponse

import random
import json
import csv
import time
import string
import os
import logging
import sys
from pypdf import PdfReader,PdfWriter
from pypdf.generic import NameObject,NumberObject,TextStringObject,encode_pdfdocencoding
from pypdf.constants import AnnotationDictionaryAttributes,InteractiveFormDictEntries,PageAttributes,StreamAttributes,FilterTypes,FieldDictionaryAttributes,FieldFlag
from pypdf.filters import FlateDecode
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# logging: log to file and to stdout, for all messages of .info or higher
logging.basicConfig(filename='repeaterTest_'+time.strftime('%Y%m%d%H%M%S')+'.log',format='%(asctime)s:%(message)s',level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

firstMapID=2200
numberOfMaps=150

mapIDList=list(range(firstMapID,firstMapID+numberOfMaps+1)) # the list ends one element before the second argument
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
	'Milton Reservoir',
	'Shingle Falls',
	'Bridgeport covered bridge',
	'Emerald Pools',
	'Penner Lake',
	'South Yuba Primitive Camp',
	'Buckeye Rd at Chalk Bluff Rd',
	'Lake Sterling',
	'Dog Bar Rd at South Fork Wolf Creek',
	'Peter Grubb Hut',
	'Prosser Boat Ramp',
	'Sagehen CG',
	'Boyington Mill CG',
	'Pacific Crest Trail at Meadow Lake Road'
]
letters=list(string.ascii_uppercase)[0:len(repeaters)]

# the code below relies on a naming convention of fields in the fillable pdf:
#  control name = repeater name with spaces removed
#  e.g. for PILOT PEAK, the pdf control(field) name nust be PILOTPEAK
#   (since it's not clear whether spaces in control names could cause problems)

fillable_pdf='repeater_map_for_test.pdf'

SENDGRID_API_KEY=os.getenv("SENDGRID_API_KEY")

# 1. generate the answer sets
solutionDict={}

def buildSolutionDict():
	for id in mapIDList:
		solutionDict[str(id)]={}
		repeaterSample=random.sample(repeaters,len(repeaters)) # unique sampling
		for n in range(len(repeaterSample)):
			solutionDict[str(id)][repeaterSample[n]]=chr(65+n)
	logging.info(json.dumps(solutionDict,indent=3))
	fileName='solutionDict_partOne'+time.strftime('%Y%m%d%H%M%S')+'.json'
	with open(fileName,'w') as ofile:
		logging.info('Saving solutionDict to '+fileName)
		json.dump(solutionDict,ofile,indent=3)

# 2. generate the PDF for each set

# 3 and 4 - handled externally

# 5. read the results from jotform and check the answers
#    (to be done on pythonanywhere, triggered by jotform webhook)

# csvName='NCSSAR_Repeaters_Test2023-12-25_14_54_42.csv'
# with open(csvName) as f:
# 	r=csv.DictReader(f)
# 	r.fieldnames=[x.replace('NCSSAR Repeaters >> ','') for x in r.fieldnames]
# 	guessDicts=[row for row in r]

def readSolutionDicts():
	global solutionDicts
	with open('./solutionDict_partOne20240124085012.json','r') as f:
		# logging.info(' reading partOne soltions...')
		solutionDicts['partOne']=json.load(f)
	with open('./solutionDict_partTwo.json','r') as f:
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
	# with open('./solutionDict_partThree.json','r') as f:
	# 	logging.info(' reading partThree soltions...')
	# 	solutionDicts['partThree']=json.load(f)
	# logging.info('solutionDicts read from file:')
	# logging.info(json.dumps(solutionDicts,indent=3))

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

def getEmailsFromMembersJson(filename):
	# filename should be a file containing the json response from
	#  https://api.d4h.org/v2/team/members
	with open(filename,'r') as f:
		j=json.load(f)
		logging.info('D4H members data read from file: '+filename)
	d=j['data']
	rval={}
	for member in d:
		m=member['ref']
		e=member['email']
		rval[m]={}
		rval[m]['email']=e
	return rval

def assignTests(firstMapID):
	global testDict
	mapID=firstMapID
	for sarID in testDict.keys():
		testDict[sarID]['mapID']=mapID
		mapID+=1

# email is sent using API, rather than HTTP, mainly because Gmail SMTP didn't seem to work.
#  https://help.pythonanywhere.com/pages/SMTPForFreeUsers/
# Also, SendGrid has an explanation of gmail's and yahoo's increasing requirements for email,
#  which could mean that the API option will stop being viable at some point:
#  https://sendgrid.com/en-us/blog/gmail-yahoo-sender-requirements
def sendTests(sarIDList=None):
	if not sarIDList:
		sarIDList=testDict.keys()
	for sarID in sarIDList:
		sarID=str(sarID) # keys are strings, since some may include letters like 1S9
		d=testDict.get(sarID,None)
		if not d:
			logging.info('ERROR: sendTest sarID '+str(sarID)+' has no entry in testDict.')
			continue
		mapID=d.get('mapID',None)
		if not mapID:
			logging.info('ERROR: sendTest sarID '+str(sarID)+' has no specified mapID.')
			continue
		email=d.get('email',None)
		if not email:
			logging.info('ERROR: sendTest sarID '+str(sarID)+' has no associated email address.')
			continue
		logging.info('Sending Map ID '+str(mapID)+' to SAR '+str(sarID)+' at '+str(email))
		emailSubject='Repeater Locations Test: Your Map ID is '+str(mapID)
		mapLink='https://caver456.pythonanywhere.com/repeaterTest/repeaterTest_'+str(mapID)+'.pdf'
		emailBody='PDF: '+mapLink
		msg=Mail(
			from_email='caver456@gmail.com',
			to_emails=email,
			subject='Repeater Locations Test: Your Map ID is '+str(mapID),
			html_content='''
			1. Repeater Test Instructions: <a href="https://ncssar.sharepoint.com/:w:/s/MasterFile/EYFwFd0cnBpKnCCNhdQkCbsBJu3GD3aTHlUY2itlrBkEpA?e=t6n9Yx">Click Here</a><br>
			2. Your customized repeater test map PDF: <a href="%mapLink%">Click Here</a><br>
			3. Your Map ID: %mapID%<br>
			4. The test: <a href="https://www.jotform.com/form/233555430790053?SARNumber=%sarID%&mapID=%mapID%">Click Here</a>'''.replace('%mapLink%',mapLink).replace('%mapID%',str(mapID)).replace('%sarID%',sarID)
		)
		try:
			sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)
			response = sendgrid_client.send(msg)
			logging.info('mailer response status code: '+str(response.status_code))
			logging.info('mailer response body: '+str(response.body))
			logging.info('mailer response headers: '+str(response.headers))
		except Exception as e:
			logging.info('mailer exception: '+str(e))
		logging.info('  email sent')


def gradeResponse(mapID='2000',responseDict={}):
	global solutionDicts
	logging.info('gradeResponse called for mapID='+str(mapID))
	if not responseDict:
		with open('./response.json','r') as f:
			responseDict=json.load(f)
		logging.info('responseDict read from file:')
	logging.info(json.dumps(responseDict,indent=3))
	scoreDict={}

	with open('repeaterTest_graded_'+str(mapID)+'.txt','w') as outfile:

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
			logging.info('ERROR: partOne not found in response data')
			return
		# decode then deserialize, to turn this into valid json:
		# "partOne": "{\"0\":{\"0\":\"A\",\"1\":false,\"2\":false,
		# https://stackoverflow.com/a/42452833/3577105
		partOne=json.loads(partOne.encode().decode('unicode-escape'))
		logging.info('partOne:')
		logging.info(json.dumps(partOne,indent=3))

		partOneResponseDict={}
		for rowNum in partOne.keys():
			letter=[v for v in partOne[rowNum].values() if v][0]
			partOneResponseDict[letter]=repeaters[int(rowNum)]
		
		logging.info('partOneResponseDict:')
		logging.info(json.dumps(partOneResponseDict,indent=3))

		# # responseDict: keys = repeater names, values = guessed letter
		# # invert these for use during the grading, which iterates over letters
		# responseDict2={v:k for k,v in responseDict.items()}
		solutionDict2={v:k for k,v in solutionDict.items()}

		print('NCSSAR Repeater Test - Results for Map ID '+str(mapID),file=outfile)
		print('===================================',file=outfile)
		print('Part One - match map letters to repeater names',file=outfile)
		print('-----------------------------------',file=outfile)
		for letter in letters:
			correctRepeater=solutionDict2[letter]
			guessedRepeater=partOneResponseDict[letter]
			if guessedRepeater==correctRepeater:
				print('CORRECT: '+letter+' = '+correctRepeater,file=outfile)
				scoreDict['partOne']+=1
			else:
				print('INCORRECT: '+letter+' = '+correctRepeater+'  (you guessed '+guessedRepeater+')',file=outfile)
		print('-----------------------------------',file=outfile)
		score=scoreDict['partOne']
		pct=round(float(score/len(repeaters)*100))
		print('Part One Score: '+str(pct)+'%  ('+str(score)+' of '+str(len(repeaters))+')',file=outfile)

		###########
		# PART TWO
		###########
		scoreDict['partTwo']=0
		solutionDict=solutionDicts['partTwo']
		partTwo=responseDict.get('partTwo',None)
		if not partTwo:
			print('ERROR: partTwo not found in response data',file=outfile)
			logging.info('ERROR: partTwo not found in response data')
			return
		# decode then deserialize, to turn this into valid json:
		# "partOne": "{\"0\":{\"0\":\"A\",\"1\":false,\"2\":false,
		# https://stackoverflow.com/a/42452833/3577105
		partTwo=json.loads(partTwo.encode().decode('unicode-escape'))
		# print('partTwo:')
		# print(json.dumps(partTwo,indent=3))

		partTwoResponseDict={}
		for rowNum in partTwo.keys():
			repeaterResponses=[v for v in partTwo[rowNum].values() if v]
			partTwoResponseDict[locations[int(rowNum)]]=repeaterResponses
		
		logging.info('partTwoResponseDict:')
		logging.info(json.dumps(partTwoResponseDict,indent=3))

		# # responseDict: keys = repeater names, values = guessed letter
		# # invert these for use during the grading, which iterates over letters
		# responseDict2={v:k for k,v in responseDict.items()}
		# solutionDict2={v:k for k,v in solutionDict.items()}

		print('\n===================================',file=outfile)
		print('Part Two - repeaters likely to work at listed locations',file=outfile)
		print('-----------------------------------',file=outfile)
		maxPossibleScore=0
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
			print('\n'+location+':  you selected '+strp(guessedRepeaters),file=outfile)
			if len(requiredRepeatersGuessed)==len(requiredRepeaters):
				print('    CORRECT: Your selections included all of the most likely repeaters ('+strp(requiredRepeaters)+')',file=outfile)
				scoreDict['partTwo']+=10
			else:
				print('  INCORRECT: Your selections did not include all of the most likely repeaters ('+strp(requiredRepeaters)+')',file=outfile)
			olen=len(optionalRepeatersGuessed)
			if olen>0:
				print('      BONUS: You selected '+str(olen)+' of the other possible repeaters ('+strp(optionalRepeaters)+')',file=outfile)
				scoreDict['partTwo']+=olen
			ulen=len(unlikelyRepeatersGuessed)
			if ulen>0:
				print('  DEDUCTION: You selected '+str(ulen)+' of the highly-unlikely repeaters ('+strp(unlikelyRepeaters)+')',file=outfile)
				scoreDict['partTwo']-=ulen
			maxPossibleScore+=10+olen
		print('-----------------------------------',file=outfile)
		score=scoreDict['partTwo']
		pct=round(float(score/maxPossibleScore*100))
		print('Part Two Score: '+str(pct)+'%  (your score: '+str(score)+'   maximum possible: '+str(maxPossibleScore)+')',file=outfile)

# def makePDFs():

# 	# from https://pypdf.readthedocs.io/en/stable/user/forms.html

# 	reader = PdfReader(fillable_pdf)
# 	fields = reader.get_fields()

# 	partOneDict=solutionDicts['partOne']
# 	for mapID in partOneDict.keys():
# 		# remove spaces from key names to get corresponding pdf field names
# 		fieldsDict={k.replace(' ',''):v for k,v in partOneDict[mapID].items()}
# 		fieldsDict['MAPID']=mapID
# 		logging.info('building PDF for '+mapID+'...')
# 		writer = PdfWriter()
# 		writer.append(reader)
# 		writer.update_page_form_field_values(
# 			writer.pages[0],
# 			fieldsDict,
# 			1, # has no effect - fields are still blank in Chrome extension
# 			auto_regenerate=True, # sets need_appearances which seems to help
# 		)

# 		# flatten i.e. make the final pdf non-editable
# 		#  taken from https://stackoverflow.com/a/55302753/3577105
# 		for page in writer.pages:
# 			for j in range(0, len(page['/Annots'])):
# 				writer_annot = page['/Annots'][j].get_object()
# 				# flatten all the fields by setting bit position to 1
# 				# use loop below if only specific fields need to be flattened.
# 				writer_annot.update({
# 					NameObject("/Ff"): NumberObject(1)  # changing bit position to 1 flattens field
# 				})

# 		with open('repeaterTest_'+str(mapID)+'.pdf', 'wb') as output_stream:
# 			writer.write(output_stream)

# def makePDFs():
# 	# This attempt, from https://github.com/py-pdf/pypdf/issues/355#issuecomment-1906789915
# 	#  shows fields correctly in Chrome Acrobat Reader extension (after flicker);
# 	#  on the phone, it does allow download-by-tap but does not show fields regardless
# 	#   of View settings in the acrobat reader app.

# 	reader = PdfReader(fillable_pdf)
# 	fields = reader.get_fields()

# 	partOneDict=solutionDicts['partOne']
# 	for mapID in partOneDict.keys():
# 		# remove spaces from key names to get corresponding pdf field names
# 		fieldsDict={k.replace(' ',''):v for k,v in partOneDict[mapID].items()}
# 		fieldsDict['MAPID']=mapID
# 		logging.info('building PDF for '+mapID+'...')
# 		writer = PdfWriter()
# 		writer.set_need_appearances_writer()
# 		page0=reader.pages[0]
# 		form_fields=page0.get('/Annots')
# 		for field in form_fields.get_object():
# 			field_object=field.get_object()
# 			field_object.update({
# 				NameObject('/V'):create_string_object('A'),
# 				NameObject('/Ff'): NumberObject(1)  # changing bit position to 1 flattens field
# 			})
# 		writer.add_page(page0)
# 		with open('repeaterTest_'+str(mapID)+'.pdf', 'wb') as output_stream:
# 			writer.write(output_stream)


def makePDFs():
	# this solution works for all but Read Mode on the phone:
	# https://stackoverflow.com/a/73655665/3577105
	#  the main difference is that it doesn't rely upon NeedAppearances,
	#   and actually creates stream objects instead
	template = PdfReader(fillable_pdf)

	partOneDict=solutionDicts['partOne']
	for mapID in partOneDict.keys():
		logging.info('building PDF for '+mapID+'...')
		# Initialize writer.
		writer = PdfWriter()

		# Add the template page.
		writer.add_page(template.pages[0])

		# Get page annotations.
		page_annotations = writer.pages[0][PageAttributes.ANNOTS]
		# page_annotations = writer.pages[0]['/Annots']
		
		# remove spaces from key names to get corresponding pdf field names
		data={k.replace(' ',''):v for k,v in partOneDict[mapID].items()}
		data['MAPID']=mapID

		# Loop through page annotations (fields).
		for index in range(len(page_annotations)):  # type: ignore
			# Get annotation object.
			annotation = page_annotations[index].get_object()  # type: ignore

			# Get existing values needed to create the new stream and update the field.
			field = annotation.get(NameObject("/T"))
			new_value = data.get(field, 'N/A')
			ap = annotation.get(AnnotationDictionaryAttributes.AP)
			x_object = ap.get(NameObject("/N")).get_object()
			font = annotation.get(InteractiveFormDictEntries.DA)
			rect = annotation.get(AnnotationDictionaryAttributes.Rect)

			# Calculate the text position.
			font_size = float(font.split(" ")[1])
			w = round(float(rect[2] - rect[0] - 2), 2)
			h = round(float(rect[3] - rect[1] - 2), 2)
			text_position_h = h / 2 - font_size / 3  # approximation

			# Create a new XObject stream.
			new_stream = f'''
				/Tx BMC 
				q
				1 1 {w} {h} re W n
				BT
				{font}
				2 {text_position_h} Td
				({new_value}) Tj
				ET
				Q
				EMC
			'''

			# Add Filter type to XObject.
			x_object.update(
				{
					NameObject(StreamAttributes.FILTER): NameObject(FilterTypes.FLATE_DECODE)
				}
			)

			# Update and encode XObject stream.
			x_object._data = FlateDecode.encode(encode_pdfdocencoding(new_stream))

			# Update annotation dictionary.
			annotation.update(
				{
					# Update Value.
					NameObject(FieldDictionaryAttributes.V): TextStringObject(
						new_value
					),
					# Update Default Value.
					NameObject(FieldDictionaryAttributes.DV): TextStringObject(
						new_value
					),
					# Set Read Only flag.
					NameObject(FieldDictionaryAttributes.Ff): NumberObject(
						FieldFlag(1)
					)
				}
			)

		# Clone document root & metadata from template.
		# This is required so that the document doesn't try to save before closing.
		# writer.clone_reader_document_root(template)

		# write "output".
		with open('repeaterTest_'+str(mapID)+'.pdf', 'wb') as output_stream:
			writer.write(output_stream)

## top level code:

logging.info('test')

# testDict will either be created from scratch here, or, loaded from a file
testDict={}

# initialize testDict: key = SAR ID; val = dict, with one entry for now:
#   key = 'email', val = member's email address from D4H
testDict=getEmailsFromMembersJson('members.json')

logging.info('testDict before assignTests:\n'+json.dumps(testDict,indent=3))

# add to each member's testDict entry: key = 'mapID', val = integer map number
assignTests(firstMapID)

logging.info('testDict after assignTests:\n'+json.dumps(testDict,indent=3))

# send email to members
# sendTests([35])

solutionDicts={}
# buildSolutionDict()
readSolutionDicts()
# makePDFs()
# logging.info('guessDict 2021:')
# logging.info(json.dumps(guessDict['2021'],indent=3))
gradeResponse('2242')


# class repeaterTest():
# 	def __init__(self):
# 		self.testDict={}
	
# 	def buildSolutionDict(self):