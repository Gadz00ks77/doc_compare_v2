import boto3
import os
from pathlib import Path
import os,shutil
import json as j
import logging
from botocore.exceptions import ClientError
import copy
import concurrent.futures

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
                if abs(y1 - line_box['y2'])<0.015: # next text line (at "usual" font size)
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

def gen_merged_box(raw_output):

    outputj = raw_output

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

    merged_output = gen_merged_box(raw_output=sorted_result)

    with open(f'{textbox_folder}/output.json', 'w') as f:
        j.dump(merged_output, f, ensure_ascii=False)

    return sorted_result

# collect_textract_all_pages('westjet 2020-2021.pdf')