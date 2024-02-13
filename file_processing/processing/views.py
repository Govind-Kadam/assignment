import os, sys
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
from file_processing.settings import BASE_DIR

# xml_file = "/home/vassar/Downloads/Input.xml"
output_file = os.path.join(BASE_DIR, 'result.xlsx')


class ProcessingAPI(APIView):
    """API to get input as xml file and process the data for transaction where voucher type is receipt
    API url:  "http://127.0.0.1:7001/file_processing/process/" (change path based on your server)
    Input: xml file (select file from form data of body and pass key as 'xml_file' and then in value select your input xml file)
    Output: Excel file with extension as .xlsx"""

    @staticmethod
    def post(request, *args, **kwargs):
        try:
            # Assuming xml_file contains the XML content
            xml_content_bytes = request.data['xml_file'].read()

            # Decode the bytes string
            xml_content_str = xml_content_bytes.decode('utf-8')

            # Parse the XML content string using ElementTree
            root = ET.fromstring(xml_content_str)

            # while reading direct file path as input
            # tree = ET.parse(xml_file)
            # root = tree.getroot()

            # Initialize lists to store data
            data = {'Date': [], 'Transaction Type': [], 'Vch No.': [], 'Ref No.': [], 'Ref Type': [], 'Ref Date': [],
                    'Debtor': [], 'Ref Amount': [], 'Amount': [], 'Particulars': [], 'Vch Type': [],
                    'Amount Verified': []}

            # Parse XML and extract data
            for voucher in root.findall('.//VOUCHER'):
                vch_date = voucher.find('DATE').text
                vch_type = voucher.find('VOUCHERTYPENAME').text
                vch_number = voucher.find('VOUCHERNUMBER').text

                if vch_type == 'Receipt':

                    # Parent transaction
                    parent_entry = voucher.find("./ALLLEDGERENTRIES.LIST[ISPARTYLEDGER='Yes']")
                    parent_ledger_name = parent_entry.find('LEDGERNAME').text
                    parent_amount = float(parent_entry.find('AMOUNT').text)

                    if parent_entry is not None:
                        data['Date'].append(datetime.strptime(vch_date, '%Y%m%d').strftime('%d-%m-%Y'))
                        data['Transaction Type'].append('Parent')
                        data['Vch No.'].append(vch_number)
                        data['Ref No.'].append('NA')
                        data['Ref Type'].append('NA')
                        data['Ref Date'].append('NA')
                        data['Debtor'].append(parent_ledger_name)
                        data['Ref Amount'].append('NA')
                        data['Amount'].append(parent_amount)
                        data['Particulars'].append(parent_ledger_name)
                        data['Vch Type'].append(vch_type)

                        # Calculate sum of Ref Amount for parent's child transactions
                        child_entries_agst_ref = voucher.findall("./ALLLEDGERENTRIES.LIST/BILLALLOCATIONS.LIST/[BILLTYPE='Agst Ref']")
                        child_entries_new_ref = voucher.findall("./ALLLEDGERENTRIES.LIST/BILLALLOCATIONS.LIST/[BILLTYPE='New Ref']")

                        total_child_amount = sum(float(child_entry.find('AMOUNT').text) for child_entry in child_entries_agst_ref)
                        total_child_amount += sum(float(child_entry.find('AMOUNT').text) for child_entry in child_entries_new_ref)

                        # Verify if the sum of Ref Amount equals the parent's amount
                        if total_child_amount == parent_amount:
                            data['Amount Verified'].append('Yes')
                        else:
                            data['Amount Verified'].append('NA')

                    # Child transaction
                    child_entries = voucher.findall("./ALLLEDGERENTRIES.LIST/BILLALLOCATIONS.LIST")
                    for child_entry in child_entries:
                        ref_type = None
                        bill_type_element = child_entry.find("BILLTYPE")
                        if bill_type_element is not None:
                            ref_type = bill_type_element.text

                        child_ledger_name = voucher.find("./ALLLEDGERENTRIES.LIST/LEDGERNAME").text
                        if ref_type in ['Agst Ref', 'New Ref']:
                            ref_no = child_entry.find("NAME").text
                            child_amount = float(child_entry.find('AMOUNT').text)
                            data['Date'].append(datetime.strptime(vch_date, '%Y%m%d').strftime('%d-%m-%Y'))
                            data['Transaction Type'].append('Child')
                            data['Vch No.'].append(vch_number)
                            data['Ref No.'].append(ref_no)
                            data['Ref Type'].append(ref_type)
                            data['Ref Date'].append('NA')
                            data['Debtor'].append(child_ledger_name)
                            data['Ref Amount'].append(child_amount)
                            data['Amount'].append('NA')
                            data['Particulars'].append(child_ledger_name)
                            data['Vch Type'].append(vch_type)
                            data['Amount Verified'].append('NA')

                    # Bank transaction (Other)
                    bank_entry = voucher.find("./ALLLEDGERENTRIES.LIST[LEDGERNAME='Standard Chartered Bank']")
                    if bank_entry is not None:
                        bank_ledger_name = bank_entry.find('LEDGERNAME').text
                        bank_amount = float(bank_entry.find('AMOUNT').text)
                        data['Date'].append(datetime.strptime(vch_date, '%Y%m%d').strftime('%d-%m-%Y'))
                        data['Transaction Type'].append('Other')
                        data['Vch No.'].append(vch_number)
                        data['Ref No.'].append('NA')
                        data['Ref Type'].append('NA')
                        data['Ref Date'].append('NA')
                        data['Debtor'].append(bank_ledger_name)
                        data['Ref Amount'].append('NA')
                        data['Amount'].append(bank_amount)  # Negative for bank entries
                        data['Particulars'].append(bank_ledger_name)
                        data['Vch Type'].append(vch_type)
                        data['Amount Verified'].append('NA')

            # Create DataFrame
            df = pd.DataFrame(data)
            # Save to Excel
            df.to_excel(output_file, index=False)

            return Response("success", status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(exc_type, exc_tb.tb_lineno)
            return Response(data=str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
