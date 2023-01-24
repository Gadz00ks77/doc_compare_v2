import boto3
import os
from pathlib import Path
import os,shutil
import json as j
import logging
from botocore.exceptions import ClientError
import copy
import concurrent.futures
import re

logger = logging.getLogger(__name__)


def del_working_files(folder_name):

    folder = folder_name
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except:
            pass

class TextractWrapper:
    """Encapsulates Textract functions."""
    def __init__(self, textract_client, s3_resource=None, sqs_resource=None):
        """
        :param textract_client: A Boto3 Textract client.
        :param s3_resource: A Boto3 Amazon S3 resource.
        :param sqs_resource: A Boto3 Amazon SQS resource.
        """
        self.textract_client = textract_client
        self.s3_resource = s3_resource
        self.sqs_resource = sqs_resource

    def detect_file_text(self, *, document_file_name=None, document_bytes=None):
        """
        Detects text elements in a local image file or from in-memory byte data.
        The image must be in PNG or JPG format.

        :param document_file_name: The name of a document image file.
        :param document_bytes: In-memory byte data of a document image.
        :return: The response from Amazon Textract, including a list of blocks
                 that describe elements detected in the image.
        """
        if document_file_name is not None:
            with open(document_file_name, 'rb') as document_file:
                document_bytes = document_file.read()
        try:
            response = self.textract_client.detect_document_text(
                Document={'Bytes': document_bytes})
            logger.info(
                "Detected %s blocks.", len(response['Blocks']))
        except ClientError:
            logger.exception("Couldn't detect text.")
            raise
        else:
            return response

def build_line_frequency(raw_output):

    # SO, IF A LINE (NOT A WORD) IS PARTICULARLY FREQUENT IT'S **PROBABLY** A HEADER, FOOTER OR OTHER MISC GARBAGE. WE'LL COLLECT THE LINE FREQUENCIES HERE FOR USE LATER.

    line_freq_dict = {}

    for page in raw_output:
        for block in page['output']['Blocks']:
            this_id = block['Id']
            if block['BlockType'] == 'LINE':
                if block['Text'] not in line_freq_dict:
                    line_freq_dict[block['Text']]=1
                else:
                    line_freq_dict[block['Text']]=line_freq_dict[block['Text']]+1

    return line_freq_dict

def tag_line_frequency(raw_output,linefreqdict):

    pagecnt = len(raw_output)

    for page in raw_output:
        for block in page['output']['Blocks']:
            if block['BlockType'] == 'LINE':
                block['LineFrequency']=linefreqdict[block['Text']]
                block['PageCnt']=pagecnt

    return raw_output

def add_to_box_list(current_box_list,candidate_corner,line_text,line_id,line_freq,page_cnt):

    x1 = candidate_corner['x1'] # left
    y1 = candidate_corner['y1'] # top
    x2 = candidate_corner['x2'] # right
    y2 = candidate_corner['y2'] # bottom

    if len(current_box_list)==0:
        current_box_list.append(
            {
                'boxid': 1,
                'line_box_set':
                [{
            'line_text':line_text,
            'line_id':line_id,
            'x1':x1,
            'y1':y1,
            'x2':x2,
            'y2':y2
        }]})
        return current_box_list

    found = 0

    found_set = []

    for box in current_box_list:
        currbox = box['boxid']
        for line_box in box['line_box_set']:
            if 0 <= (x1 - line_box['x1']) <=0.035: # same or similar left start
                if abs(y1 - line_box['y2'])<0.012: # next text line (at "usual" font size)
                    if line_freq < (page_cnt/3.5): # if a line is particularly frequent, leave it on it's own.
                        found_set.append(box)
                        found_box = box
                        found = 1
            
    if found == 1:
        found_box['line_box_set'].append({
        'line_text':line_text,
        'line_id':line_id,
        'x1':x1,
        'y1':y1,
        'x2':x2,
        'y2':y2
            })
        return current_box_list
     
    current_box_list.append(
            {
                'boxid': currbox + 1,
                'line_box_set':
                [{
            'line_text':line_text,
            'line_id':line_id,
            'x1':x1,
            'y1':y1,
            'x2':x2,
            'y2':y2
        }]})    
    return current_box_list

