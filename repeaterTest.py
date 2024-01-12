# repeaterTest.py

# repeater test workflow:
# 1 - create a set of unique randomized answer sets (repeater-name / letter-of-the-alphabet pairings)
# 2 - create a corresponding PDF for each one - with the repeater labeled with said letter
# 3 - distribute the PDFs to SAR members - keep track of what member# is getting what map#
# 4 - create an online form where folks can submit their guesses
# 5 - grade the guesses and respond to the members with their results

import random
import json
import csv
import time
import string
from pypdf import PdfReader,PdfWriter
from pypdf.generic import NameObject,NumberObject

mapIDList=list(range(2100,2200)) # the list ends one element before the second argument
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

# testDict is used throughout this code

# testDict = dict of dicts
# testDict keys are test names e.g. '1001'
# testDict values are dicts of fieldnames:value key-value pairs

# 1. generate the answer sets
solutionDict={}

def buildSolutionDict():
	for id in mapIDList:
		solutionDict[str(id)]={}
		repeaterSample=random.sample(repeaters,len(repeaters)) # unique sampling
		for n in range(len(repeaterSample)):
			solutionDict[str(id)][repeaterSample[n]]=chr(65+n)
	print(json.dumps(solutionDict,indent=3))
	fileName='solutionDict_partOne'+time.strftime('%Y%m%d%H%M%S')+'.json'
	with open(fileName,'w') as ofile:
		print('Saving solutionDict to '+fileName)
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
	with open('./solutionDict_partOne_20240111063226.json','r') as f:
		print(' reading partOne soltions...')
		solutionDicts['partOne']=json.load(f)
	with open('./solutionDict_partTwo.json','r') as f:
		print(' reading partTwo soltions...')
		solutionDicts['partTwo']=json.load(f)
	with open('./solutionDict_partThree.json','r') as f:
		print(' reading partThree soltions...')
		solutionDicts['partThree']=json.load(f)
	print('solutionDicts read from file:')
	print(json.dumps(solutionDicts,indent=3))

