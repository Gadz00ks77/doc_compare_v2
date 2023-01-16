import streamlit as st
import pandas as pd
import json as j
import pandas as pd
import os, shutil
import image_generator as ig 
import textbox_extractor_textract as txtex_txt
import build_doc_section_output as dos
import bold_generator as bg
import json as j 
import bold_tagger as bt

st.title('File Selector')
st.header('Select PDF files to compare')

col1,col2 = st.columns(2)

with col1:
    file1 = col1.file_uploader("Select First File:",accept_multiple_files=False,key='filename')

with col2:
    file2 = st.file_uploader("Select Second File:",accept_multiple_files=False)

filename1 = 'None'
filename2 = 'None'

if file1 is not None:
    filename1 = file1.name

if file2 is not None:
    filename2 = file2.name

yes = st.button("Run Import")

col3,col4 = st.columns(2)

if file1 is not None or file2 is not None:
    if yes == True:
        if filename1 != 'None':
            bytes_data = file1.getvalue()
            f = open(f"./working/{filename1}",'wb')
            f.write(bytes_data)
            col3.text(f'Importing {filename1}')     

            # 1. CONVERT IMAGES
            page_count = ig.convert_image_set(filename1)
            col3.text(f'Images Converted')

            # 2. BOLD FINDER
            bg.run_bold_process(file_name=filename1)
            col3.text(f'Bold Process')

            # 3. TEXTRACTOR 
            txtex_txt.collect_textract_all_pages(file_name=filename1)
            txtex_txt.collect_textract_all_pages(file_name=filename1,bold='Yes')
            bt.boldtag_viamerge(file_name=filename1)
            bt.tag_margins_doc_level(file_name=filename1)
            kpis = dos.build_extractor(file_name=filename1)
            col3.text(f'Imported {filename1}')
            items_present = kpis['items']
            items_used = kpis['found']
            items_cleansed = kpis['cleansed_cnt']
            col3.text(f'{items_present} Items Extracted Overall')
            col3.text(f'{items_used} Items Found in a Document Section - ({int((items_used/items_present)*100)}%)')        
            col3.text(f'{items_cleansed} Page Items and Repeated Nonsense Removed.')
            col3.text(f'{items_cleansed+items_used} Overall Successfully Processed Items - ({int(((items_cleansed+items_used)/(items_cleansed+items_present))*100)}%)')        
        
        if filename2 != 'None':
            bytes_data = file2.getvalue()
            f = open(f"./working/{filename2}",'wb')
            f.write(bytes_data)
            col4.text(f'Importing {filename2}')     

            # 1. CONVERT IMAGES
            page_count = ig.convert_image_set(filename2)

            # 3. BOLD FINDER
            bg.run_bold_process(file_name=filename2)

            # 3. TEXTRACTOR 
            txtex_txt.collect_textract_all_pages(file_name=filename2)
            txtex_txt.collect_textract_all_pages(file_name=filename2,bold='Yes')
            bt.boldtag_viamerge(file_name=filename2)
            bt.tag_margins_doc_level(file_name=filename2)
            kpis2 = dos.build_extractor(file_name=filename2)

            col4.text(f'Imported {filename2}')
            items_present2 = kpis2['items']
            items_used2 = kpis2['found']
            items_cleansed2 = kpis2['cleansed_cnt']
            col4.text(f'{items_present2} Items Extracted Overall')
            col4.text(f'{items_used2} Items Found in a Document Section - ({int((items_used2/items_present2)*100)}%)')        
            col4.text(f'{items_cleansed2} Page Items and Repeated Nonsense Removed.')
            col4.text(f'{items_cleansed2+items_used2} Overall Successfully Processed Items - ({int(((items_cleansed2+items_used2)/(items_cleansed2+items_present2))*100)}%)')        

        file_json = {
            "filename1":filename1,
            "filename2":filename2
        }

        with open(f'./selected_files.json', 'w') as f:
            j.dump(file_json, f, ensure_ascii=False)

        st.header('Done')