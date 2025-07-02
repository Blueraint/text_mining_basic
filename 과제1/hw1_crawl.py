from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from urllib.parse import urlparse, parse_qs, parse_qsl
import time
from datetime import datetime, timedelta
import re
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
from selenium.webdriver.chrome.service import Service as ChromeService

service = Service()
options = webdriver.ChromeOptions()
# options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# driver = webdriver.Chrome(service=service, options=options)
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))


site_url = "https://www.teamblind.com/kr/topics/부동산"


# 작성일(절대날짜 추출)
def convert_date(relative_text):
    """
    상대적인 시간 표현을 절대 날짜로 변환하는 함수
    
    Args:
        relative_text (str): '방금', '2분', '1시간', '1일', '1달' 등의 텍스트
    
    Returns:
        str: '%Y-%m-%d' 형태의 절대 날짜
    """
    # 현재 날짜 및 시간
    now = datetime.now()
    # 공백 제거 및 소문자 변환
    text = relative_text.strip()
    # '방금'인 경우 오늘 날짜 반환
    if text == '방금':
        return now.strftime('%Y-%m-%d')
    
    # 숫자와 단위 추출을 위한 정규표현식
    pattern = r'(\d+)(분|시간|일|달|주)'
    match = re.search(pattern, text)
    
    if not match:
        # 패턴이 매치되지 않으면 오늘 날짜 반환
        return now.strftime('%Y-%m-%d')
    
    number = int(match.group(1))
    unit = match.group(2)
    
    # 단위별로 날짜 계산
    if unit == '분':
        target_date = now - timedelta(minutes=number)
    elif unit == '시간':
        target_date = now - timedelta(hours=number)
    elif unit == '일':
        target_date = now - timedelta(days=number)
    elif unit == '주':
        target_date = now - timedelta(weeks=number)
    elif unit == '달':
        # 달의 경우 대략 30일로 계산 (정확하지 않을 수 있음)
        target_date = now - timedelta(days=number * 30)
    else:
        target_date = now
    
    return target_date.strftime('%Y-%m-%d')


def get_comment_txt(comment) :
    comment_map = {}
    comment_map['firm']=comment.text.split('·')[0] # 리플 작성회사
    comment_map['id']=comment.text.split('·')[1].split('\n')[0]  # 리플 작성ID
    # comment_map['contents']=comment.text.split('·')[1].split('\n')[1]  # 리플 내용
    comment_map['contents']=comment.text.split('·')[1].split(comment.text.split('·')[1].split('\n')[0])[1].split('작성일')[0] # 리플 내용
    
    return comment_map


# 게시물 이동 후 모든 컨텐츠를 가져오는 함수 definition
def get_article(link) : 
    try :
        driver.get(link)
        article = {}
        # 제목 (<h2>)
        title=driver.find_element(By.CLASS_NAME, "article-view-head").find_element(By.CSS_SELECTOR, "h2").text
        # 게시글
        body=driver.find_element(By.CLASS_NAME, "article-view-contents").find_element(By.ID, "contentArea").text
        # 작성회사
        writer_firm=driver.find_element(By.CLASS_NAME, "name").find_element(By.CLASS_NAME, "point").text
        # 작성ID
        writer_id=driver.find_element(By.CLASS_NAME, "name").text.split('\n')[-1]

        # 작성일
        write_date_before=driver.find_element(By.CLASS_NAME, "date").text.split('\n')[-1]
        write_date=convert_date(write_date_before)

        # 좋아요
        like_cnt=driver.find_element(By.CLASS_NAME, "like").text.split('\n')[-1]

        # 댓글수
        comment_cnt=driver.find_element(By.CLASS_NAME, "cmt").text.split('\n')[-1]

        # 댓글 세부내용 추출
        # 댓글이 더 있는경우 모두 펼친다
        # 이 기능은 로그인 되어있는 경우만 가능
        while True :
            # Blind 인증 요구 시 다음 Element 가 생긴다
            # 해당 Element가 존재한다면 로그인 불가로 간주하고 현재 보여지는 댓글만 가져오고 끝낸다
            # 해당 Element가 없다면, try-catch 로 계속 진행하도록 수행(로그인 된 것으로 간주)
            try :
                try :
                    driver.find_element(By.CLASS_NAME, "btn-reply").click()
                except :
                    break
                
                if(driver.find_element(By.XPATH, "/html/body/div/div/div/main/div[3]/div[1]/div")) :
                    # driver.find_element(By.CLASS_NAME, "btn-cls").click()
                    driver.find_element(By.CSS_SELECTOR, "#wrap > div:nth-child(4) > div:nth-child(1) > div > div.v--modal-box.v--modal.v--size-s > div > div.ly-modal.ly-signin > div.top-area > button").click()
                    break
            except :
                continue
            
    
        comment_element_list=driver.find_elements(By.CLASS_NAME, "comment_area")
        comment_map = [get_comment_txt(x) for x in comment_element_list]
        
        # Make tuple
        article['title']=title
        article['body']=body
        article['firm']=writer_firm
        article['id']=writer_id
        article['like_cnt']=like_cnt
        article['comment_cnt']=comment_cnt
        article['comment_map']=comment_map
        
        print(f"[세부 글] {article}")
    
        driver.back()
    except :
        return None
 
    return article


