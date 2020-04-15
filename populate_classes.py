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
from copy import deepcopy
import time

options = webdriver.ChromeOptions()
browser = webdriver.Chrome(options=options)
atexit.register(browser.quit)

sheet_id = "1-5-Wk-GXcZVccyHVAl77P3n71MSyc3js3-c1z1WrEzY"

instructor_column = "F"
review_link_column = "G"
review_source_column = "H"
review_data_column = "J"

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
                    WebDriverWait(browser, 5).until(expected_conditions.text_to_be_present_in_element((By.CLASS_NAME, "dtl-course-code"), c.find_element_by_class_name("result__code").text))
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
                vals = [[course_department, course_number, course_name, course_description, course_requirements, course_instructor, course_review_link]]
                Thread(target=lambda: write_sheet(sheet=sheet_id, values=vals,
                                                  r=f"{terms[term]}!A{i+2+600*linc}:{index_to_column(len(vals[0]))}{i+2+600*linc}")).start()
                print(i, course_code, course_name)
                course_data.find_element_by_class_name("panel__back").click()

class HandleMethod(Enum):
    NONE = 0
    NUMBER_AVERAGE = 1
    YES_NO = 2
    CONCENTRATOR = 3

review_template = {
    "minhours": {"fmt": "Average Hours"},
    "maxhours": {"fmt": "Max Hours"},
    "difficulty": {"fmt": "Difficult"},
    "learned": {"fmt": "Useful"},
    "loved": {"fmt": "Enjoyable"},
    "effective": {"fmt": "Presentation"},
    "encouraged": {"fmt": "Discussion"},
    "passionate": {"fmt": "Passion"},
    "grading-fairness": {"fmt": "Fair Grading"},
    "receptive": {"fmt": "Feedback Receptiveness"},
    "clear-goals":{"fmt":"Clear Goals"},
    "readings":{"fmt":"Readings Worthwhile"},
    "class-materials":{"fmt":"Useful Materials"},
    "grading-speed": {"fmt": "Grading Speed"},
    "efficient":{"fmt":"Efficiency"},
    "availableFeedback": {"fmt":"Feedback Available"},
    "conc":{"fmt":"Concentrator (%)", "method":HandleMethod.CONCENTRATOR},
    "requirement":{"fmt":"Took for Requirement (%)", "method":HandleMethod.YES_NO},
    "non-conc": {"fmt":"Good for NC"},  # ???
    "grade":{"fmt":"Student Grade", "method":HandleMethod.NONE},
    "attendance":{"fmt":"Attendance Weighted"},
}

def fmean(l):
    fl = [t for t in list(filter(None, l)) if t is not "na"]
    if len(fl) == 0: return ""
    try:
        return round(sum([float(f) for f in fl])/len(fl), 2)
    except ValueError:
        print(f"ValueError thrown on list {fl}")
        return ""


def get_reviews(season='fall'):
    with open(os.path.join(os.path.dirname(__file__), "credentials", "brown.json")) as jf: creds = json.load(jf)
    course_cells = [{"instructor":p[0].strip() if len(p) > 0 else "", "url":p[1] if len(p) > 1 else ""} for p in
                    get_sheet(sheet=sheet_id, r=f"{season}!{instructor_column}2:{review_link_column}1500", mode="ROWS").get("values")]
    Thread(target=lambda: write_sheet(sheet=sheet_id, values=[["Most Recent Source", "Critical Review"] + [review_template[r]['fmt'] for r in review_template]], r=f"{season}!{review_source_column}1")).start()
    browser.get("https://thecriticalreview.org/search/FORCE_LOGIN")
    browser.find_element_by_id("username").send_keys(creds['username'])
    browser.find_element_by_id("password").send_keys(creds['password'])
    browser.find_element_by_tag_name("button").click()
    rs = 0
    for ro, entry in enumerate(course_cells[rs:]):
        i = ro + rs
        if entry['url'] and "thecriticalreview" in entry['url']:
            browser.get(entry['url'])
            sem = ""
            review = ""
            if not len(browser.find_elements_by_class_name("course_title")) > 0:
                Thread(target=lambda: write_sheet(sheet=sheet_id, values=[["No reviews found!", ""]], r=f"{season}!{review_source_column}{i+2}")).start()
            else:
                if not (len(entry['instructor']) > 0 and not entry['instructor'] == "TBD"):
                    Thread(target=lambda: write_sheet(sheet=sheet_id, values=[["No professor available; reviews withheld!", ""]], r=f"{season}!{review_source_column}{i + 2}")).start()
                else:
                    instructor_last_name = entry['instructor'].split(" ")[-1]
                    sem = browser.find_element_by_id("semester").text
                    review = "\n".join([s.strip() for s in browser.find_element_by_id("full_review_contents").text.split("\n") if len(s.strip()) > 0])
                    if not browser.find_element_by_id("professor").text.startswith(instructor_last_name):
                        history_dropdown = browser.find_element_by_id("past_offerings")
                        inputs = history_dropdown.find_elements_by_tag_name("input")
                        if len(inputs) > 0:
                            inputs[0].send_keys(instructor_last_name)
                            first_selection, no_item = history_dropdown.find_elements_by_xpath("//*[contains(@class, 'item') and not(contains(@class, 'filtered'))]"), history_dropdown.find_elements_by_class_name("message")
                            if len(no_item) != 0:
                                Thread(target=lambda: write_sheet(sheet=sheet_id, values=[[f"No reviews found for professor {entry['instructor']}!", ""]], r=f"{season}!{review_source_column}{i + 2}")).start()
                                continue
                            else:
                                lt = [f for f in first_selection if len(f.text) > 0]
                                if len(lt) > 0:
                                    lt[0].click()
                                else:
                                    Thread(target=lambda: write_sheet(sheet=sheet_id, values=[[f"No reviews found for professor {entry['instructor']}!", ""]], r=f"{season}!{review_source_column}{i + 2}")).start()

                        else:
                            Thread(target=lambda: write_sheet(sheet=sheet_id, values=[[f"No reviews found for professor {entry['instructor']}!", ""]],r=f"{season}!{review_source_column}{i + 2}")).start()

                    WebDriverWait(browser, 10).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, "review_data")))
                    rd = browser.find_element_by_class_name("review_data").get_attribute("data-test-value")
                    review_data = json.loads(rd) if rd else {}
                    review_formatted = deepcopy(review_template)

                    for k in review_data:
                        if k in review_formatted:
                            if not "method" in review_formatted[k] or review_formatted[k]['method'] == HandleMethod.NUMBER_AVERAGE:
                                review_formatted[k]['value'] = fmean(review_data[k])
                            elif review_formatted[k]['method'] == HandleMethod.YES_NO:
                                cy, cn = review_data[k].count("Y"), review_data[k].count("N")
                                review_formatted[k]['value'] = round(cy/(cy+cn), 2)
                            elif review_formatted[k]['method'] == HandleMethod.YES_NO:
                                cy, cn = review_data[k].count("C"), review_data[k].count("D")+review_data[k].count("N")
                                review_formatted[k]['value'] = round(cy/(cy+cn), 2)
                    Thread(target=lambda: write_sheet(sheet=sheet_id, values=[[sem, review]+[review_formatted[r]['value'] if 'value' in review_formatted[r] else "" for r in review_formatted]], r=f"{season}!{review_source_column}{i+2}")).start()

if __name__ == '__main__':
    get_reviews("fall")
    get_reviews("spring")


