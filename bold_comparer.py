
import json as j

def get_bold_box_page(bold_box_set,page_num):

    bold_box_page_set = []

    for box in bold_box_set:
        if box['text_page']==page_num:
            bold_box_page_set.append(box)

    return bold_box_page_set

def give_page_margins(margins_set,page_num):

    for page in margins_set:
        if page == 'page' + str(page_num):
            margins = margins_set[page]

    return margins

with open(f'./output.json', 'rb') as f:
    output_dict = j.load(f)


found_boxes = output_dict['text_box_set']['boxes']
found_box_margins = output_dict['text_box_set']['margins']

bold_boxes = output_dict['bold_box_set']

last_page = 0
curr_margins = {}

for box in found_boxes:
    current_page = box['text_page']

    if current_page != last_page:
        bold_boxes_on_page = get_bold_box_page(bold_box_set=bold_boxes,page_num=current_page)
        last_page = current_page
        curr_margins = give_page_margins(margins_set=found_box_margins,page_num=current_page)
    
    this_box_left_x = box['box']['x1']
    page_margin = curr_margins['left_x']
    
    if abs(this_box_left_x-page_margin)<=5:
        left_margin = 'yes'
    else:
        left_margin = 'no'

    bold_text_candidate = str(box['text']).replace('\n','').replace('\r','')

    for bold_box in bold_boxes_on_page:
        # print(bold_box['text'])
        # print(bold_text_candidate.find(bold_box['text'])==0)

        if len(bold_box['text'])>0:
            if bold_text_candidate==bold_box['text'] and left_margin == 'yes':
                box['section_candidate']='left margin bold found'
                box['section_found_via']=bold_box['text']
            elif bold_text_candidate==bold_box['text'] and left_margin == 'no':
                box['section_candidate']='bold found'
                box['section_found_via']=bold_box['text']
            elif bold_text_candidate.find(bold_box['text'])==0 and left_margin == 'yes':
                box['section_candidate']='left margin part bold found'
                box['section_found_via']=bold_box['text']

# print('#################################################################')
# print(j.dumps(found_boxes))


keys = []

for box in found_boxes:
    key_candidate = str(box['text']).replace('\n','').replace('\r','')
    if key_candidate not in keys and 'section_candidate' in box:
        if box['section_candidate'] in ['left margin bold found','left margin part bold found']:
            keys.append(key_candidate)

print(j.dumps(keys))