import json as j
import re 
import math as m

def round_up(n, decimals=0):
    multiplier = 10 ** decimals
    return m.ceil(n * multiplier) / multiplier

def stringclean(input):

    try:
        output = " ".join(input.split())
        output = output.replace("\u2013","-")

    except:
        print('WHHOOOOPS')
        print(input)

    return output

def get_matches(item_list,input_dict,key,on_page):

    inputytop = input_dict['y2']
    inputybottom = input_dict['y1']

    for item in item_list:
        # compareytop = item['box']['y2']
        # compareybottom = item['box']['y1']

        compareybottom = item['box']['y2']
        compareytop = item['box']['y1']

        if stringclean(item['text'])!= key:
            if item['text_page']==on_page:

                # THIS WASN'T RIGHT. ADJUSTED.
                rcyt = int(round_up(compareytop,2)*1000)
                riyt = int(round_up(inputytop,2)*1000)
                riyb = int(round_up(inputybottom,2)*1000)

                #only really need to check whether the top of the candidate starts within the range of the height of the key
                #sadly we have to feather this a little because... well... people can't format Word documents to save their lives. (-10 below)

                if rcyt-10 <= riyt and rcyt >= riyb:
                # if inputytop >= compareybottom and inputybottom <= compareytop: 
                    item['used']=1
                    return item

    return None

def is_likely_key(item_value,found_keys):

    if item_value == '':
        return 0
    elif item_value in found_keys:
        return 1
    else:
        for key in found_keys:
            if key.find(item_value)==0:
                return 1
    
    return 0

def exact_matcher(key_candidate,item_list,output_set,found_these_keys):

    found = 0

    for item in item_list:
        potential_key = stringclean(item['text'])
        if potential_key == key_candidate:
            text_box_dict = item['box']
            on_page = item['text_page']
            found =  get_matches(item_list=item_list,input_dict=text_box_dict,key=key_candidate,on_page=on_page)
            if found is not None:
                found_these_keys.append(key_candidate)
                output_set.append(
                    {
                        key_candidate:{
                            'value_sets':[{
                                'text':stringclean(found['text']),
                                'original_text': found['text'],
                                'text_box_location':{
                                    'page': on_page,
                                    'box':found['box']
                                }
                            }],
                            'key_box_location': text_box_dict,
                            'key_box_page':on_page,
                            'found_via': key_candidate,
                            'found_clauses':[],
                            'find_method':'key_val_box'
                        },
                        'sorter': item['sorter'] 
                    }
                )
                item['used']=1
                found = 1

    if found == 1:
        return {
            'found':1,
            'new_item_list': item_list,
            'output_set': output_set,
            'found_keys': found_these_keys
        }
    else:
        return {
            'found':0
        }

def fetch_candidate_keys(file_name):

    folder = file_name.replace(' ','_').replace('-','_').replace(".pdf","")

    with open(f'./textbox_working_textract/{folder}/tagged_margins_output.json', 'rb') as f:
        outputj = j.load(f)

    key_set = []
    found_keys = []

    page_cnt = 0

    for page in outputj:
        page_cnt = page_cnt + 1
        for block in page['output']['Blocks']:
            if block['BlockType']=='MERGED':
                if 'MARGIN_IDENT' in block and 'MERGEBOLDMATCH' in block:
                    if block['MARGIN_NUM_FOR_TYPE']==1: # Gets perhaps too specific here...
                        # CHECK IF KEY WAS FOUND BEFORE
                        if block['Text'] not in found_keys:
                            key_set.append({'key_name':block['Text'],'key_length':len(block['Text']),'key_cnt':1})
                            found_keys.append(block['Text'])
                        else:
                            for akey in key_set:
                                if akey['key_name']==block['Text']:
                                    akey['key_cnt']=akey['key_cnt']+1

    final_set = []

    for akey in key_set:
        # ONLY ADD KEYS THAT DON'T CONSISTENTLY REPEAT. (THESE ARE LIKELY PAGE HEADERS AND OTHER DOCUMENT GUFF)
        if akey['key_cnt']<= page_cnt/2:
            final_set.append(akey)

    with open(f'./textbox_working_textract/{folder}/keys_output.json', 'w') as f:
        j.dump(final_set,f,ensure_ascii=True)

    return sorted(final_set, key=lambda d: d['key_length'],reverse=True)    

def gen_item_list_output(file_name):

    folder = file_name.replace(' ','_').replace('-','_').replace(".pdf","")

    with open(f'./textbox_working_textract/{folder}/tagged_margins_output.json', 'rb') as f:
        outputj = j.load(f)

    item_list = []

    for page in outputj:
        page_num = page['page_num']
        for block in page['output']['Blocks']:
            if block['BlockType']=='MERGED':

                    candidate_text = block['Text']
                    candidate_geo = block['Geometry']

                    x1 = candidate_geo['Polygon'][0]['X']
                    y1 = candidate_geo['Polygon'][0]['Y']
                    x2 = candidate_geo['Polygon'][1]['X']
                    y2 = candidate_geo['Polygon'][2]['Y']

                    item_list.append({
                        'text': candidate_text,
                        'text_page': int(page_num),
                        'box': {
                            'x1': x1,
                            'y1': y1,
                            'x2': x2,
                            'y2': y2
                        },
                        'sorter': int(page_num)+y2/100
                    })

    item_list = sorted(item_list, key=lambda d: d['sorter'])    

    return item_list

