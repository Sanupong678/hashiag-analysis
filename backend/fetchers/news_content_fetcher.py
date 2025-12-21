"""
News Content Fetcher - ดึงรายละเอียดเพิ่มเติมของข่าวจาก URL
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
import time
from urllib.parse import urlparse
import re

class NewsContentFetcher:
    """
    ดึงรายละเอียดเพิ่มเติมของข่าวจาก URL
    - Full article content
    - Images
    - Tags/Categories
    - Author details
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.timeout = 10  # 10 seconds timeout
    
    def fetch_article_content(self, url: str) -> Optional[Dict]:
        """
        ดึงรายละเอียดเพิ่มเติมของข่าวจาก URL
        
        Args:
            url: URL ของข่าว
        
        Returns:
            Dictionary with article details หรือ None ถ้าไม่สามารถดึงได้
        """
        if not url or url == '':
            return None
        
        try:
            # Rate limiting - รอ 0.5 วินาทีก่อน request
            time.sleep(0.5)
            
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # ดึง title
            title = self._extract_title(soup)
            
            # ดึงเนื้อหาหลัก
            content = self._extract_content(soup)
            
            # ไม่ดึงรูปภาพเพื่อลดพื้นที่ในการจัดเก็บ
            # images = self._extract_images(soup, url)
            
            # ดึง tags/categories
            tags = self._extract_tags(soup)
            
            # ดึง author
            author = self._extract_author(soup)
            
            # ดึง publish date
            publish_date = self._extract_publish_date(soup)
            
            return {
                'title': title,  # เพิ่ม title ที่ดึงจาก HTML
                'full_content': content,
                # 'images': images,  # ไม่ดึงรูปภาพเพื่อลดพื้นที่
                'tags': tags,
                'author': author,
                'publish_date': publish_date,
                'word_count': len(content.split()) if content else 0,
                'content_fetched_at': time.time()
            }
            
        except requests.exceptions.RequestException as e:
            # Network error - ไม่ต้อง log ทุกครั้ง
            return None
        except Exception as e:
            # Error อื่นๆ
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """
        ดึง title ของบทความ
        """
        # ลองหาจาก meta tags ก่อน
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
        
        # หาจาก title tag
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            if title_text:
                return title_text
        
        # หาจาก h1
        h1 = soup.find('h1')
        if h1:
            h1_text = h1.get_text(strip=True)
            if h1_text:
                return h1_text
        
        return ''
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """
        ดึงเนื้อหาหลักของบทความ
        """
        # สำหรับ Yahoo Finance - ลองหาเนื้อหาจากหลายๆ tag ที่เป็นไปได้
        content_selectors = [
            'article',
            '[role="article"]',
            '.article-content',
            '.article-body',
            '.post-content',
            '.entry-content',
            '.content',
            'main',
            '[itemprop="articleBody"]',
            # Yahoo Finance specific selectors
            '[data-module="ArticleBody"]',
            '.caas-body',
            '.caas-article-body',
            '[data-test-locator="article-body"]'
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                # รวมเนื้อหาจากทุก element
                texts = []
                for elem in elements:
                    # ลบ script และ style tags
                    for script in elem(["script", "style", "nav", "footer", "header", "aside", "button", "a"]):
                        script.decompose()
                    
                    text = elem.get_text(separator=' ', strip=True)
                    if text and len(text) > 100:  # ต้องมีเนื้อหามากกว่า 100 ตัวอักษร
                        texts.append(text)
                
                if texts:
                    return ' '.join(texts)
        
        # ถ้าไม่เจอ ให้ดึงจาก <p> tags ทั้งหมด (เฉพาะใน main หรือ article)
        main_content = soup.find('main') or soup.find('article')
        if main_content:
            paragraphs = main_content.find_all('p')
            if paragraphs:
                texts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
                content = ' '.join(texts)
                if len(content) > 100:
                    return content
        
        # ถ้ายังไม่เจอ ให้ดึงจาก <p> tags ทั้งหมด
        paragraphs = soup.find_all('p')
        if paragraphs:
            texts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
            content = ' '.join(texts)
            if len(content) > 100:
                return content
        
        return ''
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list:
        """
        ดึงรูปภาพจากบทความ
        """
        images = []
        
        # หา main image (og:image หรือ article image)
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            images.append({
                'url': self._make_absolute_url(og_image['content'], base_url),
                'type': 'main'
            })
        
        # หา images ใน article
        article_images = soup.select('article img, [role="article"] img, .article-content img')
        for img in article_images[:5]:  # จำกัด 5 รูป
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src:
                images.append({
                    'url': self._make_absolute_url(src, base_url),
                    'alt': img.get('alt', ''),
                    'type': 'content'
                })
        
        return images
    
    def _extract_tags(self, soup: BeautifulSoup) -> list:
        """
        ดึง tags/categories
        """
        tags = []
        
        # หา meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            tags.extend([t.strip() for t in meta_keywords['content'].split(',')])
        
        # หา tags จาก HTML
        tag_elements = soup.select('.tags a, .categories a, [rel="tag"], .tag')
        for elem in tag_elements:
            tag_text = elem.get_text(strip=True)
            if tag_text:
                tags.append(tag_text)
        
        # ลบ duplicates และ return
        return list(set([t for t in tags if t]))
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """
        ดึงชื่อ author
        """
        # หาจาก meta tags
        author_meta = soup.find('meta', property='article:author') or soup.find('meta', attrs={'name': 'author'})
        if author_meta and author_meta.get('content'):
            return author_meta['content']
        
        # หาจาก HTML
        author_elem = soup.select_one('.author, [rel="author"], [itemprop="author"]')
        if author_elem:
            return author_elem.get_text(strip=True)
        
        return None
    
    def _extract_publish_date(self, soup: BeautifulSoup) -> Optional[str]:
        """
        ดึงวันที่ publish
        """
        # หาจาก meta tags
        date_meta = soup.find('meta', property='article:published_time') or soup.find('meta', attrs={'name': 'publish-date'})
        if date_meta and date_meta.get('content'):
            return date_meta['content']
        
        # หาจาก time tag
        time_elem = soup.find('time', attrs={'datetime': True})
        if time_elem:
            return time_elem['datetime']
        
        return None
    
    def _make_absolute_url(self, url: str, base_url: str) -> str:
        """
        แปลง relative URL เป็น absolute URL
        """
        if not url:
            return ''
        
        if url.startswith('http://') or url.startswith('https://'):
            return url
        
        parsed_base = urlparse(base_url)
        base = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        if url.startswith('//'):
            return f"{parsed_base.scheme}:{url}"
        elif url.startswith('/'):
            return f"{base}{url}"
        else:
            return f"{base}/{url}"

