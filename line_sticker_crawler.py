import os
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

class LineStickerCrawler:
    def __init__(self, url):
        self.url = url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        }
        self.save_dir = 'line_stickers'
        self.session = requests.Session()
        
    def create_save_dir(self):
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            
    def download_image(self, img_url, filename, retry=3):
        for attempt in range(retry):
            try:
                response = self.session.get(
                    img_url, 
                    headers=self.headers,
                    verify=False,
                    timeout=30
                )
                
                if response.status_code == 200:
                    file_path = os.path.join(self.save_dir, filename)
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    print(f"成功下载: {filename}")
                    return True
                else:
                    print(f"下载失败 {filename}: HTTP {response.status_code}")
            except Exception as e:
                if attempt == retry - 1:  # 最后一次重试
                    print(f"下载 {filename} 时发生错误: {str(e)}")
                else:
                    print(f"下载 {filename} 重试 {attempt + 1}/{retry}")
                    time.sleep(2)  # 重试前等待2秒
        return False

    def download_all_images(self, img_urls):
        success_count = 0
        total = len(img_urls)
        
        for i, img_url in enumerate(img_urls):
            filename = f"sticker_{i+1}.png"
            print(f"正在下载 ({i+1}/{total}): {filename}")
            if self.download_image(img_url, filename):
                success_count += 1
            time.sleep(1)  # 每次下载后等待1秒
        return success_count

    def get_sticker_urls(self):
        try:
            # 先尝试从本地HTML文件读取
            try:
                with open('卡皮巴啦x小日常 – LINE貼圖 _ LINE STORE.html', 'r', encoding='utf-8') as f:
                    html_content = f.read()
                print("从本地文件读取HTML成功")
            except FileNotFoundError:
                # 如果本地文件不存在，则从网络获取
                print("本地文件不存在，从网络获取...")
                response = self.session.get(
                    self.url, 
                    headers=self.headers, 
                    verify=False,
                    timeout=30
                )
                response.raise_for_status()
                html_content = response.text
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 使用set来存储URL，自动去重
            img_urls_set = set()
            
            # 找到所有带有background-image样式的span标签
            spans = soup.find_all('span', class_='mdCMN09Image')
            
            for span in spans:
                # 从style属性中提取URL
                style = span.get('style', '')
                url_match = re.search(r'url\((.*?)\)', style)
                if url_match:
                    img_url = url_match.group(1)
                    # 移除URL中可能存在的引号
                    img_url = img_url.strip("'").strip('"')
                    img_urls_set.add(img_url)  # 使用set添加，自动去重
            
            # 转换回列表
            return list(img_urls_set)
            
        except Exception as e:
            print(f"获取贴图URL时发生错误: {str(e)}")
            return []

    def run(self):
        start_time = time.time()
        
        print("开始爬取LINE贴图...")
        self.create_save_dir()
        
        img_urls = self.get_sticker_urls()
        if not img_urls:
            print("没有找到贴图URL")
            return
            
        total_count = len(img_urls)
        print(f"找到 {total_count} 个贴图，开始下载...")
        
        # 下载图片
        success_count = self.download_all_images(img_urls)
        
        end_time = time.time()
        print(f"爬取完成! 成功: {success_count}/{total_count} 用时: {end_time - start_time:.2f} 秒")

if __name__ == "__main__":
    url = "https://store.line.me/stickershop/product/24694000/zh-Hant"
    crawler = LineStickerCrawler(url)
    crawler.run() 