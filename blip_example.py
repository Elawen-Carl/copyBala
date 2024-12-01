import torch
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
import requests
from io import BytesIO
import os
from googletrans import Translator
import random

class Test:   
    def __init__(self, url):
        
        # 设置代理
        self.proxies = {
            'http': 'http://127.0.0.1:7897',
            'https': 'http://127.0.0.1:7897'
        }
        
        # 设置环境变量，让huggingface_hub使用代理
        os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7897'
        os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7897'
        
        # 初始化BLIP模型
        try:
            print("正在加载BLIP模型...")
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.processor = BlipProcessor.from_pretrained(
                "Salesforce/blip-image-captioning-base",
            )
            self.model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base",
            ).to(self.device)
            print("BLIP模型加载完成")
        except Exception as e:
            print(f"加载BLIP模型失败: {str(e)}")
            raise
        
    def get_image_title(self, image_path):
        try:
            # 读取本地图片文件
            with open(image_path, 'rb') as f:
                image_content = f.read()
            
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

if __name__ == "__main__":
    # 示例1：使用本地图片
    print("\n示例1：处理本地图片")
    test = Test("./line_stickers/sticker_1.png")
    print(test.get_image_title("./line_stickers/sticker_2.png"))