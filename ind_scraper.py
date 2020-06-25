import requests
import datetime
from lxml import html
import json
from bs4 import BeautifulSoup
import re
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

### UTILITY METHOD #####
def find_word(text, search):
    result = re.findall('.*'+search+'.*', text, flags=re.IGNORECASE)
    if len(result)>0:
        return True
    else:
        return False

# Use a service account
cred = credentials.Certificate('./devServiceAccount.json')
firebase_admin.initialize_app(cred)

db = firestore.client()


userName="sachin@emerhub.com"
session_requests = requests.session()

#https://crs.sec.gov.ph/getUserAuthentication?hashun=sachin%40emerhub.com&hashps=lolypoly&_csrftoken=481f63ca4b3fd18ab06a3d0506d5ca9c
##### Get CSRF TOKEN ######
login_url="https://crs.sec.gov.ph/login"
result = session_requests.get(login_url)

tree = html.fromstring(result.text)
authenticity_token = list(set(tree.xpath("//input[@name='_csrftoken']/@value")))[0]
print(authenticity_token)
##### END Get CSRF TOKEN ######

##### GET AUTHORIZED USER ######


authUrl="https://crs.sec.gov.ph/getUserAuthentication?hashun=sachin@emerhub.com&hashps=lolypoly&_csrftoken="+authenticity_token
print(authUrl)
authRes = session_requests.post(url = authUrl) 

##### END GET AUTHORIZED USER ######

##### LOGIN USER ######
if authRes.text == "authorized":
    loginPayload = {
        "user": userName, 
        "_csrftoken": authenticity_token
    }

    loginRes = session_requests.post(url = login_url,data = loginPayload)
    ##### END LOGIN USER ######


    ##### SCRAP THE API ######
    dictCompanyType =   {   0:{"id":"001","name":"Stock Corporation",},
                            1:{"id":"002","name":"Non-Stock Corporation"},
                            2:{"id":"003","name":"Foreign Stock Corporation"},
                            3:{"id":"004","name":"Foreign Non-Stock Corporation"},
                            4:{"id":"005","name":"General Partnership"},
                            5:{"id":"006","name":"Limited Partnership"},
                            6:{"id":"007","name":"Professional Partnership"}
                        } 
                        
    for companytype in dictCompanyType:
        
        dictCompanytype={
            'refId': dictCompanyType[companytype]['id'],
            'name': dictCompanyType[companytype]['name'],
            'created':datetime.datetime.now(),
            'updated':datetime.datetime.now(),
        }
        ##doc_ref = db.collection('philippines_company_type')
        ##doc_ref.add(dictCompanytype)

        with open("philippines_company_type.json", mode='w', encoding='utf-8') as f:
            json.dump([], f)
        with open("philippines_company_type.json", mode='w', encoding='utf-8') as feedsjson:
            entry = {'name': args.name, 'url': args.url}
            feeds.append(dictCompanytype)
            json.dump(feeds, feedsjson)

        urlCompanyType="https://crs.sec.gov.ph/getCompanySubtypes.json?companyType="+dictCompanyType[companytype]['id']
        scrapCompanyClassification = session_requests.get(
            urlCompanyType, 
            headers = dict(referer = urlCompanyType)
        )
        resCompanyClassification=json.loads(scrapCompanyClassification.text)
        for companyClassification in resCompanyClassification:
            
            shareHolderPercentage =""
            if (find_word(companyClassification, "with 0%")  ):
                shareHolderPercentage =0
            elif(find_word(companyClassification, "0.01%") and  find_word(companyClassification, "40%") ):
                shareHolderPercentage =1
            elif(find_word(companyClassification, "40.01%") and  find_word(companyClassification, "100%") ):
                shareHolderPercentage =2
            dictCompanyClassification={
                'refId':   resCompanyClassification[companyClassification],
                'name': companyClassification,
                'companyTypeID': dictCompanyType[companytype]['id'],
                'created':datetime.datetime.now(),
                'updated':datetime.datetime.now(),
                'shareHolderPercentage':shareHolderPercentage

            }
            ##doc_ref = db.collection('philippines_company_classification')
            ###doc_ref.add(dictCompanyClassification)
            
            urlcompanyClassification="https://crs.sec.gov.ph/getSections.json?companyType="+dictCompanyType[companytype]['id']+"&companySubtype="+resCompanyClassification[companyClassification]
            scrapIndustryClassification = session_requests.get(
            urlcompanyClassification, 
            headers = dict(referer = urlcompanyClassification)
            )
            resIndustryClassification=json.loads(scrapIndustryClassification.text)
            for industryClassification in resIndustryClassification:
                dictIndustryClassification={
                    'refId':industryClassification,
                    'name':resIndustryClassification[industryClassification],
                    'created':datetime.datetime.now(),
                    'updated':datetime.datetime.now(),
                    'shareHolderPercentage':shareHolderPercentage,
                    'companyTypeID': dictCompanyType[companytype]['id'],
                    'companyClassificationeID': resCompanyClassification[companyClassification],
                }
                #print(dictIndustryClassification)
                ##doc_ref = db.collection('philippines_industry_classification')
                ##doc_ref.add(dictIndustryClassification)

                urlIndustryClassification="https://crs.sec.gov.ph/getSubclassBySection.json?companyType="+dictCompanyType[companytype]['id']+"&companySubtype="+resCompanyClassification[companyClassification]+"&section="+industryClassification
                scrapSubclass= session_requests.get(
                urlIndustryClassification, 
                headers = dict(referer = urlIndustryClassification)
                )
                resSubclass=json.loads(scrapSubclass.text)
                for subclass in resSubclass:
                    dictSubclass={
                        'refId':resSubclass[subclass],
                        'name':subclass,
                        'created':datetime.datetime.now(),
                        'updated':datetime.datetime.now(),
                        'shareHolderPercentage':shareHolderPercentage,
                        'companyTypeID': dictCompanyType[companytype]['id'],
                        'companyClassificationeID': resCompanyClassification[companyClassification],
                        'industryClassificationID': industryClassification,
                    }
                    ##doc_ref = db.collection('philippines_business_activities')
                    ##doc_ref.add(dictSubclass)
                    print(dictSubclass)
                    with open("philippines_business_activities.json", mode='w', encoding='utf-8') as f:
                        json.dump([], f)
                    with open("philippines_business_activities.json", mode='w', encoding='utf-8') as feedsjson:
                        #entry = dictSubclass
                        feeds.append(dictSubclass)
                        json.dump(feeds, feedsjson)
            
    
    ##### END SCRAP THE API ######
