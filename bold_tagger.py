import copy
import json as j
import pandas as pd

def get_iou(bb1, bb2):
    """
    Calculate the Intersection over Union (IoU) of two bounding boxes.

    Parameters
    ----------
    bb1 : dict
        Keys: {'x1', 'x2', 'y1', 'y2'}
        The (x1, y1) position is at the top left corner,
        the (x2, y2) position is at the bottom right corner
    bb2 : dict
        Keys: {'x1', 'x2', 'y1', 'y2'}
        The (x, y) position is at the top left corner,
        the (x2, y2) position is at the bottom right corner

    Returns
    -------
    float
        in [0, 1]
    """
    # assert bb1['x1'] < bb1['x2']
    # assert bb1['y1'] < bb1['y2']
    # assert bb2['x1'] < bb2['x2']
    # assert bb2['y1'] < bb2['y2']

    # determine the coordinates of the intersection rectangle
    x_left = max(bb1['x1'], bb2['x1'])
    y_top = max(bb1['y1'], bb2['y1'])
    x_right = min(bb1['x2'], bb2['x2'])
    y_bottom = min(bb1['y2'], bb2['y2'])

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    # The intersection of two axis-aligned bounding boxes is always an
    # axis-aligned bounding box
    intersection_area = (x_right - x_left) * (y_bottom - y_top)

    # compute the area of both AABBs
    bb1_area = (bb1['x2'] - bb1['x1']) * (bb1['y2'] - bb1['y1'])
    bb2_area = (bb2['x2'] - bb2['x1']) * (bb2['y2'] - bb2['y1'])

    # compute the intersection over union by taking the intersection
    # area and dividing it by the sum of prediction + ground-truth
    # areas - the interesection area
    iou = intersection_area / float(bb1_area + bb2_area - intersection_area)
    # assert iou
    # assert iou <= 1.0
    return iou

def boldtag_viamerge(file_name):

    folder = file_name.replace(' ','_').replace('-','_').replace(".pdf","")

    with open(f'./textbox_working_textract/{folder}/output.json', 'rb') as f:
        outputj = j.load(f)

    with open(f'./boldbox_working_textract/{folder}/output.json', 'rb') as f:
        boldoutputj = j.load(f)

    for page in boldoutputj:
        # if page['page_num']==2:
            # print('yeah')
            page_num = page['page_num']
            for block in page['output']['Blocks']:
                if block['BlockType']=='MERGED':

                    candidate_text = block['Text']
                    candidate_geo = block['Geometry']

                    x1 = candidate_geo['Polygon'][0]['X']
                    y1 = candidate_geo['Polygon'][0]['Y']
                    x2 = candidate_geo['Polygon'][1]['X']
                    y2 = candidate_geo['Polygon'][2]['Y']

                    cand_dict = {'x1':x1,'x2':x2,'y1':y1,'y2':y2}

                    same_page_t = list(filter(lambda page: page['page_num'] == page_num, outputj))

                    for tpage in same_page_t:
                        # if tpage['page_num']==2:
                            for tblock in tpage['output']['Blocks']:
                                if tblock['BlockType']=='MERGED':
                                    targ_text = tblock['Text']
                                    targ_geo = tblock['Geometry']

                                    tx1 = targ_geo['Polygon'][0]['X']
                                    ty1 = targ_geo['Polygon'][0]['Y']
                                    tx2 = targ_geo['Polygon'][1]['X']
                                    ty2 = targ_geo['Polygon'][2]['Y']                           

                                    targ_dict = {'x1':tx1,'x2':tx2,'y1':ty1,'y2':ty2}

                                    iou = get_iou(cand_dict,targ_dict)

                                    if iou > 0.3:
                                        tblock['MERGEBOLDMATCH']=1
                                        tblock['MERGEBOLDSTRENGTH']=iou

    with open(f'./textbox_working_textract/{folder}/tagged_output.json', 'w') as f:
        j.dump(outputj, f, ensure_ascii=False)

    return 1

