import streamlit as st
import json as j
import plot_generator as po

def fetch_keys(file_names):

    outkeys = []

    for file in file_names:

        outfilename = file.replace(' ','_').replace('-','_')
        with open(f'./textbox_working_textract/{outfilename}/final_output.json') as f:
            output_set = j.load(f)            

            for key in output_set['results']:
                for keyval in key:
                    if keyval != 'sorter':
                        if keyval not in outkeys:
                            outkeys.append(keyval)

    return outkeys

def fill_range(first_page,last_page):

    i = first_page
    out_range = []

    while i <= last_page:
        out_range.append(i)
        i = i + 1

    return out_range

def fetch_valuejson_for_key(file_name,key_lookup_val):

    outfilename = file_name.replace(' ','_').replace('-','_')

    keyvaloutset = []

    with open(f'./textbox_working_textract/{outfilename}/final_output.json') as f:
        output_set = j.load(f)    

        for key in output_set['results']:
            for keyval in key:
                if keyval==key_lookup_val:
                    
                    # to_paste_values = []
                    for vals in key[keyval]['value_sets']:
                        # to_paste_values.append(vals['original_text'])
                        keyvaloutset.append(vals['text'])

    return j.dumps(keyvaloutset)

def page_num_from_key(lookup_key,file_name):

    outfilename = file_name.replace(' ','_').replace('-','_')
    with open(f'./textbox_working_textract/{outfilename}/final_output.json') as f:
        output_set = j.load(f)          
        for key in output_set['results']:
            for keyval in key:
                
                if keyval == lookup_key:
                    return key[keyval]['key_box_page']
    
    return 1

with open(f'./selected_files.json') as f:
    file_set = j.load(f)          

filename = file_set['filename1'].replace('.pdf','')
filename2 = file_set['filename2'].replace('.pdf','')

if filename =='None' and filename2=='None':
    st.text('Select Files in File Selector')
elif filename == 'None' or filename2 == 'None':
    if filename == 'None':
        filename=filename2

    key_list = fetch_keys([filename])
    key_lookup_val = st.selectbox("Select Document Section:",key_list)
    page_num = page_num_from_key(key_lookup_val,file_name=filename)
    this_keys_json = fetch_valuejson_for_key(file_name=filename,key_lookup_val=key_lookup_val)
    st.header(filename)

    plot_page_range = po.key_plot_pages(
        file_name=filename,specific_key=key_lookup_val
    )

    col1, col2 = st.columns(2)

    with col1:
        col1.text('Page View')
        if plot_page_range['min_page'] != plot_page_range['max_page']:
            num_range = fill_range(plot_page_range['min_page'],plot_page_range['max_page'])            
            selector1 = col1.selectbox("Select Page",num_range,key='yes')
            target_page_num = selector1
            plot_img = po.process_text_detection(file_name=filename,page=target_page_num,key=key_lookup_val)
            col1.image(plot_img)
        else:
            target_page_num = page_num
            plot_img = po.process_text_detection(file_name=filename,page=target_page_num,key=key_lookup_val)
            col1.image(plot_img)

    with col2:
        col2.text('Key Values')
        col2.json(this_keys_json,expanded=False)
else:
    
    key_list = fetch_keys([filename,filename2])
    key_lookup_val = st.selectbox("Select Document Section:",key_list)
    page_num = page_num_from_key(key_lookup_val,file_name=filename)
    page_num2 = page_num_from_key(key_lookup_val,file_name=filename2)
    this_keys_json = fetch_valuejson_for_key(file_name=filename,key_lookup_val=key_lookup_val)
    this_keys_json2 = fetch_valuejson_for_key(file_name=filename2,key_lookup_val=key_lookup_val)

    col1, col2, col3 = st.columns(3)

    with col2:
        col2.header(filename)

        plot_page_range = po.key_plot_pages(
            file_name=filename,specific_key=key_lookup_val
        )

        page_view_expander = st.expander("See Page View")
        page_view_expander.text('Page View')
        if plot_page_range['min_page'] != plot_page_range['max_page']:
            num_range = fill_range(plot_page_range['min_page'],plot_page_range['max_page'])         
            selector1 = col2.selectbox('Select Page',num_range,key='yes')
            target_page_num=selector1
            plot_img = po.process_text_detection(file_name=filename,page=target_page_num,key=key_lookup_val)
        else:
            target_page_num = page_num
            plot_img = po.process_text_detection(file_name=filename,page=target_page_num,key=key_lookup_val)
        
        page_view_expander.image(plot_img)

        st.text('Key Values')
        st.json(this_keys_json,expanded=False)

    with col3:
        col3.header(filename2)

        plot_page_range2 = po.key_plot_pages(
            file_name=filename2,specific_key=key_lookup_val
        )

        page_view_expander2 = st.expander("See Page View")
        page_view_expander2.text('Page View')
        if plot_page_range2['min_page'] != plot_page_range2['max_page']:
            num_range2 = fill_range(plot_page_range2['min_page'],plot_page_range2['max_page'])         
            selector2 = col3.selectbox('Select Page',num_range2,key='no')
            target_page_num2=selector2
            plot_img2 = po.process_text_detection(file_name=filename2,page=target_page_num2,key=key_lookup_val)
        else:
            target_page_num2 = page_num2
            plot_img2 = po.process_text_detection(file_name=filename2,page=target_page_num2,key=key_lookup_val)
        
        page_view_expander2.image(plot_img2)

        st.text('Key Values')
        st.json(this_keys_json2,expanded=False)