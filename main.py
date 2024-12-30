from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from typing import Optional
from time import sleep
from tqdm import tqdm
import json
import re
import requests
import argparse


def fuzzy(s: str) -> str:
    return s.replace(" ", "").lower().strip()


def create_filename(s: str) -> str:
    return re.sub(r"[^\w]+", "_", s)

parser = argparse.ArgumentParser(description="Download classes listed in the input file.")
parser.add_argument("file", help="Path to the file containing the list of classes.")
args = parser.parse_args()

courses = []
with open(args.file, 'r') as file:
    for line in file:
        courses.append(line.strip())


class LeccapDownloader:
    fuzzy_course: str
    driver: webdriver.Chrome
    download_path: Path

    def __init__(self, folder_name: str, course_name: str, lecture: bool) -> None:
        self.lecture = lecture # whether to download the first link or the second and which folder to put it in
        self.fuzzy_course = fuzzy(course_name)
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--user-data-dir=chrome-data")
        self.driver = webdriver.Chrome(options=chrome_options)

        self.download_path = (
            Path(__file__).parent / "downloads" / folder_name
        )

    def close(self) -> None:
        self.driver.close()

    def go(self) -> None:
        course_links = self.find_course_links()
        if not course_links:
            print("[!] Could not find course! Check your search term.")
            return
        
        if self.lecture:
            assert len(course_links) == 1 or len(course_links) == 2
            self.download_course_link(course_links[0], self.lecture)
        else:
            assert len(course_links) == 2
            self.download_course_link(course_links[1], self.lecture)

    def goto_home(self) -> None:
        self.driver.get("https://leccap.engin.umich.edu/leccap/")
        sleep(1.0)
        while not self.driver.current_url.startswith(
            "https://leccap.engin.umich.edu"
        ):
            sleep(1.0)

    def find_course_links(self) -> Optional[list[WebElement]]:
        print("[i] Searching for course...")
        self.goto_home()
        by_year_link = self.driver.find_element(
            by=By.PARTIAL_LINK_TEXT, value="View courses by year"
        )
        by_year_link.click()
        while True:
            links = self.driver.find_elements(
                by=By.CSS_SELECTOR,
                value='a.list-group-item[href^="/leccap/site/"]',
            )

            matches = [
                link
                for link in links
                if fuzzy(link.text).startswith(course_name)
            ]
            if not matches:
                prev_year_link = self.driver.find_element(
                    by=By.CSS_SELECTOR, value=".previous > a:nth-child(1)"
                )
                if (
                    prev_year_link.get_attribute("href") == "#"
                    or prev_year_link.text[-4:] <= "2015"
                ):
                    return None
                prev_year_link.click()
            else:
                return matches

    def download_course_link(self, course_link: WebElement, lecture: bool) -> None:
        course_link.click()
        play_buttons = self.driver.find_elements(
            by=By.CSS_SELECTOR,
            value='.play-link>a.btn[href^="/leccap/player/r/"]',
        )
        jsons = []
        for btn in tqdm(play_buttons, desc="Download JSON", leave=False):
            href = btn.get_attribute("href")
            assert href
            slug = href.split("/")[-1]
            res = self.driver.execute_async_script(
                f"""
                const callback = arguments[arguments.length - 1];
                fetch("/leccap/player/api/product/?rk={slug}")
                    .then(res => res.json())
                    .then(json => callback(json));
                """
            )
            jsons.append(res)

        def json_filename(j: dict) -> str:
            date_parts = j["date"].split("/")
            date = f"{date_parts[2]}-{date_parts[0]}-{date_parts[1]}"
            return create_filename(f"{date} {j['title']}")

        if lecture:
            class_type_path = self.download_path / "lecture"
        else:
            class_type_path = self.download_path / "discussion"

        parent = class_type_path / "json"
        parent.mkdir(parents=True, exist_ok=True)
        for i, j in enumerate(jsons):
            with open(
                parent / f"{i+1:03}-{json_filename(j)}.json",
                "w",
            ) as f:
                f.write(json.dumps(j))
                # print(j)

        print("[i] Downloading media. This may take a very long time...")

        def download_file(url: str, path: Path):
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get("content-length", 0))
            block_size = 1024

            with tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                leave=False,
                desc=path.name,
            ) as pb:
                with open(path, "wb") as f:
                    for data in response.iter_content(block_size):
                        pb.update(len(data))
                        f.write(data)

        parent = class_type_path / "videos"
        parent.mkdir(parents=True, exist_ok=True)
        for i, j in enumerate(tqdm(jsons)):
            url = f"https:{j['mediaPrefix']}{j['sitekey']}/{j['info']['products'][0]['movie_exported_name']}.mp4"
            video_filename = f"{i+1:03}-{json_filename(j)}.mp4"
            subtitle_filename = f"{i+1:03}-{json_filename(j)}.vtt"
            download_file(url, parent / video_filename)
            res = self.driver.execute_async_script(
                f"""
                const callback = arguments[arguments.length - 1];
                fetch("/leccap/player/api/webvtt/?rk={j['recordingkey']}")
                    .then(res => res.text())
                    .then(t => callback(t));
                """
            )
            with open(parent / subtitle_filename, "w") as f:
                f.write(res)

# not gonna bother allow changing the download path since it seems like mount is needed to use external storage in wsl
print(f"[i] Mount another directory to the downloads directory to change where the files are saved'")

for course in courses:
    folder_name = "".join(course.split())
    course_name = fuzzy(course)
    print(f"[i] Course files for {course} will be saved under 'downloads/{folder_name}'")

    downloader = LeccapDownloader(folder_name, course_name, True)
    downloader.go()
    downloader.close()