def get_article_list(url, crawl_cnt) :
    try :
        driver.get(url)
        driver.implicitly_wait(3)
        time.sleep(2)  # 페이지 로딩 대기

        article_pre_data = []

        # 게시물 첫번째거 설정(최초 1회, 이후에는 sibling 으로 설정)
        article_preview=driver.find_element(By.CLASS_NAME, "article-list-pre")

        for i in range(0, crawl_cnt+1) :
            article_object={}
            
            # 광고로 게시물인 경우 넘어간다
            # 게시물 text 가 'NOW\n' or 'HOT\n' 으로 시작하면 추천게시물이므로 넘어간다
            # 이외의 경우 반복 게시물 크롤링 시작
            if(article_preview.get_attribute('class').lower().endswith('ad') == False and
                article_preview.text.startswith('HOT\n') == False and
                article_preview.text.startswith('NOW\n') == False) :
                #title on list
                title = article_preview.find_element(By.CLASS_NAME, "tit").find_element(By.XPATH, 'h3/a').text
                
                # article link
                link = article_preview.find_element(By.CLASS_NAME, "tit").find_element(By.XPATH, 'h3/a').get_attribute('href')
                
                # article pre-text
                pre_text = article_preview.find_element(By.CLASS_NAME, "tit").find_element(By.CLASS_NAME, 'pre-txt').text
                
                # article firm
                firm = article_preview.find_element(By.CLASS_NAME, "sub").find_element(By.CLASS_NAME, 'name').text.split('·')[0]
                
                # article id
                id = article_preview.find_element(By.CLASS_NAME, "sub").find_element(By.CLASS_NAME, 'name').text.split('·')[1]
            
                # article date
                date_before = article_preview.find_element(By.CLASS_NAME, "sub").find_element(By.CLASS_NAME, 'info_fnc').find_element(By.CLASS_NAME, "past").text.split('작성시간\n')[1]
                date=convert_date(date_before)
            
                article_object['title']=title
                article_object['link']=link
                article_object['pre_text']=pre_text
                article_object['firm']=firm
                article_object['id']=id
                article_object['date']=date
                
                print(f"[{i}번째] {article_object}")
                
                article_pre_data.append(article_object)
                
            try :
                article_preview = article_preview.find_element(By.XPATH, './following-sibling::div')
            # 스크롤링의 끝인 경우 새로운 스크롤링 수행 후 계속 크로링 수행
            except NoSuchElementException as e:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)    
                
                print("### 스크롤링 완료###")
    finally :
        return article_pre_data
    
# article_doc 을 series 로 반환하는 함수
def extract_article_data(row):
    article_tuple = row['article_doc']
    
    # --- ✨ 가장 중요한 수정 포인트 ---
    # 본격적인 처리를 시작하기 전에 article_tuple이 None인지 먼저 확인합니다.
    # 만약 None이면, 더 이상 진행하지 않고 즉시 None 시리즈를 반환하여 TypeError를 방지합니다.
    if article_tuple is None:
        return pd.Series([None, None, None, None])

    # 이 아래 코드는 article_tuple이 None이 아닐 경우에만 실행됩니다.
    print(f"row : {row}")
    print(f"article_tuple : {article_tuple}")
    
    # 이 부분은 article_doc이 딕셔너리라고 가정하고 작성되었습니다.
    # 만약 문자열이라면 변환 과정이 필요합니다. (아래 '추가 제안' 참고)
    try:
        # 튜플의 첫 번째 요소(제목)와 title 컬럼의 값을 비교
        print(row['title'])
        print(article_tuple['title'])
        
        print(type(row['title']))
        print(type(article_tuple['title']))
        
        if (row['title'] == article_tuple['title']) :
            # 일치하면 body, like_cnt, comment_cnt, comment_map 값을 반환
            res_series = pd.Series([article_tuple['body'], article_tuple['like_cnt'], article_tuple['comment_cnt'], article_tuple['comment_map']])
            
            # print문은 '+'가 아닌 ',' 로 연결해야 합니다.
            print("####", res_series)
            return res_series
        else :
            # 제목이 불일치하면 None으로 채운 Series를 반환
            return pd.Series([None, None, None, None])

    except (TypeError, KeyError) as e:
        # article_tuple이 딕셔너리가 아니거나(예: 튜플, 리스트)
        # 'title' 같은 키가 없을 때 발생할 수 있는 오류를 방지합니다.
        print(f"데이터 처리 중 오류 발생: {e}. 해당 행은 None으로 처리됩니다.")
        return pd.Series([None, None, None, None])
    
    
    
# get list    
list = get_article_list(site_url, 50000)
df = pd.DataFrame(list)
df.to_csv("blind_topic_realestate_20250703.csv",encoding="utf-8")

df['article_doc'] = df.apply(lambda x : get_article(x.link) , axis=1)

new_cols = ['body', 'like_cnt', 'comment_cnt', 'comment_map']
df[new_cols] = df.apply(extract_article_data, axis=1)

df.to_csv("blind_topic_realestate_final_20250703.csv", encoding="utf-8")