def likely_page_number(text):

    page_regex = [
        'Page\s[0-9]+',
        'Page\s[0-9]+\sof',
        'PAGE\s[0-9]+\sOF',
        '.+Page\s[0-9]+$',
    ]

    found = 0

    for r in page_regex:
        m = re.match(r,text)
        if m is not None:
            found = 1

    return found

def in_it(alist,afield,avalue):

    for item in alist:
        if avalue == item[afield]:
            return 1
        
    return 0

def has_multi_at_y(text_multis_list,candidate_text,y_top):

    if likely_page_number(candidate_text)==1:
        text_to_check = 'ZZ_ PAGE SET'
    else:
        text_to_check = candidate_text

    top_to_check = round(y_top,2)

    for t in text_multis_list:
        if t['name']==text_to_check:
            for c in t['matched_geos']:
                this_len = len(c['set'])
                for s in c['set']:
                    check_against_top = round(s['Top'],2)
                    check_against_bottom = round(s['Height'],2) + round(s['Top'],2)
                    if top_to_check >= check_against_top and top_to_check <= check_against_bottom and this_len > 1:
                        return 1

    return 0

def remove_guff(file_path):

    # DO NOT USE ON BOLD FILES

    with open(f'{file_path}/raw_output.json', 'rb') as f:
        out_raw = j.load(f)   

    all_text = []

    page_cnt = 0

    for page in out_raw:
        page_cnt = page_cnt + 1
        for block in page['output']['Blocks']:
            if block['BlockType']=='LINE':
                if likely_page_number(text=block['Text'])==1:
                    all_text.append({
                        'text':'ZZ_ PAGE SET',
                            'geo':block['Geometry']['BoundingBox']
                    })
                else:
                    all_text.append({
                        'text':block['Text'],
                            'geo':block['Geometry']['BoundingBox']
                    })

    all_text_of_same_type = []

    for t in all_text:
        this_text = t['text']
        this_geo = t['geo']
        if in_it(all_text_of_same_type,'name',this_text)==0:
            all_text_of_same_type.append({
                'name':this_text,
                'geo_set':[this_geo]
            })
        else:
            for st in all_text_of_same_type:
                if st['name']==this_text:
                    st['geo_set'].append(this_geo)

    max_id = 0

    for c in all_text_of_same_type:
        for g in c['geo_set']:
            found_match = 0
            if 'matched_geos' not in c:
                max_id += 1
                c['matched_geos']=[{
                    'id':max_id,
                    'set':[g]
                }]
                found_match = 1
            else:
                for m in c['matched_geos']:
                    this_id = m['id']
                    to_check_top = round(g['Top'],2)
                    for s in m['set']:
                        against_top = round(s['Top'],2)
                        against_bottom = round(s['Top']+s['Height'],2)
                        if to_check_top >= against_top and to_check_top <= against_bottom: # and len(m['set'])>=3:  # this literal should be modified for page counts
                            found_match = 1
                            m['set'].append(g)
                            break
                                    
                if found_match == 0:
                    max_id += 1
                    c['matched_geos'].append(
                        {
                            'id':max_id,
                            'set':[g]
                        }
                    )
                
    lose_it = []
    final = []

    for page in out_raw:
        page_num = page['page_num']
        keep_these_blocks = [] 
        for block in page['output']['Blocks']:
            if block['BlockType']=='LINE':
                if block['Confidence']>50:
                    if has_multi_at_y(all_text_of_same_type, block['Text'],block['Geometry']['BoundingBox']['Top'])==0:
                        keep_these_blocks.append(block)
                    else:
                        block['reason']='good confidence, but multi ys'
                        lose_it.append(block)    
                    
                elif has_multi_at_y(all_text_of_same_type, block['Text'],block['Geometry']['BoundingBox']['Top'])==0:
                    keep_these_blocks.append(block)
                else:
                    block['reason']='no confidence'
                    lose_it.append(block)

        page['Blocks'] = copy.deepcopy(keep_these_blocks)

        final.append({'page_num':page_num,'output':{'Blocks':keep_these_blocks}})

    with open(f'{file_path}/cleansed_output.json', 'w') as f:
        j.dump(final, f, ensure_ascii=False)

    with open(f'{file_path}/multiy_output.json', 'w') as f:
        j.dump(all_text_of_same_type, f, ensure_ascii=False)
    
    with open(f'{file_path}/cleansed_output_removed.json', 'w') as f:
        j.dump(lose_it, f, ensure_ascii=False)

    return 1

