import os
import time
import json
import requests
import subprocess
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

def ensure_dir(directory):
    '''如果目录不存在，则创建它'''
    if not os.path.exists(directory):
        os.makedirs(directory)

def download_file(url, filename, retry_times=3):
    '''从给定的URL下载mp4文件，并保存。支持断点续传和错误重试'''
    for _ in range(retry_times):
        try:
            # 如果文件已存在，那么就获取已下载的文件大小
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
            else:
                file_size = 0
            headers = {"Range": f"bytes={file_size}-"}
            response = requests.get(url, headers=headers, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            # 使用tqdm显示下载进度
            progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)
            progress_bar.update(file_size)
            with open(filename, 'ab') as fp:
                for data in response.iter_content(chunk_size=1024):
                    progress_bar.update(len(data))
                    fp.write(data)
            progress_bar.close()
            break
        except requests.exceptions.RequestException as e:
            print(f"Error downloading file, retrying... ({str(e)})")
            continue
    else:
        print(f"Failed to download file after {retry_times} attempts.")

def merge_videos(filenames, output_filename):
    '''使用ffmpeg的concat功能来合并mp4文件'''
    with open('filelist.txt', 'w') as f:
        for filename in filenames:
            f.write(f"file '{filename}'\n")
    subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', 'filelist.txt', '-c', 'copy', output_filename])

def delete_temp_files(filenames):
    '''删除临时文件'''
    for filename in filenames:
        if os.path.exists(filename):
            os.remove(filename)
    if os.path.exists('filelist.txt'):
        os.remove('filelist.txt')

def process_json_url(url):
    '''从指定的URL下载json，并处理其中的mp4链接'''
    response = requests.get(url)
    data = json.loads(response.text)
    filenames = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        for i, next_level_url in enumerate(data['data']['mp4PlayUrl']):
            next_level_data = requests.get(next_level_url).json()
            for server in next_level_data['servers']:
                mp4_url = server['url']
                filename = os.path.join('tmp', f'temp_{i}.mp4')
                filenames.append(filename)
                executor.submit(download_file, mp4_url, filename)

    time_string = time.strftime("%Y%m%d-%H%M%S")
    output_filename = os.path.join('out', f'output_{time_string}.mp4')
    merge_videos(filenames, output_filename)
    delete_temp_files(filenames)

ensure_dir('tmp')
ensure_dir('out')
json_url = input
process_json_url(json_url)
