import fitz
from pathlib import Path
import os,shutil

def del_image_files(folder_name):

    folder = f'./pdf_images/{folder_name}'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except:
            pass

def convert_image_set(pdf_file_name):

    pdf_file_name_noext = pdf_file_name.replace('.pdf','')
    working_file_name = pdf_file_name_noext.replace(' ','_').replace('-','_')
    Path(f"./pdf_images/{working_file_name}").mkdir(parents=True, exist_ok=True)
    del_image_files(working_file_name)

    pdffile = f'./working/{pdf_file_name_noext}.pdf' 
    doc = fitz.open(pdffile)
    zoom = 4
    mat = fitz.Matrix(zoom, zoom)
    count = 0
    for p in doc:
        count += 1
    for i in range(count):
        val = f"./pdf_images/{working_file_name}/image-{i+1}.png"
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=mat)
        pix.save(val)
    doc.close()

    return count