from selenium import webdriver
from selenium.common.exceptions import *
import atexit
import traceback

browser = webdriver.Chrome()
atexit.register(browser.quit)

#202010, 202020 = fall, spring

browser.get("https://cab.brown.edu")
browser.implicitly_wait(5)

term_selector = browser.find_element_by_id("crit-srcdb")
course_selector = browser.find_element_by_id("crit-coursetype")

for term in term_selector.find_elements_by_xpath(".//option[@value='202010' or @value='202020']"):
    term.click()
    for option in course_selector.find_elements_by_tag_name("option")[1:]:
        option.click()
        browser.find_element_by_id("search-button").click()
        classes = browser.find_elements_by_class_name("result--group-start")
        for c in classes:
            c.click()
            found = False
            while not found:
                try:
                    course_data = browser.find_elements_by_class_name("panel__content")[-1]
                    course_code = course_data.find_element_by_class_name("dtl-course-code").text
                    if course_code.strip().endswith("XLIST"): break
                    course_name = course_data.find_element_by_class_name("detail-title").text
                    course_description = course_data.find_element_by_class_name("section--description").find_element_by_class_name("section__content").text
                    course_review_link = course_data.find_element_by_class_name("detail-resources_critical_review_html").find_element_by_tag_name("a").get_attribute("href")
                    course_instructor = course_data.find_element_by_class_name("instructor-name").text
                    print(course_code, course_name, course_description, course_review_link, course_instructor)
                    course_data.find_element_by_class_name("panel__back").click()
                    found = True
                except StaleElementReferenceException:
                    # traceback.print_exc()
                    print("Failed to get element; retrying...")


