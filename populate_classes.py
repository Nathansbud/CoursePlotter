from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *

from goog import write_sheet, index_to_column
from threading import Thread

import atexit
import traceback

options = webdriver.ChromeOptions()
# options.add_argument("headless")
browser = webdriver.Chrome(options=options)

atexit.register(browser.quit)

#202010, 202020 = fall, spring

browser.get("https://cab.brown.edu")
browser.implicitly_wait(3)

term_selector = browser.find_element_by_id("crit-srcdb")
course_selector = browser.find_element_by_id("crit-coursetype")
ignored_exceptions = (NoSuchElementException, StaleElementReferenceException)
terms = ['fall', 'spring']

course_dict = {
    s:{"0000":{},"1000":{},"2000":{}} for s in terms
}

for term, t in enumerate(term_selector.find_elements_by_xpath(".//option[@value='202010' or @value='202020']")):
    t.click()
    for level, option in enumerate(course_selector.find_elements_by_tag_name("option")[1:]):
        linc = level
        option.click()
        browser.find_element_by_id("search-button").click()
        classes = browser.find_elements_by_class_name("result--group-start")
        for i, c in enumerate(classes):
            c.click()
            try:
                ww = WebDriverWait(browser, 5).until(expected_conditions.text_to_be_present_in_element((By.CLASS_NAME, "dtl-course-code"), c.find_element_by_class_name("result__code").text))
            except TimeoutException:
                try:
                    tab_text = c.text.split("\n")
                    tab_department, tab_number = tab_text[0].split(" ")
                    tab_name = tab_text[1]
                    tab_instructor = tab_text[-1] if tab_text[-2] == "Instructor:" else ""
                    tab_description = "Couldn't load course data in time"
                    print(i, tab_department, tab_number, tab_name, tab_instructor)
                    vals = [[tab_department, tab_number, tab_name, tab_description, tab_instructor]]
                    Thread(target=lambda: write_sheet(sheet="1-5-Wk-GXcZVccyHVAl77P3n71MSyc3js3-c1z1WrEzY",values=vals,r=f"{terms[term]}!A{i+2+600*linc}:{index_to_column(len(vals[0]))}{i+2+600*linc}")).start()
                except StaleElementReferenceException:
                    print("idk how that happened but uhhhh...SER thrown")
                continue

            course_data = browser.find_elements_by_class_name("panel__content")[-1]
            # print(i, course_data.get_property("innerHTML"))
            course_code = course_data.find_element_by_class_name("dtl-course-code").text
            if course_code.strip().endswith("XLIST"):
                print("SKIPPING", i)
                i -= 1
                continue
            course_department, course_number = course_code.split(" ")
            course_name = course_data.find_element_by_class_name("detail-title").text

            cds = course_data.find_elements_by_class_name("section--description")
            course_description = cds[0].find_element_by_class_name("section__content").text if len(cds) > 0 else ""

            crl = course_data.find_elements_by_class_name("detail-resources_critical_review_html")
            course_review_link = crl[0].find_element_by_tag_name("a").get_attribute("href") if len(crl) > 0 else ""

            ci = course_data.find_elements_by_class_name("instructor-name")
            course_instructor = ci[0].text if len(ci) > 0 else ""

            rr = course_data.find_elements_by_class_name("section--registration_restrictions")
            course_requirements = rr[0].find_element_by_class_name("section__content").text if len(rr) > 0 else ""

            course_dict[terms[term]][str(linc)+"000"][course_code] = {
                "code":course_code,
                "name":course_name,
                "description":course_description,
                "prerequisites":course_requirements,
                "reviews":course_review_link,
                "instructor":course_instructor
            }
            vals = [[course_department, course_number, course_name, course_description, course_instructor, course_requirements, course_review_link]]
            Thread(target=lambda: write_sheet(sheet="1-5-Wk-GXcZVccyHVAl77P3n71MSyc3js3-c1z1WrEzY", values=vals,
                                              r=f"{terms[term]}!A{i+2+600*linc}:{index_to_column(len(vals[0]))}{i+2+600*linc}")).start()
            print(i, course_code, course_name)
            course_data.find_element_by_class_name("panel__back").click()



