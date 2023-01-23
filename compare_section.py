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

def diff_word_json(doc_json1,doc_json2):

    # A weak little word differ. Not sentence comparison, but word content.

    output = {}
    
    document_1_text = ' \n'.join(str(y) for y in j.loads(doc_json1))
    document_2_text = ' \n'.join(str(y2) for y2 in j.loads(doc_json2))

    document_1_words = document_1_text.split()
    document_2_words = document_2_text.split()

    common = set(document_1_words).intersection( set(document_2_words) )

    out1 = document_1_text
    out2 = document_2_text

    not_in = []
    not_in_2 = []

    for d1word in document_1_words:
        if d1word not in common:
            not_in.append(d1word)

    for d2word in document_2_words:
        if d2word not in common:
            not_in_2.append(d2word)

    if ' ' not in out1:
        for not_word in not_in:
            out1 = out1.replace(''+not_word+'','**:red['+ not_word + ']**')
    else:
        for not_word in not_in:
            out1 = out1.replace(' '+not_word+' ',' **:red['+ not_word + ']** ')
            out1 = out1.replace('\n'+not_word+' ','\n**:red['+ not_word + ']** ')


    if ' ' not in out2:
        for not_word in not_in_2:
            out2 = out2.replace(''+not_word+'','**:red['+ not_word + ']**')
    else:
        for not_word in not_in_2:
            out2 = out2.replace(' '+not_word+' ',' **:red['+ not_word + ']** ')
            out2 = out2.replace('\n'+not_word+' ','\n**:red['+ not_word + ']** ')

    output['doc1']=out1
    output['doc2']=out2

    return output

