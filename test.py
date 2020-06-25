import re
import datetime
dictCompanyType =   {'Domestic Corporation with 0% Foreign Equity (All Filipino)': '1002', 'Domestic Corporation with 0% Foreign Equity (All Filipino)(Non-Profit) ': '1022', 'Domestic Corporation with 0.01% to 40% Foreign Equity': '006', 'Domestic Corporation with 0.01% to 40% Foreign Equity(Non- Profit)': '1023', 'Financing Corporation - Main - with 0% Foreign Equity (All Filipino)': '1012', 'Financing Corporation - Main - with 0.01% to 40% Foreign Equity': '1013', 'Financing Corporation - Main - with 40.01% to 100% Foreign Equity (Under FIA)': '1015', 'Foreign Owned Corporation with 40.01%-100% Foreign Equity (Under FIA)': '017', 'Foreign Owned Corporation with 40.01%-100% Foreign Equity (Under FIA)(Non-Profit)': '1024', 'Lending Corporation - Main - with 0% Foreign Equity (All Filipino)': '1009', 'Lending Corporation - Main - with 0.01% to 40% Foreign Equity': '1010', 'Lending Corporation - Main - with 40.01% to 100% Foreign Equity (under FIA)': '1011'} 


def find_word(text, search):
    result = re.findall('.*'+search+'.*', text, flags=re.IGNORECASE)
    if len(result)>0:
        return True
    else:
        return False

for companyClassification in dictCompanyType:
    shareHolderPercentage =""
    if (find_word(companyClassification, "with 0%")  ):
        shareHolderPercentage =0
    elif(find_word(companyClassification, '0.01%') and  find_word(companyClassification, '40%') ):
        shareHolderPercentage =1
    elif(find_word(companyClassification, '40.01%') and  find_word(companyClassification, '100%') ):
        shareHolderPercentage =2
    print(shareHolderPercentage)
    print(companyClassification)
    print(datetime.datetime.now())

