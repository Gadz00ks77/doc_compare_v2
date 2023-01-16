import cv2
import numpy as np
import os,shutil
from pathlib import Path
import copy
import concurrent.futures

def del_image_files(folder_name):

    folder = f'./bold_images/{folder_name}'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except:
            pass

def process_image(folder_name,image_file_name):

    img = cv2.imread(f'./pdf_images/{folder_name}/{image_file_name}')
    # img = cv2.imread('./pil_out/easyfly/image-12.png') 
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)[1]
    kernel = np.ones((5,5),np.uint8)
    kernel2 = np.ones((3,3),np.uint8)
    marker = cv2.dilate(thresh,kernel,iterations = 1)
    mask=cv2.erode(thresh,kernel,iterations = 1)

    while True:
        tmp=marker.copy()
        marker=cv2.erode(marker, kernel2)
        marker=cv2.max(mask, marker)
        difference = cv2.subtract(tmp, marker)
        
        if cv2.countNonZero(difference) == 0:
            break

    marker_color = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
    out=cv2.bitwise_or(img, marker_color)
    cv2.imwrite(filename=f'./bold_images/{folder_name}/{image_file_name}',img=out)

    return 1

def gen_file_paths(img_folder):

    file_names = []

    for filename in os.listdir(img_folder):
        file_names.append(filename)

    return file_names

def run_bold_process(file_name):

    folder_name = file_name.replace(' ','_').replace('-','_').replace(".pdf","")
    img_folder = f'./pdf_images/{folder_name}'

    Path(f"./bold_images/{folder_name}").mkdir(parents=True, exist_ok=True)
    del_image_files(folder_name=folder_name)

    file_set = gen_file_paths(img_folder=img_folder)

    # for filename in os.listdir(img_folder):
        # file_path = os.path.join(img_folder, filename)
        # process_image(folder_name=folder_name,image_file_name=filename)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_image = {executor.submit(process_image,folder_name,fname): fname for fname in file_set}
        for future in concurrent.futures.as_completed(future_to_image):
            fname = future_to_image[future]
            data = future.result()

    return 1