def get_likely_headers_n_footers(raw_output):

    tops = {}

    for page in raw_output:
        box_list = []
        for block in page['output']['Blocks']:
            this_id = block['Id']
            if block['BlockType'] == 'LINE':
                this_top = str(round(block['Geometry']['BoundingBox']['Top'],2))
                this_text = block['Text']
                is_page = likely_page_number(text=this_text)
                if is_page == 1:
                    print('yes')

                if this_top not in tops:
                    tops[this_top]={}
                    tops[this_top][this_text]=1
                    if is_page == 1:
                        if 'is_page' in tops[this_top]:
                            tops[this_top]['is_page']=tops[this_top]['is_page']+1
                        else:
                            tops[this_top]['is_page']=1
                else:
                    if this_text not in tops[this_top]:
                        tops[this_top][this_text]=1
                        if is_page == 1:
                            if 'is_page' in tops[this_top]:
                                tops[this_top]['is_page']=tops[this_top]['is_page']+1
                            else:
                                tops[this_top]['is_page']=1
                    else:
                        tops[this_top][this_text]=tops[this_top][this_text]+1 
                        if is_page == 1:
                            tops[this_top]['is_page']=tops[this_top]['is_page']+1         

    sorted_keys = sorted(tops)

    sorted_output = {}
    repeat_cnt = 0

    for item in sorted_keys:
        sorted_output[item] = tops[item]
    
    for pos in sorted_output:
        found_multi = 0
        for text in sorted_output[pos]:
            if sorted_output[pos][text]>1:
                repeat_cnt = 0
                found_multi = 1

        if found_multi ==0:
            repeat_cnt = repeat_cnt + 1
            if repeat_cnt == 2:
                break
            else:
                header_y_p = float(pos)

    rsorted_keys = sorted(tops,reverse=True)

    rsorted_output = {}
    repeat_cnt = 0

    for item in rsorted_keys:
        rsorted_output[item] = tops[item]

    for pos in rsorted_output:
        found_multi = 0
        found_many = 0
        for text in rsorted_output[pos]:
            if rsorted_output[pos][text]>1:
                found_multi = 1
                repeat_cnt = 0
            if len(str(rsorted_output[pos][text]).split())>=3 and rsorted_output[pos][text]==1:
                found_many = found_many + 1

        if found_many > 1:    
            found_multi = 0
            repeat_cnt = 0 

        if found_multi ==0:
            repeat_cnt = repeat_cnt + 1
            if repeat_cnt == 2:
                break
            else:
                footer_y_p = float(pos)
            
    return {
        'min_y':header_y_p,
        'max_y':footer_y_p
        }