def page_margin_set(file_name):

    # A PAGE MARGIN SET will be useful if we add some definition for page *declaration* (i.e. what's written on the page)
    # For now, we will use doc_margin_set

    folder = file_name.replace(' ','_').replace('-','_').replace(".pdf","")

    with open(f'./textbox_working_textract/{folder}/tagged_output.json', 'rb') as f:
        outputj = j.load(f)

    page_margins = []

    for page in outputj:

        margin_dict = {}
        page_num = page['page_num']
        margin_dict['page_num']=int(page_num)
        for block in page['output']['Blocks']:
            if block['BlockType']=='MERGED':
                leftx = block['Geometry']['BoundingBox']['Left']
                if leftx in margin_dict:
                    margin_dict[leftx] = margin_dict[leftx]+1
                else:
                    margin_dict[leftx] = 1

        page_margins.append(copy.deepcopy(margin_dict))
    
    return page_margins

def doc_margin_set(file_name):

    # Assumption: Frequency for a left margin must be > page count + 5% (or == page count where page count == 1) and < 0.40% of page
    # Assumption: Frequency for centre margins between +/- 10pp of 50%

    folder = file_name.replace(' ','_').replace('-','_').replace(".pdf","")

    with open(f'./textbox_working_textract/{folder}/tagged_output.json', 'rb') as f:
        outputj = j.load(f)

    doc_margins = {}
    page_cnt = 0

    all_lefts = []

    for page in outputj:
        page_cnt = page_cnt + 1
        for block in page['output']['Blocks']:
            if block['BlockType']=='MERGED':
                leftx = block['Geometry']['BoundingBox']['Left']
                all_lefts.append(leftx)
                # if leftx in doc_margins:
                #     doc_margins[leftx] = doc_margins[leftx]+1
                # else:
                #     doc_margins[leftx] = 1
    
    sorted_all_lefts = sorted(all_lefts)

    for left in sorted_all_lefts:
        if left in doc_margins:
            doc_margins[left] = doc_margins[left]+1
        else:
            doc_margins[left] = 1

    margin_set = []
    left_num = 0
    found_lefts = []
    centre_num = 0
    found_centres = []

    for candidate in doc_margins:
        if 0 <= float(candidate) < 0.25:
            if doc_margins[candidate]>(page_cnt+int(page_cnt/20)):
                if candidate not in found_lefts:
                    left_num = left_num + 1
                    margin_set.append({'left_num':left_num,'left_margin':candidate})
                    found_lefts.append(candidate)
        elif 0.45 <= float(candidate) < 0.55:
            if candidate not in found_centres:
                centre_num = centre_num + 1
                found_centres.append(candidate)
                margin_set.append({'centre_num':centre_num,'centre_margin':candidate})
        
    return margin_set

def margset_for_page(page_num,doc_margins,page_margins):

    add_these = []
    page_out_set = []

    for page in page_margins:
        if page['page_num']==page_num:
            for margin in doc_margins:
                if 'left_margin' in margin:
                    if margin['left_margin'] in page:
                        add_these.append(margin['left_margin'])

    sort_add = sorted(add_these)

    num = 0

    for add in sort_add:
        num = num + 1
        page_out_set.append({
            'left_num':num,
            'left_margin':add
        })

    return page_out_set

def tag_margins_doc_level(file_name):

    folder = file_name.replace(' ','_').replace('-','_').replace(".pdf","")

    margin_set = doc_margin_set(file_name=file_name)
    page_margins = page_margin_set(file_name=file_name)

    with open(f'./textbox_working_textract/{folder}/tagged_output.json', 'rb') as f:
        outputj = j.load(f)

        for page in outputj:
            page_num = page['page_num']
            page_set = margset_for_page(page_num=page_num,doc_margins=margin_set,page_margins=page_margins)
            for block in page['output']['Blocks']:
                if block['BlockType']=='MERGED':
                    leftx = block['Geometry']['BoundingBox']['Left']

                    for m in page_set:
                    # for m in margin_set:
                        if 'left_margin' in m: 
                            if m['left_margin']==leftx:
                                block['MARGIN_IDENT']='LEFT'
                                block['MARGIN_NUM_FOR_TYPE']=m['left_num']
                        # (removed centre stuff for now)
                        # elif 'centre_margin' in m:
                        #     if m['centre_margin']==leftx:
                        #         block['MARGIN_IDENT']='CENTRE'
                        #         block['MARGIN_NUM_FOR_TYPE']=m['centre_num']

    with open(f'./textbox_working_textract/{folder}/tagged_margins_output.json', 'w') as f:
        j.dump(outputj, f, ensure_ascii=False)

    return 1



