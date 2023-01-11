import json as j
from PIL import Image, ImageDraw

def key_plot_pages(file_name,specific_key):

    outfilename = file_name.replace(' ','_').replace('-','_')

    min_page = 0
    max_page = 0

    with open(f'./textbox_working_textract/{outfilename}/final_output.json') as f:
        output_set = j.load(f)     

    for key in output_set['results']:
        for keyval in key:
            if keyval == specific_key:
                for val_set in key[keyval]['value_sets']:
                    if min_page == 0:
                        min_page = val_set['text_box_location']['page']
                    elif val_set['text_box_location']['page'] <= min_page:
                        min_page = val_set['text_box_location']['page']
                    
                    if max_page == 0:
                        max_page = val_set['text_box_location']['page']
                    elif val_set['text_box_location']['page'] >= max_page:
                        max_page = val_set['text_box_location']['page']

    return {
        "min_page":min_page,
        "max_page":max_page
    }

def fetch_key_data(file_name,key_name,pagenum):

    outfilename = file_name.replace(' ','_').replace('-','_')

    with open(f'./textbox_working_textract/{outfilename}/final_output.json') as f:
        output_set = j.load(f)     

    for key in output_set['results']:
        for keyval in key:
            if keyval == key_name:
                    lowest_valx1 = 0
                    greatest_valx2 = 0
                    lowest_valy1 = 0
                    greatest_valy2 = 0

                    for val_set in key[keyval]['value_sets']:
                       
                        if str(val_set['text_box_location']['page']) == str(pagenum):
                            if val_set['text_box_location']['box']['x1']<lowest_valx1 or lowest_valx1 ==0:
                                lowest_valx1 = val_set['text_box_location']['box']['x1']
                            if val_set['text_box_location']['box']['x2']>greatest_valx2:
                                greatest_valx2 = val_set['text_box_location']['box']['x2']
                            if val_set['text_box_location']['box']['y1']<lowest_valy1 or lowest_valy1 ==0:
                                lowest_valy1 = val_set['text_box_location']['box']['y1']
                            if val_set['text_box_location']['box']['y2']>greatest_valy2:
                                greatest_valy2 = val_set['text_box_location']['box']['y2']
                            
    return_pol = [
        {
            'X':lowest_valx1,
            'Y':lowest_valy1
        },
        {
            'X':greatest_valx2,
            'Y':lowest_valy1
        },
        {
            'X':greatest_valx2,
            'Y':greatest_valy2
        },
        {
            'X':lowest_valx1,
            'Y':greatest_valy2
        }
    ]

    return return_pol

def process_text_detection(file_name,page,key):

    filename = file_name.replace(' ','_').replace('-','_').replace(".pdf","")
    file_path = f'./pdf_images/{filename}/image-{page}.png'

    with open(file_path,'rb') as f:

        image=Image.open(f)

        #Get the text blocks
        polyset=fetch_key_data(file_name=filename,key_name=key,pagenum=page)
        width, height =image.size    
        
        draw=ImageDraw.Draw(image)
        points=[]

        for polygon in polyset:
            points.append((width * polygon['X'], height * polygon['Y']))

        draw.polygon((points), outline='red',width=5)    

    return image

# process_text_detection(filename='westjet_2020_2021',page='2',key='UNIQUE MARKET REFERENCE:')