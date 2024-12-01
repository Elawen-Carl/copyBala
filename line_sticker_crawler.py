import os
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
from googletrans import Translator
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
import torch
from io import BytesIO
import json
import random

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
        
        # 设置代理
        self.proxies = {
            'http': 'http://127.0.0.1:7897',
            'https': 'http://127.0.0.1:7897'
        }
        
        # 设置环境变量，让huggingface_hub使用代理
        os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7897'
        os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7897'
        
        # # 初始化BLIP模型
        # try:
        #     print("正在加载BLIP模型...")
        #     self.device = "cuda" if torch.cuda.is_available() else "cpu"
        #     self.processor = BlipProcessor.from_pretrained(
        #         "Salesforce/blip-image-captioning-base",
        #     )
        #     self.model = BlipForConditionalGeneration.from_pretrained(
        #         "Salesforce/blip-image-captioning-base",
        #     ).to(self.device)
        #     print("BLIP模型加载完成")
        # except Exception as e:
        #     print(f"加载BLIP模型失败: {str(e)}")
        #     raise
        
        self.sticker_data = {
            "name": "",
            "description": "",
            "author": "",
            "images": []
        }
        
    def create_save_dir(self):
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            
    def download_image(self, img_url, index, total, retry=3):
        for attempt in range(retry):
            try:
                response = self.session.get(
                    img_url, 
                    headers=self.headers,
                    verify=False,
                    timeout=30,
                    proxies=self.proxies
                )
                
                if response.status_code == 200:
                    print(f"正在下载 ({index}/{total}): {title}")
                    # 处理文件名（移除非法字符）
                    filename = f"sticker_{index}.png"
                    
                    # 保存图片
                    file_path = os.path.join(self.save_dir, filename)
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    
                    # 添加到sticker数据中
                    self.sticker_data['images'].append({
                        "title": title,
                        "path": filename,
                        "type": "local"
                    })
                    
                    print(f"成功下载: {filename}")
                    return True
                    
                else:
                    print(f"下载失败: HTTP {response.status_code}")
                    
            except Exception as e:
                if attempt == retry - 1:
                    print(f"下载失败: {str(e)}")
                else:
                    print(f"下载重试 {attempt + 1}/{retry}")
                    time.sleep(2)
        return False

    def download_all_images(self, img_urls):
        success_count = 0
        total = len(img_urls)
        
        for i, img_url in enumerate(img_urls):
            if self.download_image(img_url, i, total):
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
                # 修改代理配置，添加代理检查
                try:
                    proxies = {
                        'http': 'http://127.0.0.1:7897',
                        'https': 'http://127.0.0.1:7897'
                    }
                    # 测试代理连接
                    test_response = self.session.get('https://www.google.com', 
                        proxies=proxies, 
                        timeout=5,
                        verify=False
                    )
                except:
                    print("代理服务器连接失败，尝试直接连接...")
                    proxies = None  # 代理失败时不使用代理
                    
                response = self.session.get(
                    self.url, 
                    headers=self.headers, 
                    verify=False,
                    timeout=30,
                    proxies=proxies  # 根据测试结果决定是否使用代理
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

    def get_image_title(self, image_content):
        try:
            # 将图片内容转换为PIL Image
            image = Image.open(BytesIO(image_content))
            if image.mode == 'P':
                image = image.convert('RGBA')
            image = image.convert('RGB')
            
            # 使用更简单的prompt
            prompt = "description of this sticker:"  # 尝试不使用prompt
            
            # 处理图片并生成描述
            inputs = self.processor(image, return_tensors="pt").to(self.device)
            
            out = self.model.generate(
                **inputs,
                max_length=20,          # 减小最大长度
                min_length=5,           # 设置最小长度
                num_beams=3,            # 使用较小的beam数
                temperature=1.0,        # 使用默认temperature
                repetition_penalty=1.0,  # 重置重复惩罚
                length_penalty=1.0,      # 添加长度惩罚
                use_cache=True
            )
            
            # 添加更多调试信息
            title = self.processor.decode(out[0], skip_special_tokens=True)
            print(f"模型输出设备: {out.device}")
            print(f"输入图片尺寸: {image.size}")
            print(f"原始输出: {title}")
            
            # 移除prompt部分
            if prompt in title.lower():
                title = title.lower().replace(prompt.lower(), "").strip()
            
            # 在翻译之前确保文本不为空
            if not title.strip():
                return f"sticker_{random.randint(1000, 9999)}"
            
            # 翻译成中文
            translator = Translator()
            title_zh = translator.translate(title, dest='zh-cn').text
            
            # 限制标题长度
            if len(title_zh) > 15:
                title_zh = title_zh[:15]
            
            return title_zh
            
        except Exception as e:
            print(f"图片标题生成失败: {str(e)}")
            return f"sticker_{random.randint(1000, 9999)}"

    def get_sticker_info(self):
        """获取贴图集的基本信息"""
        try:
            # 先尝试从本地HTML文件读取
            try:
                with open('卡皮巴啦x小日常 – LINE貼圖 _ LINE STORE.html', 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except FileNotFoundError:
                response = self.session.get(
                    self.url, 
                    headers=self.headers, 
                    verify=False,
                    timeout=30,
                    proxies=self.proxies
                )
                html_content = response.text
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 获取标题
            title_elem = soup.find('p', class_='mdCMN38Item01Ttl')
            self.sticker_data['name'] = title_elem.text.strip() if title_elem else "未知贴图集"
            
            # 获取作者
            author_elem = soup.find('a', class_='mdCMN38Item01Author')
            self.sticker_data['author'] = author_elem.text.strip() if author_elem else "未知作者"
            
            # 获取描述
            desc_elem = soup.find('p', class_='mdCMN38Item01Txt')
            self.sticker_data['description'] = desc_elem.text.strip() if desc_elem else "无描述"
            
        except Exception as e:
            print(f"获取贴图信息失败: {str(e)}")
            self.sticker_data.update({
                'name': "未知贴图集",
                'author': "未知作者",
                'description': "无描述"
            })

    def save_sticker_data(self):
        """保存贴图数据到JSON文件"""
        try:
            output_file = os.path.join(self.save_dir, 'sticker_data.json')
            # 将数据包装成列表格式
            data_to_save = [self.sticker_data]
            img_urls = self.get_sticker_urls()
            for i, img_url in enumerate(img_urls):
                self.sticker_data['images'].append({
                    "title": f"sticker_{i}",
                    "path": img_url,
                    "type": "remote"
                })
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            print(f"贴图数据已保存到: {output_file}")
        except Exception as e:
            print(f"保存贴图数据失败: {str(e)}")

    def run(self):
        start_time = time.time()
        
        print("开始爬取LINE贴图...")
        self.create_save_dir()
        
        # 先获取贴图集基本信息
        self.get_sticker_info()
        
        img_urls = self.get_sticker_urls()
        if not img_urls:
            print("没有找到贴图URL")
            return
            
        total_count = len(img_urls)
        # print(f"找到 {total_count} 个贴图，开始下载...")
        print(f"找到 {total_count} 个贴图")
        
        # 下载图片
        # success_count = self.download_all_images(img_urls)
        
        # 保存贴图数据
        self.save_sticker_data()
        
        end_time = time.time()
        # print(f"爬取完成! 成功: {success_count}/{total_count} 用时: {end_time - start_time:.2f} 秒")

if __name__ == "__main__":
    url = "https://store.line.me/emojishop/product/6319855a83603436e7d1951d/zh-Hant"
    crawler = LineStickerCrawler(url)
    crawler.run() 