def repeater_set(item_list):

    items = []
    item_cnt_set = {}

    for item in item_list:
        if item['text'] in items:
            item_cnt_set[item['text']]=item_cnt_set[item['text']]+1
        else:
            items.append(item['text'])
            item_cnt_set[item['text']]=1 

    return item_cnt_set

def pages_get(item_list):

    max_page = 0

    for item in item_list:
        if item['text_page']>= max_page:
            max_page = item['text_page']

    return max_page

def declare_page_number_keypairs(item_list):

    page_regex = [
        'Page\s[0-9]+',
        'Page\s[0-9]+\sof',
        'PAGE\s[0-9]+\sOF',
        '.+Page\s[0-9]+$',
    ]

    pageset_found = []

    for item in item_list:
        found = 0
        for r in page_regex:
            m = re.match(r,item['text'])
            if m is not None:
                found = 1
        
        if found  == 1:
            if item['text'] not in pageset_found:
                pageset_found.append(item['text'])
    
    return pageset_found

def get_next_boxes_for_key(key,value_set,key_box_location,key_page,search_item_list,found_keys,find_method=None):

    # GET START  

    i = 0

    return_list = []

    for item in search_item_list:
        if item['box'] == key_box_location and item['text_page']==key_page:
            start_from_item_list = search_item_list[i+1:]            
            break
        else:
            i = i + 1

    last_item_y = None
    last_page = None

    keyx1 = key_box_location['x1']
    keyx2 = key_box_location['x2']
    keyy1 = key_box_location['y1']
    keyy2 = key_box_location['y2']


    if find_method == 'pafb':
        page_mod = 2300 # THIS IS NOT USED EVER IN THIS VERSION
    else:
        page_mod = 1

    large_gap = 0.3
    feather_amt = 0.01

    for item in start_from_item_list:

        this_item_y1 = item['box']['y1']
        this_item_y2 = item['box']['y2']
        this_item_page = item['text_page']
        this_item_x1 =  item['box']['x1']
        this_item_value = stringclean(item['text'])

        if last_item_y is not None:
            if abs(last_item_y-this_item_y1) >= large_gap and last_page == item['text_page']:
                # NOTHING FOR A WHILE; LARGE GAPS WILL BREAK THE LOOP
                last_item_y = None
                last_page = None
                # print ('break on gap:NOTHING FOR A WHILE')
                break

            elif abs(page_mod - last_item_y - this_item_y1) >= large_gap and last_page != item['text_page']:
                # print('yeah')
                last_item_y = None
                last_page = None
                break

            elif (m.ceil(keyx1) - m.ceil(this_item_x1))<=feather_amt and is_likely_key(this_item_value,found_keys=found_keys)==1:
                # SAME STARTING POINT AS MY KEY = NEW KEY; BREAK THE LOOP
                last_item_y = None
                last_page = None
                # print ('break on gap:IS KEY')
                break

            elif 'used' in item:
                # NEVER USE A USED ALREADY - BUT CARRY ON.
                last_item_y = this_item_y2
                last_page = this_item_page
                pass

            elif this_item_page == key_page and this_item_x1 > (keyx2 - feather_amt) and this_item_y1 <= keyy1:
                # SAME PAGE, IDENTED FURTHER THAN END OF KEY BOX (SOME FEATHERING HERE) AND LOWER THAN KEYBOX
                item['used']=1
                return_list.append(item)
                last_item_y = this_item_y2
                last_page = this_item_page

            elif this_item_page > key_page and this_item_x1 > (keyx2 - feather_amt) :
                # NEXT PAGE, IDENTED FURTHER THAN END OF KEY BOX (SOME FEATHERING HERE)
                item['used']=1
                return_list.append(item)
                last_item_y = this_item_y2
                last_page = this_item_page

            else:
                item['used']=1
                last_item_y = this_item_y2
                last_page = this_item_page
                # print('break on; NOTHING TO DO')
                return_list.append(item)

        else:

            if   (m.ceil(keyx1) - m.ceil(this_item_x1))<=feather_amt and is_likely_key(this_item_value,found_keys=found_keys)==1:
                # SAME STARTING POINT AS MY KEY = NEW KEY; BREAK THE LOOP
                last_item_y = None
                last_page = None
                # print ('break on gap:KEY FOUND')
                break

            elif 'used' in item:
                last_item_y = this_item_y2
                last_page = this_item_page
                pass

            elif this_item_page == key_page and this_item_x1 > (keyx2 - feather_amt) and this_item_y1 <= keyy1:
                # SAME PAGE, IDENTED FURTHER THAN END OF KEY BOX (SOME FEATHERING HERE) AND LOWER THAN KEYBOX                
                item['used']=1
                return_list.append(item)
                last_item_y = this_item_y2
                last_page = this_item_page

            elif this_item_page > key_page and this_item_x1 > (keyx2 - feather_amt) :
                # NEXT PAGE, IDENTED FURTHER THAN END OF KEY BOX (SOME FEATHERING HERE)
                item['used']=1
                return_list.append(item)
                last_item_y = this_item_y2
                last_page = this_item_page

            else:
                item['used']=1
                last_item_y = this_item_y2
                last_page = this_item_page
                # print('break on; NOTHING TO DO')
                return_list.append(item)

    return return_list

