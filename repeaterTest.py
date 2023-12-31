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

mapIDList=list(range(2000,2005))
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
testDict={}

def buildTestDict():
	for id in mapIDList:
		testDict[str(id)]={}
		repeaterSample=random.sample(repeaters,len(repeaters)) # unique sampling
		for n in range(len(repeaterSample)):
			testDict[str(id)][repeaterSample[n]]=chr(65+n)
	print(json.dumps(testDict,indent=3))
	fileName='testDict_'+time.strftime('%Y%m%d%H%M%S')+'.json'
	with open(fileName,'w') as ofile:
		print('Saving test dict to '+fileName)
		json.dump(testDict,ofile,indent=3)

# 2. generate the PDF for each set

# 3 and 4 - handled externally

# 5. read the results from jotform and check the answers
#    (to be done on pythonanywhere, triggered by jotform webhook)

# csvName='NCSSAR_Repeaters_Test2023-12-25_14_54_42.csv'
# with open(csvName) as f:
# 	r=csv.DictReader(f)
# 	r.fieldnames=[x.replace('NCSSAR Repeaters >> ','') for x in r.fieldnames]
# 	guessDicts=[row for row in r]

def gradeResponse():
	print(json.dumps(guessDicts,indent=3))

	score=0
	mapID='123'
	guessDict=[x for x in guessDicts if x['Map ID']==mapID][0]

	# guessDict: keys = repeater names, values = guessed letter
	guessDict2={v:k for k,v in guessDict.items()}
	answerDict2={v:k for k,v in answerDict[id].items()}

	print('Results for Map ID '+str(mapID))
	print('-------------')
	for letter in letters:
		correctRepeater=answerDict2[letter]
		guessedRepeater=guessDict2[letter]
		if guessedRepeater==correctRepeater:
			print('CORRECT: '+letter+' = '+correctRepeater)
			score+=1
		else:
			print('INCORRECT: '+letter+' = '+correctRepeater+'  (you guessed '+guessedRepeater+')')


	# for repeater in repeaters:
	# 	answer=answerDict[id].get(repeater,None)
	# 	guess=guessDict.get(repeater,None)
	# 	if guess==answer:
	# 		print('CORRECT: '+str(answer)+' = '+str(repeater))
	# 		score+=1
	# 	else:
			# print('INCORRECT: '+str(answer)+' = '+str(repeater)+' (you guessed '+str(guess)+')')

	print('-------------')
	pct=round(float(score/len(repeaters)*100))
	print('Score: '+str(pct)+'%  ('+str(score)+' of '+str(len(repeaters))+')')

	# lines=csv.reader(f)
	# # don't assume the columns are in alphabetical order
	# header=lines[0]
	# colNumDict={}
	# for n in range(len(header)):
	# 	for repeater in repeaters:
	# 		if header[n]=='NCSSAR Repeaters >> '+repeater:
	# 			colNumDict[repeater]=n
	# for line in lines[1:]:
	# 	print('LINE: '+str(line))

	# 	for repeater in repeaters:
	# 		responses[mapID][repeater]=line[colNumDict[repeater]]	

def makePDFs():

	# from https://pypdf.readthedocs.io/en/stable/user/forms.html

	reader = PdfReader(fillable_pdf)
	fields = reader.get_fields()

	for testName in testDict.keys():
		# remove spaces from key names to get corresponding pdf field names
		fieldsDict={k.replace(' ',''):v for k,v in testDict[testName].items()}
		fieldsDict['MAPID']=testName
		print('building PDF for '+testName+'...')
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

		with open('repeater_test_'+str(testName)+'.pdf', 'wb') as output_stream:
			writer.write(output_stream)


## top level code:

buildTestDict()
makePDFs()