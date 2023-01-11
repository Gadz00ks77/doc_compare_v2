#DocCompare - Textract Ver
This version uses AWS textract and resolves the document section headers programmatically (instead of using a list to search for.)
This version is slower BUT it is cleaner and could be adapted for different document "types" more successfully.

##Instructions / Prereqs
1. Python 3.8
2. AWS Boto creds with an account with Textract permissions (using AWS CLI)
3. pip install the relevant libraries
4. create the folders as instructed
5. launch "streamlit run Landing_Page.py" from Command Line

###Libraries
* boto3
* streamlit
* opencv-python
* PyMuPDF
* spacy (with en_core_web_md)

###Folders
./working
./bold_images
./boldbox_working_textract
./pdf_images
./textbox_working_textract