def build_extractor(file_name):

    folder = file_name.replace(' ','_').replace('-','_').replace(".pdf","")

    find_method = 'n/a'
    keys = fetch_candidate_keys(file_name=file_name)
    item_list = gen_item_list_output(file_name=file_name)
    found_keys = []
    kvset = []

    for candidate_key_set in keys:

        key_candidate = candidate_key_set['key_name']

        found_candidate_key = 0
        exact_outcome = exact_matcher(key_candidate=key_candidate,item_list=item_list,output_set=kvset,found_these_keys=found_keys)
        found_it = exact_outcome['found']

        if found_it==1:
            kvset=exact_outcome['output_set']
            item_list=exact_outcome['new_item_list']
            found_keys=exact_outcome['found_keys']
        
    sorted_kvset = sorted(kvset, key=lambda d: d['sorter']) 

    with open(f'./textbox_working_textract/{folder}/initial_kv_match.json','w') as f:
        j.dump(sorted_kvset,f,ensure_ascii=False)

    # CLEANSE FOR REPEATED PAGE BREAKS ETC ETC - GARBAGE
    item_repeat_cnt = repeater_set(item_list)

    max_pages = pages_get(item_list)

    cleansed_item_list = []
    cleansed_cnt = 0

    for item in item_list:
        if 'used' in item:
            cleansed_item_list.append(item)
        elif max_pages >= 5 and item_repeat_cnt[item['text']]<= int(max_pages / 3.1): # IF AN ITEM IS ON APPROX 30% OF THE PAGES OR MORE - IT'S PROBABLY GUFF (IF THE DOC IS OVER 5 PAGES LONG)
            cleansed_item_list.append(item)
        elif max_pages <5:
            cleansed_item_list.append(item)
        else:
            cleansed_cnt = cleansed_cnt + 1


    # CLEANSE FOR PAGE NUMBERS

    page_number_set = declare_page_number_keypairs(item_list)
    cleansed_cnt = cleansed_cnt + len(page_number_set)

    cleansed_of_pages_item_list = []

    for item in cleansed_item_list:
        found = 0
        if 'used' in 'item':
            cleansed_of_pages_item_list.append(item)
        else:
            for page_candidate in page_number_set:
                if item['text']==page_candidate:
                    found = 1

        if found != 1:
            cleansed_of_pages_item_list.append(item)

        # # COLLECT KV PARAGRAPHS
    for key in sorted_kvset:
        for keyval in key:
            if keyval != 'sorter':
                valset = key[keyval]['value_sets']
                key_box_location = key[keyval]['key_box_location']
                key_box_page = key[keyval]['key_box_page']
                found_via_key = key[keyval]['found_via']
                
                next_values = get_next_boxes_for_key(
                    key=keyval,
                    value_set=valset,
                    key_box_location=key_box_location,
                    key_page=key_box_page,
                    search_item_list=cleansed_of_pages_item_list,
                    found_keys=found_keys,
                    find_method=find_method)
                
                for value in next_values:
                    key[keyval]['value_sets'].append({
                                        'text':stringclean(value['text']),
                                        'original_text': value['text'],
                                        'text_box_location':{
                                            'page': value['text_page'],
                                            'box':value['box']
                                        }     }       )

    sorted_kvset = sorted(kvset, key=lambda d: d['sorter']) 

    root_object = {
        'output_file_name': f'./textbox_working_textract/{folder}/final_output.json',
        'find_method': find_method,
        'source_file_path': f"./working/{file_name}",
        'page_sizes': [],
        'results':[]
    }

    root_object['results']=sorted_kvset

    with open(f'./textbox_working_textract/{folder}/final_output.json', 'w') as f:
        j.dump(root_object, f, ensure_ascii=False)

    item_cnt = 0
    used_cnt = 0
    for clean in cleansed_item_list:
        item_cnt = item_cnt + 1
        if 'used' in clean:
            used_cnt = used_cnt + 1

    return {
        'items': item_cnt,
        'found': used_cnt,
        'cleansed_cnt': cleansed_cnt
    }
