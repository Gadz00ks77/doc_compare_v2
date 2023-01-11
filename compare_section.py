import spacy as sp
import en_core_web_md as md
import json as j

def return_value_set(this_output_set,this_key):

    for key_set in this_output_set['results']:
        for key in key_set: 
            if key == this_key:
                return key_set

    return None 

def concat_value_set(this_value_set,mykey):

    out_str = ''

    for set in this_value_set[mykey]['value_sets']:
        out_str = out_str + ' ' + set['text']

    return out_str

def return_candidate(filename,key):

    outfilename = filename.replace(' ','_').replace('-','_').replace(".pdf","")

    with open(f'./textbox_working_textract/{outfilename}/final_output.json') as f:
        output_set = j.load(f)

        val_set = return_value_set(this_output_set=output_set,this_key=key)

        compare_candidate = concat_value_set(this_value_set=val_set,mykey=key)

    return compare_candidate

def compare_it(compare_first,compare_second):
    
    nlp = sp.load("en_core_web_md")

    doc1 = nlp(compare_first)
    doc2 = nlp(compare_second)

    return doc1.similarity(doc2)


