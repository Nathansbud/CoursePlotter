from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *

from goog import write_sheet, index_to_column, get_sheet
from threading import Thread
from enum import Enum

import atexit
import traceback
import os
import json

options = webdriver.ChromeOptions()
browser = webdriver.Chrome(options=options)
# atexit.register(browser.quit)

sheet_id = "1-5-Wk-GXcZVccyHVAl77P3n71MSyc3js3-c1z1WrEzY"
review_link_column = "G"

class HandleMethod(Enum):
    NONE = 0
    NUMBER_AVERAGE = 1
    YES_NO = 2

def populate_courses():
    browser.get("https://cab.brown.edu")
    browser.implicitly_wait(3)

    term_selector = browser.find_element_by_id("crit-srcdb")
    course_selector = browser.find_element_by_id("crit-coursetype")
    terms = ['fall', 'spring']

    course_dict = {
        s:{"0000":{},"1000":{},"2000":{}} for s in terms
    }

    # 202010, 202020 = fall, spring
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
                        Thread(target=lambda: write_sheet(sheet=sheet_id,values=vals,r=f"{terms[term]}!A{i+2+600*linc}:{index_to_column(len(vals[0]))}{i+2+600*linc}")).start()
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
                Thread(target=lambda: write_sheet(sheet=sheet_id, values=vals,
                                                  r=f"{terms[term]}!A{i+2+600*linc}:{index_to_column(len(vals[0]))}{i+2+600*linc}")).start()
                print(i, course_code, course_name)
                course_data.find_element_by_class_name("panel__back").click()

def fmean(l):
    fl = list(filter(None, l))
    return sum([int(f) for f in fl])/len(fl)

def get_reviews():
    with open(os.path.join(os.path.dirname(__file__), "credentials", "brown.json")) as jf: creds = json.load(jf)
    review_links = get_sheet(sheet=sheet_id, r=f"fall!{review_link_column}2:{review_link_column}1500", mode="COLUMNS").get("values")[0]
    browser.get("https://thecriticalreview.org/search/FORCE_LOGIN")
    browser.find_element_by_id("username").send_keys(creds['username'])
    browser.find_element_by_id("password").send_keys(creds['password'])
    browser.find_element_by_tag_name("button").click()
    for i, url in enumerate(review_links):
        if url and "thecriticalreview" in url:
            browser.get(url)
            if not len(browser.find_elements_by_class_name("course_title")) > 0:
                Thread(target=lambda: write_sheet(sheet=sheet_id, values=[["No reviews found!"]], r=f"fall!H{i+2}")).start()
            else:
                WebDriverWait(browser, 10).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, "review_data")))
                rd = browser.find_element_by_class_name("review_data").get_attribute("data-test-value")
                review_data = json.loads(rd) if rd else {}
                class_data = {
                    "clear-goals":{"fmt":"Clear Goals"},
                    "grading-speed":{"fmt":"Grading Speed"},
                    "readings":{"fmt":"Readings Worthwhile"},
                    "grading-fairness":{"fmt":"Fair Grading"}
                }
                for k in review_data:
                    if k in class_data:
                        if not "method" in class_data[k] or class_data[k]['method'] == HandleMethod.NUMBER_AVERAGE:
                            class_data[k]['value'] = fmean(review_data[k])
                        elif class_data[k]['method'] == HandleMethod.YES_NO:
                            class_data[k]['value'] = review_data[k].count("N") / review_data[k].count("Y")

                print(class_data)



                """
                "clear-goals",
                "grading-speed",
                "grading-fairness",
                "readings",
                "assignments",
                "class-materials",
                "learned",
                "loved",
                "non-concs",
                "effective",
                "efficient",
                "pacing",
                "pacing",
                "motivated",
                "feedback-available",
                "feedback-useful",
                "conc",
                "requirement",
                "graded",
                "grade":["B","A","B","A","A","C","","B","A","","A","B","A","A","A","C","B","A","B","A","B","B"],
                "attendance",
                "minhours",
                "maxhours"

                """


                # Thread(target=lambda: write_sheet(sheet=sheet_id, values=[["Reviews found lmao"]], r=f"fall!H{i + 2}")).start()


if __name__ == '__main__':
    get_reviews()
    pass