def gradeResponse(mapID='2000',responseDict={}):
	global solutionDicts
	print('gradeResponse called for mapID='+str(mapID))
	if not responseDict:
		with open('./response.json','r') as f:
			responseDict=json.load(f)
		print('responseDict read from file:')
	print(json.dumps(responseDict,indent=3))
	scoreDict={}

	###########
	# PART ONE
	###########
	scoreDict['partOne']=0
	solutionDict=solutionDicts['partOne'].get(mapID,None)
	if not solutionDict:
		print('ERROR: specified mapID '+str(mapID)+' has no corresponding entry in solutionDicts')
		return
	partOne=responseDict.get('partOne',None)
	if not partOne:
		print('ERROR: partOne not found in response data')
		return
	# decode then deserialize, to turn this into valid json:
	# "partOne": "{\"0\":{\"0\":\"A\",\"1\":false,\"2\":false,
	# https://stackoverflow.com/a/42452833/3577105
	partOne=json.loads(partOne.encode().decode('unicode-escape'))
	# print('partOne:')
	# print(json.dumps(partOne,indent=3))

	partOneResponseDict={}
	for rowNum in partOne.keys():
		letter=[v for v in partOne[rowNum].values() if v][0]
		partOneResponseDict[letter]=repeaters[int(rowNum)]
	
	print('partOneResponseDict:')
	print(json.dumps(partOneResponseDict,indent=3))

	# # responseDict: keys = repeater names, values = guessed letter
	# # invert these for use during the grading, which iterates over letters
	# responseDict2={v:k for k,v in responseDict.items()}
	solutionDict2={v:k for k,v in solutionDict.items()}

	print('NCSSAR Repeater Test - Results for Map ID '+str(mapID))
	print('===================================')
	print('Part One - match map letters to repeater names')
	print('-----------------------------------')
	for letter in letters:
		correctRepeater=solutionDict2[letter]
		guessedRepeater=partOneResponseDict[letter]
		if guessedRepeater==correctRepeater:
			print('CORRECT: '+letter+' = '+correctRepeater)
			scoreDict['partOne']+=1
		else:
			print('INCORRECT: '+letter+' = '+correctRepeater+'  (you guessed '+guessedRepeater+')')
	print('-----------------------------------')
	score=scoreDict['partOne']
	pct=round(float(score/len(repeaters)*100))
	print('Part One Score: '+str(pct)+'%  ('+str(score)+' of '+str(len(repeaters))+')')

	###########
	# PART TWO
	###########
	scoreDict['partTwo']=0
	solutionDict=solutionDicts['partTwo']
	partTwo=responseDict.get('partTwo',None)
	if not partTwo:
		print('ERROR: partTwo not found in response data')
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
	
	print('partTwoResponseDict:')
	print(json.dumps(partTwoResponseDict,indent=3))

	# # responseDict: keys = repeater names, values = guessed letter
	# # invert these for use during the grading, which iterates over letters
	# responseDict2={v:k for k,v in responseDict.items()}
	# solutionDict2={v:k for k,v in solutionDict.items()}

	print('\n===================================')
	print('Part Two - repeaters likely to work at listed locations')
	print('-----------------------------------')
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
		print('\n'+location+':  you selected '+str(guessedRepeaters))
		if len(requiredRepeatersGuessed)==len(requiredRepeaters):
			print('    CORRECT: Your selections included all of the most likely repeaters ('+str(requiredRepeaters)+')')
			scoreDict['partTwo']+=10
		else:
			print('  INCORRECT: Your selections did not include all of the most likely repeaters ('+str(requiredRepeaters)+')')
		olen=len(optionalRepeatersGuessed)
		if olen>0:
			print('      BONUS: You selected '+str(olen)+' of the other possible repeaters ('+str(optionalRepeaters)+')')
			scoreDict['partTwo']+=olen
		ulen=len(unlikelyRepeatersGuessed)
		if ulen>0:
			print('  DEDUCTION: You selected '+str(ulen)+' of the highly-unlikely repeaters ('+str(unlikelyRepeaters)+')')
			scoreDict['partTwo']-=ulen
		maxPossibleScore+=10+olen
	print('-----------------------------------')
	score=scoreDict['partTwo']
	pct=round(float(score/maxPossibleScore*100))
	print('Part Two Score: '+str(pct)+'%  (your score: '+str(score)+'   maximum possible: '+str(maxPossibleScore)+')')

def makePDFs():

	# from https://pypdf.readthedocs.io/en/stable/user/forms.html

	reader = PdfReader(fillable_pdf)
	fields = reader.get_fields()

	for mapID in solutionDict.keys():
		# remove spaces from key names to get corresponding pdf field names
		fieldsDict={k.replace(' ',''):v for k,v in solutionDict[mapID].items()}
		fieldsDict['MAPID']=mapID
		print('building PDF for '+mapID+'...')
		writer = PdfWriter()
		writer.append(reader)
		writer.update_page_form_field_values(
			writer.pages[0],
			fieldsDict,
			auto_regenerate=False,
		)

		# flatten i.e. make the final pdf non-editable
		#  taken from https://stackoverflow.com/a/55302753/3577105
		for page in writer.pages:
			for j in range(0, len(page['/Annots'])):
				writer_annot = page['/Annots'][j].get_object()
				# flatten all the fields by setting bit position to 1
				# use loop below if only specific fields need to be flattened.
				writer_annot.update({
					NameObject("/Ff"): NumberObject(1)  # changing bit position to 1 flattens field
				})

		with open('RepeaterTest_'+str(mapID)+'.pdf', 'wb') as output_stream:
			writer.write(output_stream)


## top level code:

solutionDicts={}
# buildSolutionDict()
# makePDFs()
readSolutionDicts()
# print('guessDict 2021:')
# print(json.dumps(guessDict['2021'],indent=3))
gradeResponse('2111')