def gen_merged_box(raw_output,bold=None):

    # # CLEANSE HEADER AND FOOTER RECORDS

    # if bold is None:

    #     fetch_hfs = get_likely_headers_n_footers(
    #         raw_output=raw_output
    #     )

    #     for page in raw_output:
    #         new_block_arr = []
    #         for block in page['output']['Blocks']:
    #             # if 'Text' in block:
    #             #     if block['Text']=='PAGE 2 OF 12':
    #             #         print('yes')
    #             top_chk = round(block['Geometry']['BoundingBox']['Top'],2)
    #             if top_chk < fetch_hfs['min_y'] or top_chk > fetch_hfs['max_y'] :
    #                 continue
    #             else:
    #                 new_block_arr.append(block)

    #         page['output']['Blocks']=copy.deepcopy(new_block_arr)            

    outputj = copy.deepcopy(raw_output)

    this_line_frequency = build_line_frequency(raw_output=outputj)
    modified_output = tag_line_frequency(raw_output=outputj,linefreqdict=this_line_frequency)

    for page in modified_output:
        box_list = []
        for block in page['output']['Blocks']:
            this_id = block['Id']
            
            if block['BlockType'] == 'LINE':

                leftx = 100
                topy = 0
                bottomy = 100
                rightx = 0

                for p in block['Geometry']['Polygon']:
                    if p['X'] <= leftx:
                        leftx = p['X']
                    if p['Y'] <= bottomy:
                        bottomy = p['Y']
                    if p['Y'] >= topy:
                        topy = p['Y']
                    if p['X'] >= rightx:
                        rightx = p['X']
            
                # FIX THIS SHIT
                nottopy = bottomy
                bottomy = topy
                topy = nottopy
                
                box_list = add_to_box_list(current_box_list=box_list,candidate_corner={'x1':round(leftx,2),'x2':round(rightx,2),'y1':round(topy,3),'y2':round(bottomy,3)},line_text=block['Text'],line_id=this_id,line_freq=block['LineFrequency'],page_cnt=block['PageCnt'])

        output_list = []

        for out_box in box_list:

            this_text = ''
            x1 = 0
            x2 = 0
            y1 = 100
            y2 = 0

            line_relationships = []

            for line_box in out_box['line_box_set']:
                line_relationships.append(line_box['line_id']) 
                this_text = this_text + ' ' + line_box['line_text']
                if line_box['x1']>x1:
                    x1 = line_box['x1']
                if line_box['y1']<y1:
                    y1 = line_box['y1']
                if line_box['x2']>x2:
                    x2 = line_box['x2']
                if line_box['y2']>y2:
                    y2 = line_box['y2']

            output_list.append({
                'BlockType': "MERGED",
                'Confidence': "Not a lot",
                'TextType':'LINE CONCAT',
                'Text': this_text[1:],
                'Geometry':{
                    'BoundingBox':{
                        'Width': x2+x1,
                        'Height': y2-y1,
                        'Left': x1,
                        'Top': y1
                    },
                    'Polygon':[
                        {
                            "X": x1,
                            "Y": y1
                        },
                        {
                            "X": x2,
                            "Y": y1
                        },
                        {
                            "X": x2,
                            "Y": y2
                        },
                        {
                            "X": x1,
                            "Y": y2
                        }
                    ]
                },
                'Id': out_box['boxid'],
                'Relationships': [
                        {
                            'Type': "CHILD",
                            'Ids': line_relationships
                        }
                    ]
            })

        for item in output_list:
            page['output']['Blocks'].append(copy.deepcopy(item))

    return modified_output

def fetch_textract(file_path,txtclient):

    TextClass = TextractWrapper(textract_client=txtclient)
    text_output = TextClass.detect_file_text(document_file_name=file_path)

    name_file = file_path[file_path.rfind('/'):]
    name_only = name_file.replace('.png','')
    page_num = int(name_only[name_only.find('-')+1:])

    page_set = {'page_num':page_num}
    # text_output = TextClass.detect_file_text(document_file_name=file_path)
    page_set['output']=text_output

    return page_set

def gen_file_paths(imgfolder):

    paths = []

    for file_name in os.listdir(imgfolder):
        file_path = os.path.join(imgfolder,file_name)
        paths.append(file_path)

    return paths

def collect_textract_all_pages(file_name,bold=None):

    tclient = boto3.client('textract')

    if bold is None:
        img_folder = './pdf_images/'+file_name.replace(' ','_').replace('-','_').replace(".pdf","")
        textbox_folder = './textbox_working_textract/'+file_name.replace(' ','_').replace('-','_').replace(".pdf","")
        Path(textbox_folder).mkdir(parents=True, exist_ok=True)
        del_working_files(textbox_folder)
    else:
        img_folder = './bold_images/'+file_name.replace(' ','_').replace('-','_').replace(".pdf","")
        textbox_folder = './boldbox_working_textract/'+file_name.replace(' ','_').replace('-','_').replace(".pdf","")
        Path(textbox_folder).mkdir(parents=True, exist_ok=True)
        del_working_files(textbox_folder)        

    result_set = []

    file_path_set = gen_file_paths(imgfolder=img_folder)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(fetch_textract,fpath,tclient): fpath for fpath in file_path_set}
        for future in concurrent.futures.as_completed(future_to_url):
            fpath = future_to_url[future]
            data = future.result()
            result_set.append(copy.deepcopy(data))

    sorted_result = result_set

    with open(f'{textbox_folder}/raw_output.json', 'w') as f:
        j.dump(sorted_result, f, ensure_ascii=False)

    remove_guff(f'{textbox_folder}')

    with open(f'{textbox_folder}/cleansed_output.json', 'rb') as f:
        cleansed_result = j.load(f)

    merged_output = gen_merged_box(raw_output=cleansed_result,bold=bold)

    with open(f'{textbox_folder}/output.json', 'w') as f:
        j.dump(merged_output, f, ensure_ascii=False)

    return sorted_result